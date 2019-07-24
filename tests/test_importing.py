# coding: utf-8
from io import StringIO

from django.contrib.contenttypes.models import ContentType
from django.test import TransactionTestCase

from wagtail.core.models import Page
from wagtail.core.models import Site

from wagtailcsvimport.importing import import_pages

from tests.models import M2MPage
from tests.models import SimplePage


class ImportingTests(TransactionTestCase):

    def setUp(self):
        # default Wagtail pages are not available because
        # TransactionTestCase truncates the tables after each test
        page_content_type, created = ContentType.objects.get_or_create(
            app_label='wagtailcore',
            model='page'
        )
        self.root, created = Page.objects.get_or_create(
            path='0001', defaults={
                'title': 'Root',
                'slug': 'root',
                'content_type': page_content_type,
                'path': '0001',
                'depth': 1,
                'numchild': 1,
                'url_path': '/',
            }
        )
        self.home, created = Page.objects.get_or_create(
            path='00010001', defaults={
                'title': "Home Page",
                'slug': 'home',
                'content_type': page_content_type,
                'depth': 2,
                'numchild': 0,
                'url_path': '/home/',
            }
        )
        self.site, created = Site.objects.get_or_create(
            hostname='localhost', defaults={
                'root_page_id': self.home.pk,
                'is_default_site': True,
            }
        )

    def test_create_cannot_set_excluded_fields(self):
        csv_data = StringIO(
            'id,parent,title,content_type,depth,numchild,page_ptr,path,url_path,int_field\r\n'
            f',{self.home.pk},Test page,42,3,7,{self.home.pk},000100010001,/home/wrong-path,42\r\n'
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
        self.home.add_child(instance=simple_page)

        csv_data = StringIO(
            'id,parent,title,fk\r\n'
            f',{self.home.pk},Page with FK,{simple_page.pk}\r\n'
        )
        successes, errors = import_pages(csv_data, M2MPage)
        self.assertEqual(successes, ['Created page Page with FK'], f'Errors: {errors}')
        self.assertEqual(errors, [])
        page = M2MPage.objects.latest('id')
        self.assertEqual(page.get_parent().id, self.home.pk)
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
        self.home.add_child(instance=simple_page_1)
        self.home.add_child(instance=simple_page_2)

        csv_data = StringIO(
            'id,parent,title,m2m\r\n'
            f',{self.home.pk},Page with M2M,"{simple_page_1.pk},{simple_page_2.pk}"\r\n'
        )
        successes, errors = import_pages(csv_data, M2MPage)
        self.assertEqual(successes, ['Created page Page with M2M'], f'Errors: {errors}')
        self.assertEqual(errors, [])
        page = M2MPage.objects.latest('id')
        self.assertEqual(page.get_parent().id, self.home.pk)
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
            f',tests.m2mpage,{self.home.pk},Wrong type,42\r\n'
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
        csv_data = StringIO(
            'id,content_type,parent,title,slug,full_url,seo_title,search_description,live,bool_field,char_field,int_field,rich_text_field\r\n'
            f',tests.simplepage,{self.home.pk},Test page,slug-life,http://localhost/test-page/,SEO title,SEO desc,False,False,char,42,<p>Rich text</p>\r\n'
        )
        successes, errors = import_pages(csv_data, SimplePage)
        self.assertEqual(successes, ['Created page Test page'], f'Errors: {errors}')
        self.assertEqual(errors, [])
        page = SimplePage.objects.latest('id')
        self.assertEqual(page.get_parent().id, self.home.pk)
        self.assertEqual(page.title, 'Test page')
        self.assertEqual(page.slug, 'slug-life')
        self.assertEqual(page.seo_title, 'SEO title')
        self.assertEqual(page.search_description, 'SEO desc')
        self.assertIs(page.live, False)
        self.assertIs(page.bool_field, False)
        self.assertEqual(page.char_field, 'char')
        self.assertEqual(page.int_field, 42)
        self.assertEqual(page.rich_text_field, '<p>Rich text</p>')

    def test_create_simple_page_minimum_required_fields(self):
        csv_data = StringIO(
            'id,parent,title,int_field\r\n'
            f',{self.home.pk},A simple page for a simple test,27\r\n'
        )
        successes, errors = import_pages(csv_data, SimplePage)
        self.assertEqual(successes, ['Created page A simple page for a simple test'], f'Errors: {errors}')
        self.assertEqual(errors, [])
        page = SimplePage.objects.latest('id')
        self.assertEqual(page.get_parent().id, self.home.pk)
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
            f',{self.home.pk},日本語,漢語,42,<p> </p>\r\n'
        )
        successes, errors = import_pages(csv_data, SimplePage)
        self.assertEqual(successes, ['Created page 日本語'], f'Errors: {errors}')
        self.assertEqual(errors, [])
        page = SimplePage.objects.latest('id')
        self.assertEqual(page.get_parent().id, self.home.pk)
        self.assertEqual(page.title, '日本語')
        self.assertEqual(page.seo_title, '漢語')
        self.assertEqual(page.rich_text_field, '<p> </p>')

    def test_non_editable_fields_are_silently_ignored(self):
        page = Page(
            title='Test Page',
            locked=False
        )
        self.home.add_child(instance=page)

        csv_data = StringIO(
            'id,locked\r\n'
            f'{page.pk},True\r\n'
        )
        successes, errors = import_pages(csv_data, Page)
        self.assertEqual(successes, ['Updated page Test Page'], f'Errors: {errors}')
        self.assertEqual(errors, [])

        page = Page.objects.get(pk=page.pk)
        # non-editable fields have not been changed
        self.assertIs(page.locked, False)

    def test_update_wont_move_pages(self):
        page = Page(
            title='Test Page',
        )
        self.home.add_child(instance=page)

        csv_data = StringIO(
            'id,parent\r\n'
            f'{page.pk},{self.root.pk}\r\n'
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
        self.home.add_child(instance=page)

        csv_data = StringIO(
            'id,title,seo_title,int_field,rich_text_field\r\n'
            f'{page.pk},A New Title,Now THIS is SEO,27,<p>Anything by Ted Chiang really</p>\r\n'
        )
        successes, errors = import_pages(csv_data, SimplePage)
        self.assertEqual(successes, ['Updated page A New Title'], f'Errors: {errors}')
        self.assertEqual(errors, [])

        page = SimplePage.objects.get(pk=page.pk)
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
        self.home.add_child(instance=page)

        csv_data = StringIO(
            'id,live\r\n'
            f'{page.pk},True\r\n'
        )
        successes, errors = import_pages(csv_data, SimplePage)
        self.assertEqual(successes, ['Updated page Test Page'], f'Errors: {errors}')
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
        self.home.add_child(instance=page)
        rev = page.save_revision()
        rev.publish()

        csv_data = StringIO(
            'id,live\r\n'
            f'{page.pk},False\r\n'
        )
        successes, errors = import_pages(csv_data, SimplePage)
        self.assertEqual(successes, ['Updated page Test Page'], f'Errors: {errors}')
        self.assertEqual(errors, [])

        page = SimplePage.objects.get(pk=page.pk)
        # page has been unpublished
        self.assertIs(page.live, False)

    def test_wagtail_model_validation_errors(self):
        """Test validation errors generated by Page models clean() and full_clean()"""
        csv_data = StringIO(
            'id,parent,title,slug\r\n'
            f',{self.root.pk},Another Home,home\r\n'
        )
        successes, errors = import_pages(csv_data, Page)
        self.assertEqual(successes, [])
        self.assertEqual(
            [repr(e) for e in errors],
            ["Error(Errors processing row number 1: {'slug': ['This slug is already in use']})"]
        )
