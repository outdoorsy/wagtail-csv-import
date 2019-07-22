from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from wagtail.core.models import Page

from wagtailcsvimport.exporting import export_pages

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

    def test_export_ignores_foreign_keys_and_m2m(self):
        page = M2MPage(title='Complex Page', live=True)
        home = Page.objects.get(pk=2)
        home.add_child(instance=page)
        ct = ContentType.objects.get_for_model(M2MPage)

        row_iter = export_pages(page, content_type=ct)
        self.assertIteratorEquals(
            row_iter,
            [
                'id,type,parent,title,slug,full_url,seo_title,search_description,live\r\n',
                '3,tests.m2mpage,2,Complex Page,complex-page,http://localhost/complex-page/,,,True\r\n',
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

        row_iter = export_pages(home, only_published=True)
        self.assertIteratorEquals(
            row_iter,
            [
                'id,type,parent,title,slug,full_url,seo_title,search_description,live\r\n',
                '2,wagtailcore.page,1,Welcome to your new Wagtail site!,home,http://localhost/,,,True\r\n',
                '3,tests.simplepage,2,Test page,test-page,http://localhost/test-page/,,,True\r\n',
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

        row_iter = export_pages(home)
        self.assertIteratorEquals(
            row_iter,
            [
                'id,type,parent,title,slug,full_url,seo_title,search_description,live\r\n',
                '2,wagtailcore.page,1,Welcome to your new Wagtail site!,home,http://localhost/,,,True\r\n',
                '3,tests.simplepage,2,Test page,test-page,http://localhost/test-page/,,,True\r\n',
                '4,tests.simplepage,2,Another test page,custom-slug,http://localhost/custom-slug/,SEO title,SEO description,True\r\n',
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
                'id,type,parent,title,slug,full_url,seo_title,search_description,live,bool_field,char_field,int_field,rich_text_field\r\n',
                '3,tests.simplepage,2,Test page,test-page,http://localhost/test-page/,,,True,False,char,42,<p>Rich text</p>\r\n',
                '4,tests.simplepage,2,Another test page,custom-slug,http://localhost/custom-slug/,SEO title,SEO description,True,True,almendras,27,\r\n'
            ]
        )
