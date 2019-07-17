from django.test import TestCase

from wagtail.core.models import Page

from tests.models import SimplePage


class ExportFormTests(TestCase):

    def test_export_default_fields_no_specific_page_model(self):
        from wagtailcsvimport.forms import ExportForm
        form = ExportForm()
        self.assertEqual(form.fields['fields'].choices, [
            ('id', 'ID'),
            ('type', 'Page type'),
            ('parent', 'Parent page id'),
            ('title', 'title'),
            ('slug', 'slug'),
            ('full_url', 'URL'),
            ('seo_title', 'page title'),
            ('search_description', 'search description'),
            ('live', 'live')
        ])
        self.assertEqual(form.fields['fields'].initial, [
            'id', 'type', 'parent', 'title', 'slug', 'full_url',
            'seo_title', 'search_description', 'live',
        ])

    def test_export_fields_choices_with_specific_page_model(self):
        from wagtailcsvimport.forms import ExportForm
        form = ExportForm(page_model=SimplePage)
        self.assertEqual(form.fields['fields'].choices, [
            ('id', 'ID'),
            ('type', 'Page type'),
            ('parent', 'Parent page id'),
            ('title', 'title'),
            ('slug', 'slug'),
            ('full_url', 'URL'),
            ('seo_title', 'page title'),
            ('search_description', 'search description'),
            ('live', 'live'),
            ('bool_field', 'Boolean field'),
            ('char_field', 'Char field'),
            ('int_field', 'Integer field'),
            ('rich_text_field', 'Rich text field')
        ])
        self.assertEqual(form.fields['fields'].initial, [
            'id', 'type', 'parent', 'title', 'slug', 'full_url',
            'seo_title', 'search_description', 'live',
        ])

    def test_export_invalid_fields_error(self):
        from wagtailcsvimport.forms import ExportForm
        data = {
            'fields': ['id', 'missing_field'],
            'root_page': 1,
        }
        form = ExportForm(data)
        form.is_valid()
        self.assertEqual(
            form.errors,
            {'fields': ['Select a valid choice. missing_field is not one of the available choices.']}
        )

    def test_export_invalid_root_page_error(self):
        from wagtailcsvimport.forms import ExportForm
        data = {
            'fields': ['id'],
            'root_page': 4242,
        }
        form = ExportForm(data)
        form.is_valid()
        self.assertEqual(
            form.errors,
            {'root_page': ['Select a valid choice. That choice is not one of the available choices.']}
        )

    def test_export_specific_fields(self):
        from wagtailcsvimport.forms import ExportForm
        page = SimplePage(
            bool_field=False,
            char_field='char',
            int_field=42,
            rich_text_field='<p>Rich text</p>',
            title='Test page'
        )
        root = Page.objects.get(pk=1)
        root.add_child(instance=page)
        data = {
            'fields': ['id', 'title', 'int_field'],
            'root_page': page.pk,
        }
        form = ExportForm(data, page_model=SimplePage)
        form.is_valid()
        self.assertEqual(form.errors, {})
        self.assertEqual(form.cleaned_data['root_page'], page)
        self.assertEqual(form.cleaned_data['only_published'], False)
        self.assertEqual(form.cleaned_data['fields'], ['id', 'title', 'int_field'])
