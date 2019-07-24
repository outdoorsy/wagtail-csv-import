from django.test import TestCase

from wagtail.core.models import Page

from tests.models import SimplePage


class ExportFormTests(TestCase):
    maxDiff = None

    def test_cleaned_data_specific_fields(self):
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

    def test_fields_no_specific_page_model(self):
        from wagtailcsvimport.forms import ExportForm
        form = ExportForm()
        self.assertEqual(
            form.fields['fields'].choices,
            [
                ('id', 'ID'),
                ('content_type', 'Page type'),
                ('parent', 'Parent page id'),
                ('title', 'title'),
                ('slug', 'slug'),
                ('full_url', 'URL'),
                ('live', 'live'),
                ('draft_title', 'draft title'),
                ('expire_at', 'expiry date/time'),
                ('expired', 'expired'),
                ('first_published_at', 'first published at'),
                ('go_live_at', 'go live date/time'),
                ('has_unpublished_changes', 'has unpublished changes'),
                ('last_published_at', 'last published at'),
                ('latest_revision_created_at', 'latest revision created at'),
                ('live_revision', 'live revision'),
                ('locked', 'locked'),
                ('owner', 'owner'),
                ('search_description', 'search description'),
                ('seo_title', 'page title'),
                ('show_in_menus', 'show in menus'),
            ]
        )
        self.assertEqual(
            form.fields['fields'].initial,
            [
                'id',
                'content_type',
                'parent',
                'title',
                'slug',
                'full_url',
                'live',
                'draft_title',
                'expire_at',
                'expired',
                'first_published_at',
                'go_live_at',
                'has_unpublished_changes',
                'last_published_at',
                'latest_revision_created_at',
                'live_revision',
                'locked',
                'owner',
                'search_description',
                'seo_title',
                'show_in_menus',
            ]
        )

    def test_fields_with_specific_page_model(self):
        from wagtailcsvimport.forms import ExportForm
        form = ExportForm(page_model=SimplePage)
        self.assertEqual(
            form.fields['fields'].choices,
            [
                ('id', 'ID'),
                ('content_type', 'Page type'),
                ('parent', 'Parent page id'),
                ('title', 'title'),
                ('slug', 'slug'),
                ('full_url', 'URL'),
                ('live', 'live'),
                ('bool_field', 'Boolean field'),
                ('char_field', 'Char field'),
                ('draft_title', 'draft title'),
                ('expire_at', 'expiry date/time'),
                ('expired', 'expired'),
                ('first_published_at', 'first published at'),
                ('go_live_at', 'go live date/time'),
                ('has_unpublished_changes', 'has unpublished changes'),
                ('int_field', 'Integer field'),
                ('last_published_at', 'last published at'),
                ('latest_revision_created_at', 'latest revision created at'),
                ('live_revision', 'live revision'),
                ('locked', 'locked'),
                ('owner', 'owner'),
                ('rich_text_field', 'Rich text field'),
                ('search_description', 'search description'),
                ('seo_title', 'page title'),
                ('show_in_menus', 'show in menus'),
            ]
        )
        self.assertEqual(
            form.fields['fields'].initial,
            [
                'id',
                'content_type',
                'parent',
                'title',
                'slug',
                'full_url',
                'live',
                'draft_title',
                'expire_at',
                'expired',
                'first_published_at',
                'go_live_at',
                'has_unpublished_changes',
                'last_published_at',
                'latest_revision_created_at',
                'live_revision',
                'locked',
                'owner',
                'search_description',
                'seo_title',
                'show_in_menus',
            ]
        )

    def test_invalid_fields_error(self):
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

    def test_invalid_root_page_error(self):
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
