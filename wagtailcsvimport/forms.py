from functools import lru_cache

from django import forms
from django.forms import Media
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

try:
    from wagtail.admin.widgets import AdminPageChooser
    from wagtail.core.models import get_page_models
    from wagtail.core.models import Page
except ImportError:  # fallback for Wagtail <2.0
    from wagtail.wagtailadmin.widgets import AdminPageChooser
    from wagtail.wagtailcore.models import get_page_models
    from wagtail.wagtailcore.models import Page


from .exporting import get_exportable_fields_for_model
from django.apps import apps


def get_models():
    page_models = get_page_models()
    settings_models = [apps.get_model(x) for x in settings.WAGTAILCSVIMPORT_MODELS]
    return [*page_models, *settings_models]


class PageTypeForm(forms.Form):
    page_type = forms.ChoiceField(
        choices=[],  # populated on __init__
        required=False,
        label=_("Page type"),
        help_text=_("Will only export pages of this type, with all their extra information. If not set will export all pages of all types, but with minimal information.")
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        page_type_choices = self.get_page_type_choices()
        self.fields['page_type'].choices = page_type_choices

    @staticmethod
    def get_page_type_choices():
        choices = []
        for m in get_models():
            choice = (ContentType.objects.get_for_model(m).id, m.get_verbose_name())
            if m is Page:
                page_choice = choice
            else:
                choices.append(choice)

        # sort by model verbose name
        choices.sort(key=lambda c: c[1])

        # HACK: put Page first so it will appear as default
        # Using initial won't work because the form is always bound in the views
        choices.insert(0, page_choice)

        return choices

    def get_content_type(self):
        assert(not self._errors)  # must be called after is_valid()
        content_type_id = self.cleaned_data['page_type']
        if content_type_id:
            content_type = ContentType.objects.get_for_id(content_type_id)
            return content_type
        else:
            return ContentType.objects.get_for_model(Page)

    def get_page_model(self):
        assert(not self._errors)  # must be called after is_valid()
        content_type = self.get_content_type()
        if content_type is not None:
            return content_type.model_class()
        else:
            return Page

    @property
    def media(self):
        return Media(js=['wagtailcsvimport/js/page_type_form_helpers.js'])


class ImportForm(forms.Form):
    file = forms.FileField(label=_("File to import"))


class ExportForm(forms.Form):
    fields = forms.MultipleChoiceField(
        label=_('Fields to export'),
        choices=[],
        widget=forms.CheckboxSelectMultiple)
    only_published = forms.BooleanField(
        label=_('Include only published pages?'),
        required=False
    )
    root_page = forms.ModelChoiceField(
        label=_('Root page to export'),
        queryset=Page.objects.all().specific(),
        widget=AdminPageChooser(can_choose_root=True),
        help_text=_("Will export this page and all its descendants of the chosen page type.")
    )

    def __init__(self, *args, **kwargs):
        page_model = kwargs.pop('page_model', Page)
        super().__init__(*args, **kwargs)
        self.fields['fields'].choices = self.get_export_fields_choices(page_model)
        self.fields['fields'].initial = [c[0] for c in self.get_export_fields_choices(Page)]

    @staticmethod
    @lru_cache(64)
    def get_export_fields_choices(page_model):
        choices = []
        if page_model is None:
            page_model = Page
        exportable_fields = get_exportable_fields_for_model(page_model)
        for field_name in exportable_fields:
            if field_name == 'content_type':
                choices.append(('content_type', 'Page type'))
            elif field_name == 'full_url':
                choices.append(('full_url', 'URL'))
            elif field_name == 'parent':
                choices.append(('parent', 'Parent page id'))
            else:
                field = page_model._meta.get_field(field_name)
                choices.append((field_name, field.verbose_name))
        return choices
