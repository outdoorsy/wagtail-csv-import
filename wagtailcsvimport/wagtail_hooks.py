from django.conf.urls import include, url
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

try:
    from wagtail.admin.menu import MenuItem
    from wagtail.core import hooks
except ImportError:  # fallback for Wagtail <2.0
    from wagtail.wagtailadmin.menu import MenuItem
    from wagtail.wagtailcore import hooks

from . import admin_urls


@hooks.register('register_admin_urls')
def register_admin_urls():
    return [
        url(r'^csv-import/', include(admin_urls, namespace='wagtailcsvimport_admin')),
    ]


class CsvImportMenuItem(MenuItem):
    def is_shown(self, request):
        return request.user.is_superuser


@hooks.register('register_admin_menu_item')
def register_csv_import_menu_item():
    return CsvImportMenuItem(
        _('CSV Import'), reverse('wagtailcsvimport_admin:index'), classnames='icon icon-download', order=800
    )
