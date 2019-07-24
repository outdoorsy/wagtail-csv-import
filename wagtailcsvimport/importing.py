import csv
import logging

from django import forms
from django.conf import settings
from django.core.exceptions import FieldError
from django.core.exceptions import ValidationError
from django.db import transaction
from wagtail.admin.rich_text.editors.draftail import DraftailRichTextArea
from wagtail.core.models import Page


logger = logging.getLogger(__name__)


IGNORED_FIELDS = {'content_type', 'depth', 'full_url', 'live',
                  'numchild', 'page_ptr', 'path', 'type', 'url_path'}
SPECIAL_PROCESS_FIELDS = {'id', 'full_url', 'live', 'type'}
NOT_REQUIRED_FIELDS = ['slug']


def import_pages(csv_file, page_model):
    """Create pages from a CSV file.

    CSV format should be the same as produced by
    exporting.export_pages. Generated fields such as full_url will
    just be ignored.

    If the CSV has a "type" column it will be checked that it matches
    the right value for the given page_model, otherwise the row will
    fail with a ValidationError.

    """
    reader = csv.DictReader(csv_file)
    successes = []
    errors = []

    try:
        form_class = get_form_class(page_model, reader.fieldnames)
    except FieldError as e:
        errors.append(f'Error in CSV header: {e}')
        return successes, errors

    try:
        check_csv_header(reader.fieldnames, form_class)
    except ValidationError as e:
        errors.append(e.message)
        return successes, errors

    # transaction will only commit if there are no errors
    transaction.set_autocommit(False)

    try:
        for i, row in enumerate(reader, start=1):
            page_id = row.get('id')
            if page_id:
                # update existing page
                page = page_model.objects.get(pk=page_id)
                form = form_class(row, instance=page)
            else:
                form = form_class(row)

            if form.is_valid():
                try:
                    new_page = form.save()
                except ValidationError as e:
                    logger.info('Validation errors importing row %s: %r',
                                i, e.message_dict)
                    errors.append(f'Errors processing row number {i}: {e.message_dict!r}')
                else:
                    if page_id:
                        logger.info('Updated page "%s" with id %d',
                                    new_page.title, new_page.pk)
                        successes.append(f'Updated page {new_page.title}')
                    else:
                        logger.info('Created page "%s" with id %d',
                                    new_page.title, new_page.pk)
                        successes.append(f'Created page {new_page.title}')
            else:
                logger.info('Error importing row number %s: %r', i, form.errors)
                errors.append(f'Errors processing row number {i}: {form.errors!r}')
    except Exception as e:
        # something unexpected happened, tell the user and make sure
        # we rollback the transaction
        logger.exception('Exception importing CSV file')
        errors.append(f'Exception importing row number {i}: {e!r}')

    if errors:
        transaction.rollback()
    else:
        transaction.commit()

    return successes, errors


def check_csv_header(header_row, form_class):
    """Validate that the fields in the header row are correct.

    Particularly this makes sure that the header has all required
    fields for the page model.

    form should be a ModelForm for the particular page model that is
    being imported (see get_form_for_page_model).

    In case of any error a ValidationError will be raised.

    """
    header_fields = set(header_row)
    form_fields = form_class.base_fields.keys()

    # check there are no extraneous fields
    unrecognized_fields = header_fields - form_fields - SPECIAL_PROCESS_FIELDS
    if unrecognized_fields:
        raise ValidationError(
            'CSV header has unrecognized fields: '
            '%r' % sorted(unrecognized_fields)
        )

    # check all required fields are accounted for
    required_fields = set()
    for field_name, field in form_class.base_fields.items():
        if field.required:
            required_fields.add(field_name)
    missing_required_fields = required_fields - header_fields
    if missing_required_fields:
        raise ValidationError(
            'CSV header is missing the following required fields: '
            '%r' % sorted(missing_required_fields)
        )

    return True


class CSVM2MField(forms.ModelMultipleChoiceField):
    """Field to process M2M fields with comma-separated values

    The default field that a ModelForm uses for a M2M field expects
    input as a list of strings (e.g. [1, 2, 3]). This field expects a
    string of comma-separated values (e.g. "1,2,3"), which is the
    format used by the CSV exporter.

    """

    def prepare_value(self, value):
        if isinstance(value, str):
            return value.split(',')
        return super().prepare_value(value)


class PageModelForm(forms.ModelForm):
    live = forms.BooleanField(initial=False, required=False)
    parent = forms.ModelChoiceField(queryset=Page.objects.all(), required=True)
    type = forms.CharField(required=False)

    def clean_live(self):
        # live field is not going to be manipulated directly, instead
        # it's used to decide whether the page instance needs to be
        # published (if it weren't and now live is True) or
        # unpublished (if it was and now live is False)
        previously_live = self.instance.pk and self.instance.live
        if previously_live and self.cleaned_data['live'] is False:
            self.cleaned_data['_unpublish_page'] = True
        elif not previously_live and self.cleaned_data['live'] is True:
            self.cleaned_data['_publish_page'] = True

    def clean_type(self):
        # type field is present in exporter CSV, if present we just
        # want to make sure it matches the type of the page model
        value = self.cleaned_data.get('type')
        model_string = f'{self.instance._meta.app_label}.{self.instance._meta.model_name}'
        if value and value != model_string:
            raise ValidationError(f"type should be {model_string}, is {value}")

    def save(self, commit=True):
        previously_live = self.instance.live

        if self.instance.pk:
            # update existing instance
            page = super().save(commit=True)
        else:
            # create new page under the given parent
            page = super().save(commit=False)
            page.live = False
            parent = self.cleaned_data['parent']
            parent.add_child(instance=page)
            self.save_m2m()

        # Handle publishing/unpublishing the page depending on the
        # live field. If the page was just created, we handle it like
        # it was previously on draft
        if self.cleaned_data.get('_publish_page'):
            rev = page.save_revision()
            rev.publish()
        elif self.cleaned_data.get('_unpublish_page'):
            page.unpublish()

        return page


def get_form_class(page_model, fields):
    """Build a ModelForm for the given page model."""
    m2m_fields = page_model._meta.local_many_to_many
    model_form = forms.modelform_factory(
        page_model, form=PageModelForm,
        fields=[f for f in fields if f not in IGNORED_FIELDS],
        # use custom form field for all M2M fields
        field_classes={f.name: CSVM2MField for f in m2m_fields}
    )
    for field_name in NOT_REQUIRED_FIELDS:
        field = model_form.base_fields.get(field_name)
        if field is not None:
            field.required = False
    # Wagtail's RichTextField widgets must be overriden because the
    # default widget expects a JSON-encoded format, but we want to
    # write the raw data without unpacking
    for field_name, field in model_form.base_fields.items():
        if isinstance(field.widget, DraftailRichTextArea):
            field.widget = forms.Textarea()
    return model_form
