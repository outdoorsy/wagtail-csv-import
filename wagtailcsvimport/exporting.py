import csv
from datetime import datetime
from functools import lru_cache
from itertools import chain
import logging

from django.utils.translation import ugettext as _
try:
    from wagtail.core.models import Page
except ImportError:  # fallback for Wagtail <2.0
    from wagtail.wagtailcore.models import Page


logger = logging.getLogger(__name__)


# Put these fields first, in this order
BASE_FIELDS_ORDER = ('id', 'content_type', 'parent', 'title', 'slug', 'full_url', 'live')

def get_content_type(page):
    if getattr(page, "content_type", None):
        return f'{page.content_type.app_label}.{page.content_type.model}'
    return ""


# Fields in Wagtail's Page model to export by default
GENERATED_FIELDS = {
    '__all__': {
        'content_type': get_content_type,
        'full_url': lambda page: getattr(page, "full_url", ""),
        'parent': lambda page: getattr(page.get_parent(), 'pk'),
    },
    # TODO: support 'model': function()
}

# Fields that will never be exported
FIELDS_TO_IGNORE = {
    '__all__': {'content_type', 'depth', 'numchild', 'page_ptr', 'path', 'url_path'},
    # TODO: support 'model': ['fields', 'to', 'exclude']
}


@lru_cache(64)
def get_exportable_fields_for_model(page_model):
    fields = []
    fields_to_exclude = FIELDS_TO_IGNORE['__all__']
    for f in chain(page_model._meta.fields, page_model._meta.local_many_to_many):
        if f.name not in fields_to_exclude:
            fields.append(f.name)
    # fields that don't exist on DB
    fields.extend(GENERATED_FIELDS['__all__'].keys())

    # sort fields, put common ones first, then the rest alphabetically
    def field_sort(item):
        try:
            return BASE_FIELDS_ORDER.index(item)
        except ValueError:
            return len(BASE_FIELDS_ORDER)
    fields.sort()
    fields.sort(key=field_sort)
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

    if getattr(page_model.objects, "descendant_of", None):
        pages = page_model.objects.descendant_of(root_page, inclusive=True).order_by('depth', 'path')
        if content_type:
            pages = pages.filter(content_type=content_type)
        if only_published:
            pages = pages.live()
    else:
        pages = page_model.objects.all()

    # Don't write to a file or even a StringIO, as that would consume
    # memory unnecessarily. We will be yielding CSV rows one by one as
    # part of an iterator so only need to hold one row at a time,
    # which is the purpose of the Echo class.
    pseudo_buffer = Echo()

    if fieldnames:
        # validate that there are no extraneous fields
        all_exportable_fields = get_exportable_fields_for_model(page_model)
        unrecognized_fields = set(fieldnames) - set(all_exportable_fields)
        if unrecognized_fields:
            raise ValueError(_("Don't recognize these fields: %(field_list)s") % {
                'field_list': sorted(unrecognized_fields)
            })
    else:
        # default to all exportable fields for the given model
        fieldnames = get_exportable_fields_for_model(page_model)

    csv_writer = csv.DictWriter(pseudo_buffer, fieldnames=fieldnames)
    header = dict(zip(fieldnames, fieldnames))
    yield csv_writer.writerow(header)

    generated_fields = GENERATED_FIELDS['__all__']
    for (i, page) in enumerate(pages.iterator()):
        page_data = {}
        for fieldname in fieldnames:
            if fieldname in generated_fields:
                page_data[fieldname] = generated_fields[fieldname](page)
            else:
                field = page._meta.get_field(fieldname)
                if field.many_to_many:
                    # M2M, write comma-separated list of all related objects' ids
                    related_objs = field.value_from_object(page)
                    obj_ids = [str(obj.pk) for obj in related_objs]
                    page_data[fieldname] = ','.join(obj_ids)
                elif field.is_relation:
                    # foreign key, write related object's id
                    page_data[fieldname] = field.value_from_object(page)
                else:
                    # regular non-relation field
                    value = field.value_from_object(page)
                    if isinstance(value, datetime):
                        # don't output timezone information, it causes
                        # errors when importing
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    page_data[fieldname] = value
        yield csv_writer.writerow(page_data)
