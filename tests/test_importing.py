# coding: utf-8
from io import BytesIO
from io import StringIO

from django.test import TestCase
import pytz

from wagtail.core.models import Page

from wagtailcsvimport.importing import import_pages

from tests.models import M2MPage
from tests.models import SimplePage


class ImportingTests(TestCase):
    fixtures = ['testdata.json']

    def test_create_cannot_set_excluded_fields(self):
        csv_data = StringIO(
            'id,parent,title,content_type,depth,numchild,page_ptr,path,url_path,int_field\r\n'
            ',2,Test page,42,3,7,2,000100010001,/home/wrong-path,42\r\n'
        )
        successes, errors = import_pages(csv_data, SimplePage)
        self.assertEqual(successes, [])
        self.assertEqual(
            [repr(e) for e in errors],
            ["Error(Error in CSV header: Unrecognized fields: ['depth', 'numchild', 'page_ptr', 'path', 'url_path'])"]
        )

    def test_create_complex_page_with_foreign_key(self):
        simple_page = SimplePage(
            title='Test Page',
            int_field=42,
        )
        home = Page.objects.get(slug='home')
        home.add_child(instance=simple_page)

        csv_data = StringIO(
            'id,parent,title,fk\r\n'
            ',2,Page with FK,3\r\n'
        )
        successes, errors = import_pages(csv_data, M2MPage)
        self.assertEqual(successes, ['Created page Page with FK with id 4'])
        self.assertEqual(errors, [])
        page = M2MPage.objects.latest('id')
        self.assertEqual(page.get_parent().id, home.pk)
        self.assertEqual(page.title, 'Page with FK')
        self.assertEqual(page.fk, simple_page)
        self.assertQuerysetEqual(page.m2m.all(), [])
        # page is in draft because live was not specified
        self.assertIs(page.live, False)

    def test_create_complex_page_with_m2m(self):
        simple_page_1 = SimplePage(
            title='Test Page',
            int_field=42,
        )
        simple_page_2 = SimplePage(
            title='Another Test Page',
            int_field=27,
        )
        home = Page.objects.get(slug='home')
        home.add_child(instance=simple_page_1)
        home.add_child(instance=simple_page_2)

        csv_data = StringIO(
            'id,parent,title,m2m\r\n'
            f',2,Page with M2M,"{simple_page_1.pk},{simple_page_2.pk}"\r\n'
        )
        successes, errors = import_pages(csv_data, M2MPage)
        self.assertEqual(successes, ['Created page Page with M2M with id 5'])
        self.assertEqual(errors, [])
        page = M2MPage.objects.latest('id')
        self.assertEqual(page.get_parent().id, home.pk)
        self.assertEqual(page.title, 'Page with M2M')
        self.assertIsNone(page.fk)
        self.assertQuerysetEqual(
            page.m2m.order_by('id'),
            ['<SimplePage: Test Page>', '<SimplePage: Another Test Page>']
        )
        # page is in draft because live was not specified
        self.assertIs(page.live, False)

    def test_create_error_missing_parent_field(self):
        csv_data = StringIO(
            'id,title,int_field\r\n'
            ',Orphan,42\r\n'
        )
        successes, errors = import_pages(csv_data, SimplePage)
        self.assertEqual(successes, [])
        self.assertEqual(
            [repr(e) for e in errors],
            ["Error(Errors processing row number 1: {'parent': [ValidationError(['Need a parent when creating a new page'])]})"])

    def test_create_error_type_field_doesnt_match_page_model(self):
        csv_data = StringIO(
            'id,content_type,parent,title,int_field\r\n'
            f',tests.m2mpage,2,Wrong type,42\r\n'
        )
        successes, errors = import_pages(csv_data, SimplePage)
        self.assertEqual(successes, [])
        self.assertEqual(
            [repr(e) for e in errors],
            ["Error(Errors processing row number 1: {'content_type': [ValidationError(['Expected tests.simplepage, was tests.m2mpage'])]})"]
        )

    def test_create_error_unrecognized_field(self):
        csv_data = StringIO(
            'id,title,int_field,wrong_field\r\n'
            ',Orphan,42,blah\r\n'
        )
        successes, errors = import_pages(csv_data, SimplePage)
        self.assertEqual(successes, [])
        self.assertEqual(
            [repr(e) for e in errors],
            ["Error(Error in CSV header: Unknown field(s) (wrong_field) specified for SimplePage)"]
        )

    def test_create_simple_page_all_fields(self):
        """Test a CSV with all possible fields.

        Check that non-editable fields are ignored.

        """
        csv_data = StringIO(
            'id,content_type,parent,title,slug,full_url,live,bool_field,char_field,draft_title,expire_at,expired,first_published_at,go_live_at,has_unpublished_changes,int_field,last_published_at,latest_revision_created_at,live_revision,locked,owner,rich_text_field,search_description,seo_title,show_in_menus\r\n'
            f',tests.simplepage,2,Test page,slug-life,http://wrong_url/,True,False,char,Draft title,2020-12-12 12:12:12,True,2019-01-01 01:01:01,,,42,2019-02-02 02:02:02,2019-03-03 03:03:03,123456,True,1,<p>Rich text</p>,SEO desc,SEO title,True\r\n'
        )
        successes, errors = import_pages(csv_data, SimplePage)
        self.assertEqual(successes, ['Created page Test page with id 3'], f'Errors: {errors}')
        self.assertEqual(errors, [])
        page = SimplePage.objects.latest('id')
        self.assertEqual(page.get_parent().id, 2)
        self.assertEqual(page.title, 'Test page')
        self.assertEqual(page.slug, 'slug-life')
        self.assertEqual(page.full_url, 'http://wagtailcsvimport.test/home/slug-life/')
        self.assertIs(page.live, True)
        self.assertIs(page.bool_field, False)
        self.assertEqual(page.char_field, 'char')
        self.assertEqual(page.draft_title, 'Test page')  # field was ignored
        self.assertEqual(page.expire_at, pytz.datetime.datetime(2020, 12, 12, 12, 12, 12, tzinfo=pytz.UTC))
        self.assertIs(page.expired, False)
        self.assertNotEqual(page.first_published_at, pytz.datetime.datetime(2019, 1, 1, 1, 1, 1, tzinfo=pytz.UTC))  # field was ignored
        self.assertIsNone(page.go_live_at)
        self.assertIs(page.has_unpublished_changes, False)
        self.assertEqual(page.int_field, 42)
        self.assertNotEqual(page.last_published_at, pytz.datetime.datetime(2019, 2, 2, 2, 2, 2, tzinfo=pytz.UTC))  # field was ignored
        self.assertNotEqual(page.latest_revision_created_at, pytz.datetime.datetime(2019, 3, 3, 3, 3, 3, tzinfo=pytz.UTC))  # field was ignored
        self.assertNotEqual(page.live_revision_id, 123456)
        self.assertIs(page.locked, False)
        self.assertEqual(page.owner_id, 1)
        self.assertEqual(page.rich_text_field, '<p>Rich text</p>')
        self.assertEqual(page.search_description, 'SEO desc')
        self.assertEqual(page.seo_title, 'SEO title')
        self.assertIs(page.show_in_menus, True)

    def test_create_simple_page_minimum_required_fields(self):
        csv_data = StringIO(
            'id,parent,title,int_field\r\n'
            f',2,A simple page for a simple test,27\r\n'
        )
        successes, errors = import_pages(csv_data, SimplePage)
        self.assertEqual(successes, ['Created page A simple page for a simple test with id 3'], f'Errors: {errors}')
        self.assertEqual(errors, [])
        page = SimplePage.objects.latest('id')
        self.assertEqual(page.get_parent().id, 2)
        self.assertEqual(page.title, 'A simple page for a simple test')
        self.assertEqual(page.int_field, 27)
        # missing fields have default values
        self.assertEqual(page.slug, 'a-simple-page-for-a-simple-test')
        self.assertEqual(page.seo_title, '')
        self.assertEqual(page.search_description, '')
        self.assertIs(page.bool_field, True)
        self.assertEqual(page.char_field, '')
        self.assertEqual(page.int_field, 27)
        self.assertEqual(page.rich_text_field, '')
        # page is in draft because live was not specified
        self.assertIs(page.live, False)

    def test_create_simple_page_unicode_text(self):
        csv_data = StringIO(
            'id,parent,title,seo_title,int_field,rich_text_field\r\n'
            f',2,日本語,漢語,42,<p> </p>\r\n'
        )
        successes, errors = import_pages(csv_data, SimplePage)
        self.assertEqual(successes, ['Created page 日本語 with id 3'], f'Errors: {errors}')
        self.assertEqual(errors, [])
        page = SimplePage.objects.latest('id')
        self.assertEqual(page.get_parent().id, 2)
        self.assertEqual(page.title, '日本語')
        self.assertEqual(page.seo_title, '漢語')
        self.assertEqual(page.rich_text_field, '<p> </p>')

    def test_non_editable_fields_are_silently_ignored(self):
        page = Page(
            title='Test Page',
            locked=False
        )
        home = Page.objects.get(slug='home')
        home.add_child(instance=page)

        csv_data = StringIO(
            'id,locked\r\n'
            f'{page.pk},True\r\n'
        )
        successes, errors = import_pages(csv_data, Page)
        self.assertEqual(successes, [f'Updated page Test Page with id 3'], f'Errors: {errors}')
        self.assertEqual(errors, [])

        page = Page.objects.get(pk=page.pk)
        # non-editable fields have not been changed
        self.assertIs(page.locked, False)

    def test_successes_are_committed_even_if_there_are_errors(self):
        page = Page(
            title='Existing Page',
        )
        home = Page.objects.get(slug='home')
        home.add_child(instance=page)

        csv_data = StringIO(
            'id,parent,title\r\n'
            '3,2,Updated Existing Page\r\n'
            ',2,New Page\r\n'
            ',2,\r\n'
        )
        successes, errors = import_pages(csv_data, Page)
        self.assertEqual(
            successes,
            ['Updated page Updated Existing Page with id 3',
             'Created page New Page with id 4'],
            f'Errors: {errors}'
        )
        self.assertEqual(
            [repr(e) for e in errors],
            ["Error(Errors processing row number 3: {'title': [ValidationError(['This field is required.'])]})"]
        )
        self.assertQuerysetEqual(
            Page.objects.order_by('id'),
            ['<Page: Root>', '<Page: Home>', '<Page: Updated Existing Page>', '<Page: New Page>']
        )

    def test_update_wont_move_pages(self):
        page = Page(
            title='Test Page',
        )
        home = Page.objects.get(slug='home')
        home.add_child(instance=page)

        csv_data = StringIO(
            'id,parent\r\n'
            f'3,1\r\n'
        )
        successes, errors = import_pages(csv_data, Page)
        self.assertEqual(successes, [])
        self.assertEqual(
            [repr(e) for e in errors],
            ["Error(Errors processing row number 1: {'parent': [ValidationError(['Cannot change parent page, moving pages is not yet supported.'])]})"]
        )

    def test_update_simple_page(self):
        page = SimplePage(
            title='Test Page',
            slug='test-page',
            seo_title='Not good SEO',
            search_description='This won\'t change',
            bool_field=True,
            char_field='Blag',
            int_field=42,
            rich_text_field='<p>Read Understand by Ted Chiang</p>'
        )
        home = Page.objects.get(slug='home')
        home.add_child(instance=page)

        csv_data = StringIO(
            'id,title,seo_title,int_field,rich_text_field\r\n'
            f'3,A New Title,Now THIS is SEO,27,<p>Anything by Ted Chiang really</p>\r\n'
        )
        successes, errors = import_pages(csv_data, SimplePage)
        self.assertEqual(successes, ['Updated page A New Title with id 3'], f'Errors: {errors}')
        self.assertEqual(errors, [])

        page = SimplePage.objects.get(pk=3)
        # listed fields have been updated
        self.assertEqual(page.title, 'A New Title')
        self.assertEqual(page.seo_title, 'Now THIS is SEO')
        self.assertEqual(page.int_field, 27)
        self.assertEqual(page.rich_text_field, '<p>Anything by Ted Chiang really</p>')

        # unlisted fields are not changed
        self.assertEqual(page.slug, 'test-page')
        self.assertEqual(page.search_description, 'This won\'t change')
        self.assertIs(page.bool_field, True)
        self.assertEqual(page.char_field, 'Blag')

    def test_update_simple_page_publish(self):
        page = SimplePage(
            title='Test Page',
            slug='test-page',
            int_field=42,
            live=False
        )
        home = Page.objects.get(slug='home')
        home.add_child(instance=page)

        csv_data = StringIO(
            'id,live\r\n'
            f'3,True\r\n'
        )
        successes, errors = import_pages(csv_data, SimplePage)
        self.assertEqual(successes, ['Updated page Test Page with id 3'], f'Errors: {errors}')
        self.assertEqual(errors, [])

        page = SimplePage.objects.get(pk=page.pk)
        # page has been published
        self.assertIs(page.live, True)

    def test_update_simple_page_unpublish(self):
        page = SimplePage(
            title='Test Page',
            slug='test-page',
            int_field=42,
            live=False
        )
        home = Page.objects.get(slug='home')
        home.add_child(instance=page)
        rev = page.save_revision()
        rev.publish()

        csv_data = StringIO(
            'id,live\r\n'
            f'3,False\r\n'
        )
        successes, errors = import_pages(csv_data, SimplePage)
        self.assertEqual(successes, ['Updated page Test Page with id 3'], f'Errors: {errors}')
        self.assertEqual(errors, [])

        page = SimplePage.objects.get(pk=page.pk)
        # page has been unpublished
        self.assertIs(page.live, False)

    def test_wagtail_model_validation_errors(self):
        """Test validation errors generated by Page models clean() and full_clean()"""
        csv_data = StringIO(
            'id,parent,title,slug\r\n'
            f',1,Another Home,home\r\n'
        )
        successes, errors = import_pages(csv_data, Page)
        self.assertEqual(successes, [])
        self.assertEqual(
            [repr(e) for e in errors],
            ["Error(Errors processing row number 1: {'slug': ['This slug is already in use']})"]
        )

    def test_wrong_file_content(self):
        not_csv_data = BytesIO(b'\x01\x11\x21\x31\x41\x51\x61\x71\x81\x91')
        successes, errors = import_pages(not_csv_data, Page)
        self.assertEqual(successes, [])
        self.assertEqual(
            [repr(e) for e in errors],
            ["Error(File is not valid CSV)"]
        )
