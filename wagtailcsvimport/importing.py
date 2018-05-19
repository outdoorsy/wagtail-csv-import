import csv
import random
import string
from io import StringIO

from django.apps import apps
from django.db import transaction
from django.core.exceptions import ValidationError

try:
    from wagtail.core.models import Page
except ImportError:  # fallback for Wagtail <2.0
    from wagtail.wagtailcore.models import Page


@transaction.atomic()
def import_pages(import_data, parent_page):
    """
    Take a CSV import of pages and create those pages under the parent page
    """
    csv_file = StringIO(import_data)
    reader = csv.DictReader(csv_file)

    pages = []
    for row in reader:
        pages.append(row)

    # Do we want to auto-detect by existing children?
    children = parent_page.get_descendants()
    child_class = None
    if children:
        child_class = children[0].specific_class

    for (i, page_record) in enumerate(pages):
        # If record specifies model type, prefer it
        app_label = page_record.pop('app', None)
        model_name = page_record.pop('model_name', None)

        if app_label is not None and model_name is not None:
            child_class = apps.get_model(app_label, model_name)

        # Set a default to not live.
        if 'live' not in page_record:
            page_record['live'] = 0

        try:
            specific_page = child_class(**page_record)
            parent_page.add_child(instance=specific_page)
        except ValidationError as e:
            edict = e.message_dict
            # handle slug validation and re-save
            if 'slug' in edict:
                str = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))
                specific_page.slug = "%s-%s" % (page_record['slug'], str)
                parent_page.add_child(instance=specific_page)

    return len(pages)
