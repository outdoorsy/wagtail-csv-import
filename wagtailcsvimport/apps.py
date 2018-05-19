from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class WagtailCsvImportAppConfig(AppConfig):
    name = 'wagtailcsvimport'
    label = 'wagtailcsvimport'
    verbose_name = _("Wagtail CSV Import")
