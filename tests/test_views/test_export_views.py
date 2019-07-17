import io

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from wagtail.core.models import Page

from tests.models import SimplePage


class ExportViewTests(TestCase):
    fixtures = ['testdata.json']

    def setUp(self):
        self.client.login(username='admin', password='admin')

    def test_export_errors(self):
        data = {
            'page_type': 4242,
        }
        response = self.client.post('/admin/csv-import/export_to_file/', data)
        self.assertContains(response, b'Select a valid choice. 4242 is not one of the available choices.')
        self.assertEqual(response.status_code, 200)

    def test_export_get(self):
        response = self.client.get('/admin/csv-import/export_to_file/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, b'<form action="/admin/csv-import/export_to_file/" method="GET"')
        self.assertContains(response, b'<form action="/admin/csv-import/export_to_file/" method="POST"')

    def test_export_get_with_page_type(self):
        ct = ContentType.objects.get_for_model(SimplePage)
        data = {'page_type': ct.id}
        response = self.client.get('/admin/csv-import/export_to_file/', data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, b'<form action="/admin/csv-import/export_to_file/" method="GET"')
        self.assertContains(response, b'<form action="/admin/csv-import/export_to_file/" method="POST"')
        # response should contain the exportable fields for SimplePage
        self.assertContains(response, b'<input type="checkbox" name="fields" value="id" id="id_fields_0" checked>')
        self.assertContains(response, b'<input type="checkbox" name="fields" value="type" id="id_fields_1" checked>')
        self.assertContains(response, b'<input type="checkbox" name="fields" value="parent" id="id_fields_2" checked>')
        self.assertContains(response, b'<input type="checkbox" name="fields" value="title" id="id_fields_3" checked>')
        self.assertContains(response, b'<input type="checkbox" name="fields" value="slug" id="id_fields_4" checked>')
        self.assertContains(response, b'<input type="checkbox" name="fields" value="full_url" id="id_fields_5" checked>')
        self.assertContains(response, b'<input type="checkbox" name="fields" value="seo_title" id="id_fields_6" checked>')
        self.assertContains(response, b'<input type="checkbox" name="fields" value="search_description" id="id_fields_7" checked>')
        self.assertContains(response, b'<input type="checkbox" name="fields" value="live" id="id_fields_8" checked>')
        self.assertContains(response, b'<input type="checkbox" name="fields" value="bool_field" id="id_fields_9">')
        self.assertContains(response, b'<input type="checkbox" name="fields" value="char_field" id="id_fields_10">')
        self.assertContains(response, b'<input type="checkbox" name="fields" value="int_field" id="id_fields_11">')
        self.assertContains(response, b'<input type="checkbox" name="fields" value="rich_text_field" id="id_fields_12">')

    def test_export_simple_page_only_specific_fields(self):
        page = SimplePage(
            bool_field=False,
            char_field='char',
            int_field=42,
            rich_text_field='<p>Rich text</p>',
            title='Test page'
        )
        home = Page.objects.get(pk=2)
        home.add_child(instance=page)

        data = {
            'fields': ['id', 'title', 'int_field'],
            'page_type': page.content_type_id,
            'root_page': page.pk,
        }
        response = self.client.post('/admin/csv-import/export_to_file/', data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.streaming)
        full_response = io.BytesIO(b''.join(response.streaming_content))
        self.assertEqual(full_response.getvalue(), b'id,title,int_field\r\n3,Test page,42\r\n')

    def test_export_simple_page_with_page_type_includes_extra_fields(self):
        page = SimplePage(
            bool_field=False,
            char_field='char',
            int_field=42,
            rich_text_field='<p>Rich text</p>',
            title='Test page'
        )
        home = Page.objects.get(pk=2)
        home.add_child(instance=page)

        data = {
            'fields': ['id', 'type', 'parent', 'title', 'slug', 'full_url',
                       'seo_title', 'search_description', 'live',
                       'bool_field', 'char_field', 'int_field',
                       'rich_text_field'],
            'page_type': page.content_type_id,
            'root_page': home.pk,
        }
        response = self.client.post('/admin/csv-import/export_to_file/', data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.streaming)
        full_response = io.BytesIO(b''.join(response.streaming_content))
        self.assertEqual(full_response.getvalue(), b'id,type,parent,title,slug,full_url,seo_title,search_description,live,bool_field,char_field,int_field,rich_text_field\r\n3,tests.simplepage,2,Test page,test-page,http://wagtailcsvimport.test/home/test-page/,,,True,False,char,42,<p>Rich text</p>\r\n')
