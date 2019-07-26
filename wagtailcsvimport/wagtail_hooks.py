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
        url(r'^csv/', include(admin_urls, namespace='wagtailcsvimport')),
    ]


class CsvExportMenuItem(MenuItem):

    def is_shown(self, request):
        return request.user.is_superuser


class CsvImportMenuItem(MenuItem):

    def is_shown(self, request):
        return request.user.is_superuser


@hooks.register('register_admin_menu_item')
def register__import_menu_item():
    return CsvImportMenuItem(
        _('CSV Export'), reverse('wagtailcsvimport:export_to_file'), classnames='icon icon-collapse-down', order=898
    )


@hooks.register('register_admin_menu_item')
def register__import_menu_item():
    return CsvImportMenuItem(
        _('CSV Import'), reverse('wagtailcsvimport:import_from_file'), classnames='icon icon-collapse-up', order=899
    )
