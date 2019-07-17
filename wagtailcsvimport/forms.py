from django import forms
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


from .exporting import EXPORT_FIELDS_FOR_MODEL


def calculate_export_fields_choices(page_model):
    choices = []
    if page_model is None:
        page_model = Page
    exportable_fields = EXPORT_FIELDS_FOR_MODEL[page_model]
    for field_name in exportable_fields:
        if field_name == 'full_url':
            choices.append(('full_url', 'URL'))
        elif field_name == 'parent':
            choices.append(('parent', 'Parent page id'))
        elif field_name == 'type':
            choices.append(('type', 'Page type'))
        else:
            field = page_model._meta.get_field(field_name)
            choices.append((field_name, field.verbose_name))
    return choices


DEFAULT_FIELDS_TO_EXPORT = calculate_export_fields_choices(Page)

PAGE_TYPE_CHOICES = [
    (ContentType.objects.get_for_model(p).id, p.get_verbose_name()) for p in get_page_models()
]


class PageTypeForm(forms.Form):
    page_type = forms.ChoiceField(
        choices=PAGE_TYPE_CHOICES,
        required=False,
        label=_("Page type"),
        help_text=_("Will only export pages of this type, with all their extra information. If not set will export all pages of all types, but with minimal information.")
    )

    def get_content_type(self):
        assert(not self._errors)  # must be called after is_valid()
        content_type_id = self.cleaned_data['page_type']
        if content_type_id:
            content_type = ContentType.objects.get_for_id(content_type_id)
            return content_type

    def get_page_model(self):
        assert(not self._errors)  # must be called after is_valid()
        content_type = self.get_content_type()
        if content_type is not None:
            return content_type.model_class()


class ImportFromFileForm(forms.Form):
    file = forms.FileField(label=_("File to import"))
    parent_page = forms.ModelChoiceField(
        queryset=Page.objects.all(),
        widget=AdminPageChooser(can_choose_root=True, user_perms='copy_to'),
        label=_("Destination parent page"),
        help_text=_("Imported pages will be created as children of this page.")
    )


class ExportForm(forms.Form):
    fields = forms.MultipleChoiceField(
        label=_('Fields to export'),
        choices=DEFAULT_FIELDS_TO_EXPORT,
        initial=[choice[0] for choice in DEFAULT_FIELDS_TO_EXPORT],
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
        page_model = kwargs.pop('page_model', None)
        super().__init__(*args, **kwargs)
        if page_model is not None:
            self.fields['fields'].choices = calculate_export_fields_choices(page_model)
