import csv
import logging

from django import forms
from django.core.exceptions import FieldError
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from wagtail.admin.rich_text.editors.draftail import DraftailRichTextArea
from wagtail.core.models import Page

from .exporting import get_exportable_fields_for_model


logger = logging.getLogger(__name__)


IGNORED_FIELDS = {'content_type', 'depth', 'first_published_at', 'full_url',
                  'live', 'numchild', 'page_ptr', 'path', 'url_path'}
NOT_REQUIRED_FIELDS = ['parent', 'slug']


class Error:
    def __init__(self, msg, value):
        self.msg = msg
        self.value = value

    def __str__(self):
        if self.value is None:
            return self.msg
        else:
            return f'{self.msg}: {self.value!s}'

    def __repr__(self):
        return f'Error({self})'

    def as_html(self):
        """Outputs the error in HTML appropriate for wagtailcsvimport templates.

        Handle different values, such as ValidationError, which
        require special processing for proper output.

        Strings are properly escaped to prevent XSS attacks.

        """
        if self.value is None:
            return format_html('<ul>{}</ul>', self.msg)
        elif isinstance(self.value, dict):
            error_list = []
            for key, raw_value in self.value.items():
                # msg can be a list
                try:
                    iterator = iter(raw_value)
                except TypeError:
                    # treat it as a string
                    str_value = str(raw_value)
                else:
                    # iterable, concatenate the values
                    # items can be ValidationError, which have a message attribute
                    str_value = '; '.join(str(getattr(item, 'message', item)) for item in iterator)
                error = format_html(
                    '<li>{}: {}</li>',
                    key, str_value
                )
                error_list.append(error)
            # individual errors have already been escaped by format_html
            detailed_errors = mark_safe('\n'.join(error_list))
        else:
            detailed_errors = str(self.value)

        return format_html('<ul>{}: {}</ul>', self.msg, detailed_errors)


def import_pages(csv_file, page_model):
    """Create pages from a CSV file.

    CSV format should be the same as produced by
    exporting.export_pages. Generated fields such as full_url will
    just be ignored.

    If the CSV has a "content_type" column it will be checked that it
    matches the right value for the given page_model, otherwise the
    row will fail with a ValidationError.

    """
    reader = csv.DictReader(csv_file)
    successes = []
    errors = []

    try:
        form_class = get_form_class(page_model, reader.fieldnames)
    except csv.Error:
        errors.append(Error(_('File is not valid CSV'), None))
        return successes, errors
    except FieldError as e:
        errors.append(Error(_('Error in CSV header'), e))
        return successes, errors

    error_msg = check_csv_header(reader.fieldnames, page_model, form_class)
    if error_msg:
        errors.append(Error(_('Error in CSV header'), error_msg))
        return successes, errors

    try:
        for i, row in enumerate(reader, start=1):
            page, error = import_page(row, i, page_model, form_class)
            if error:
                logger.info('Errors importing row %s: %s', i, error)
                errors.append(error)
            elif page and row.get('id'):
                logger.info('Updated page "%s" with id %d', page.title, page.pk)
                successes.append(_('Updated page %(title)s with id %(id)s') % {
                    'title': page.title, 'id': page.pk
                })
            elif page:
                logger.info('Created page "%s" with id %d', page.title, page.pk)
                successes.append(_('Created page %(title)s with id %(id)s') % {
                    'title': page.title, 'id': page.pk
                })
            else:
                logger.error('')
    except Exception as e:
        # something unexpected happened, tell the user and make sure
        # we rollback the transaction
        logger.exception('Exception importing CSV file')
        errors.append(Error(_('Irrecoverable exception importing row number %(number)s') % {'number': i}, e))

    return successes, errors


def import_page(row, row_number, page_model, form_class):
    page_id = row.get('id')
    if page_id:
        # update existing page
        page = page_model.objects.get(pk=page_id)
        form = form_class(row, instance=page)
    else:
        form = form_class(row)

    if form.is_valid():
        try:
            with transaction.atomic():
                page = form.save()
        except ValidationError as e:
            return None, Error(_('Errors processing row number %(number)s') % {'number': row_number},
                               e.message_dict)
        else:
            return page, None
    else:
        return None, Error(_('Errors processing row number %(number)s') % {'number': row_number},
                           form.errors.as_data())


def check_csv_header(header_row, page_model, form_class):
    """Validate that the fields in the header row are correct.

    Particularly this makes sure that the header has all required
    fields for the page model.

    form should be a ModelForm for the particular page model that is
    being imported (see get_form_for_page_model).

    In case of any error a ValidationError will be raised.

    """
    # detect unrecognized fields
    header_fields = set(header_row)
    all_valid_fields = set(get_exportable_fields_for_model(page_model))
    unrecognized_fields = header_fields - all_valid_fields
    if unrecognized_fields:
        return _('Unrecognized fields: %(field_list)s') % {
            'field_list': sorted(unrecognized_fields)
        }


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
    content_type = forms.CharField(required=False)
    live = forms.BooleanField(initial=False, required=False)
    parent = forms.ModelChoiceField(queryset=Page.objects.all(), required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # parent is not necessary when updating an instance
            self.fields['parent'].required = False

    def clean_content_type(self):
        # type field is present in exporter CSV, if present we just
        # want to make sure it matches the type of the page model
        value = self.cleaned_data.get('content_type')
        model_string = f'{self.instance._meta.app_label}.{self.instance._meta.model_name}'
        if value and value != model_string:
            raise ValidationError(_('Expected %(expected_value)s, was %(received_value)s') % {
                'expected_value': model_string, 'received_value': value
            })

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

    def clean_parent(self):
        # TODO: add support to update parent of existing pages,
        # i.e. to move them. Until then raise an error if parent
        # changes.
        value = self.cleaned_data['parent']
        if self.instance.pk:
            parent = self.instance.get_parent()
            if value and parent != value:
                raise ValidationError(_('Cannot change parent page, moving pages is not yet supported.'))
        else:
            if not value:
                raise ValidationError(_('Need a parent when creating a new page'))
        return value

    def save(self, commit=True):
        if self.instance.pk:
            # update existing instance
            page = super().save(commit=True)
            # TODO: move page if parent value has changed
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
    ignored_fields = {f.name for f in page_model._meta.fields if not f.editable}
    ignored_fields.update(IGNORED_FIELDS)
    m2m_fields = page_model._meta.local_many_to_many
    model_form = forms.modelform_factory(
        page_model, form=PageModelForm,
        fields=[f for f in fields if f not in ignored_fields],
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
