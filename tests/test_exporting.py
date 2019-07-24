from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from wagtail.core.models import Page

from wagtailcsvimport.exporting import export_pages
from wagtailcsvimport.exporting import get_exportable_fields_for_model

from tests.models import M2MPage
from tests.models import SimplePage


class ExportingTests(TestCase):

    def assertIteratorEquals(self, iterator, sequence):
        """Asserts that first argument is an iterator and it outputs the elements in sequence"""
        sequence_iter = iter(sequence)
        for i, item in enumerate(iterator):
            try:
                sequence_item = next(sequence_iter)
            except StopIteration:
                self.fail(f"Iterator has more items than expected. First extra item: {item!r}")
            if item != sequence_item:
                self.fail(f"Item {i} in iterator doesn't match expected value. Was {item!r}, expected {sequence_item!r}")
        try:
            missing_item = next(sequence_iter)
        except StopIteration:
            # happy path, both sequences match
            return
        else:
            self.fail(f"Iterator has less items than expected. First missing item: {missing_item!r}")

    def test_export_error_if_unrecognized_fields(self):
        ct = ContentType.objects.get_for_model(SimplePage)
        home = Page.objects.get(slug='home')
        with self.assertRaisesMessage(ValueError, "Don't recognize these fields: ['wrong_field']"):
            next(export_pages(home, content_type=ct, fieldnames=['id', 'content_type', 'int_field', 'wrong_field']))

    def test_export_foreign_key_and_m2m(self):
        simple_page_1 = SimplePage(
            title='Simple page 1',
            int_field=27
        )
        simple_page_2 = SimplePage(
            title='Simple page 2',
            int_field=42
        )
        home = Page.objects.get(slug='home')
        home.add_child(instance=simple_page_1)
        home.add_child(instance=simple_page_2)
        m2m_page = M2MPage(
            title='Test page',
            fk=simple_page_1
        )
        home.add_child(instance=m2m_page)
        m2m_page.m2m.add(simple_page_1, simple_page_2)

        ct = ContentType.objects.get_for_model(M2MPage)
        row_iter = export_pages(home, content_type=ct, fieldnames=['id', 'content_type', 'fk', 'm2m'])
        self.assertIteratorEquals(
            row_iter,
            [
                'id,content_type,fk,m2m\r\n',
                f'5,tests.m2mpage,{simple_page_1.pk},"{simple_page_1.pk},{simple_page_2.pk}"\r\n',
            ]
        )

    def test_export_only_published(self):
        page1 = SimplePage(
            bool_field=False,
            char_field='char',
            int_field=42,
            rich_text_field='<p>Rich text</p>',
            title='Test page',
            live=True
        )
        page2 = SimplePage(
            bool_field=True,
            char_field='almendras',
            int_field=27,
            rich_text_field='',
            title='Another test page',
            slug='custom-slug',
            seo_title='SEO title',
            search_description='SEO description',
            live=False
        )
        home = Page.objects.get(pk=2)
        home.add_child(instance=page1)
        home.add_child(instance=page2)

        row_iter = export_pages(home, fieldnames=['id'], only_published=True)
        self.assertIteratorEquals(
            row_iter,
            [
                'id\r\n',
                '2\r\n',
                '3\r\n',
            ]
        )

    def test_export_no_content_type_exports_basic_fields(self):
        page1 = SimplePage(
            bool_field=False,
            char_field='char',
            int_field=42,
            rich_text_field='<p>Rich text</p>',
            title='Test page',
            live=True
        )
        home = Page.objects.get(pk=2)
        home.add_child(instance=page1)
        page2 = M2MPage(
            title='M2M page',
            fk=page1,
            live=True
        )
        home.add_child(instance=page2)

        row_iter = export_pages(home)
        self.assertIteratorEquals(
            row_iter,
            [
                'id,content_type,parent,title,slug,full_url,live,draft_title,expire_at,expired,first_published_at,go_live_at,has_unpublished_changes,last_published_at,latest_revision_created_at,live_revision,locked,owner,search_description,seo_title,show_in_menus\r\n',
                '2,wagtailcore.page,1,Welcome to your new Wagtail site!,home,http://localhost/,True,Welcome to your new Wagtail site!,,False,,,False,,,,False,,,,False\r\n',
                '3,tests.simplepage,2,Test page,test-page,http://localhost/test-page/,True,Test page,,False,,,False,,,,False,,,,False\r\n',
                '4,tests.m2mpage,2,M2M page,m2m-page,http://localhost/m2m-page/,True,M2M page,,False,,,False,,,,False,,,,False\r\n',
            ]
        )

    def test_export_with_content_type_exports_all_fields(self):
        page1 = SimplePage(
            bool_field=False,
            char_field='char',
            int_field=42,
            rich_text_field='<p>Rich text</p>',
            title='Test page',
            live=True
        )
        page2 = SimplePage(
            bool_field=True,
            char_field='almendras',
            int_field=27,
            rich_text_field='',
            title='Another test page',
            slug='custom-slug',
            seo_title='SEO title',
            search_description='SEO description',
            live=True
        )
        home = Page.objects.get(pk=2)
        home.add_child(instance=page1)
        home.add_child(instance=page2)
        ct = ContentType.objects.get_for_model(SimplePage)

        row_iter = export_pages(home, content_type=ct)
        self.assertIteratorEquals(
            row_iter,
            [
                'id,content_type,parent,title,slug,full_url,live,bool_field,char_field,draft_title,expire_at,expired,first_published_at,go_live_at,has_unpublished_changes,int_field,last_published_at,latest_revision_created_at,live_revision,locked,owner,rich_text_field,search_description,seo_title,show_in_menus\r\n',
                '3,tests.simplepage,2,Test page,test-page,http://localhost/test-page/,True,False,char,Test page,,False,,,False,42,,,,False,,<p>Rich text</p>,,,False\r\n',
                '4,tests.simplepage,2,Another test page,custom-slug,http://localhost/custom-slug/,True,True,almendras,Another test page,,False,,,False,27,,,,False,,,SEO description,SEO title,False\r\n',
            ]
        )

    def test_get_exportable_fields_for_model_m2mpage(self):
        exportable_fields = get_exportable_fields_for_model(M2MPage)
        self.assertEqual(
            exportable_fields,
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
                'fk',
                'go_live_at',
                'has_unpublished_changes',
                'last_published_at',
                'latest_revision_created_at',
                'live_revision',
                'locked',
                'm2m',
                'owner',
                'search_description',
                'seo_title',
                'show_in_menus',
            ]
        )

    def test_get_exportable_fields_for_model_simplepage(self):
        exportable_fields = get_exportable_fields_for_model(SimplePage)
        self.assertEqual(
            exportable_fields,
            [
                'id',
                'content_type',
                'parent',
                'title',
                'slug',
                'full_url',
                'live',
                'bool_field',
                'char_field',
                'draft_title',
                'expire_at',
                'expired',
                'first_published_at',
                'go_live_at',
                'has_unpublished_changes',
                'int_field',
                'last_published_at',
                'latest_revision_created_at',
                'live_revision',
                'locked',
                'owner',
                'rich_text_field',
                'search_description',
                'seo_title',
                'show_in_menus',
            ]
        )

    def test_get_exportable_fields_for_model_wagtail_page(self):
        exportable_fields = get_exportable_fields_for_model(Page)
        self.assertEqual(
            exportable_fields,
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
