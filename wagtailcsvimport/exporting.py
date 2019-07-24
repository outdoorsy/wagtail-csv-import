import csv
import logging

try:
    from wagtail.core.models import get_page_models
    from wagtail.core.models import Page
except ImportError:  # fallback for Wagtail <2.0
    from wagtail.wagtailcore.models import get_page_models
    from wagtail.wagtailcore.models import Page


logger = logging.getLogger(__name__)


# Fields in Wagtail's Page model to export by default
BASE_FIELDS = ['id', 'type', 'parent', 'title', 'slug', 'full_url',
               'seo_title', 'search_description', 'live']

FIELDS_TO_IGNORE = {'page_ptr'}


def get_exportable_fields_for_model(page_model):
    # always include Wagtail Page fields
    fields = BASE_FIELDS[:]
    # then include the page subclass' fields that are:
    # - not present in Wagtail's Page model
    # - not listed in FIELDS_TO_IGNORE
    # - editable
    # - not foreign key or M2M
    fields_to_exclude = {f.name for f in Page._meta.fields}
    fields_to_exclude.update(FIELDS_TO_IGNORE)
    specific_fields = []
    for f in page_model._meta.fields:
        if f.name not in fields_to_exclude and f.editable and f.related_model is None:
            specific_fields.append(f.name)
    specific_fields.sort()
    fields.extend(specific_fields)
    return fields


class Echo:
    """Implement just the write method of the file-like interface."""

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


def export_pages(root_page, content_type=None, fieldnames=None,
                 only_published=True):
    """Return iterator of CSV rows of all descendants of root_page (inclusive)

    If content_type is provided it should be an instance of
    django.contrib.contenttypes.models.ContentType of a Page subclass.

    If fieldnames is None then it will default to all exportable
    fields for the model corresponding to the given content_type. If
    fieldnames is provided then it is assumed to have been validated,
    i.e. that it doesn't include any invalid fields. This is done at
    ExportForm.

    By default only published pages are exported. If only_published is
    False the root_page and all its descendants, published or not, are
    included.

    """
    logger.info('Exporting pages to CSV with args root_page=%s '
                'content_type=%s fieldnames=%s only_published=%s',
                root_page, content_type, fieldnames, only_published)

    if content_type:
        page_model = content_type.model_class()
    else:
        page_model = Page

    pages = page_model.objects.descendant_of(root_page, inclusive=True)\
                              .order_by('depth', 'path')
    if content_type:
        pages = pages.filter(content_type=content_type)
    if only_published:
        pages = pages.live()

    # Don't write to a file or even a StringIO, as that would consume
    # memory unnecessarily. We will be yielding CSV rows one by one as
    # part of an iterator so only need to hold one row at a time,
    # which is the purpose of the Echo class.
    pseudo_buffer = Echo()

    if fieldnames is None:
        # default to all exportable fields for the given model
        fieldnames = get_exportable_fields_for_model(page_model)

    csv_writer = csv.DictWriter(pseudo_buffer, fieldnames=fieldnames)
    header = dict(zip(fieldnames, fieldnames))
    yield csv_writer.writerow(header)

    for (i, page) in enumerate(pages.iterator()):
        page_data = {}
        for field in fieldnames:
            if field == 'full_url':
                page_data['full_url'] = page.full_url
            elif field == 'parent':
                parent = page.get_parent()
                page_data['parent'] = parent.pk if parent is not None else ''
            elif field == 'type':
                ct = page.content_type
                page_data['type'] = f'{ct.app_label}.{ct.model}'
            else:
                page_data[field] = getattr(page, field)
        yield csv_writer.writerow(page_data)
