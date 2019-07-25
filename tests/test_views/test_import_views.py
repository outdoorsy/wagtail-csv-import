import io

from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TransactionTestCase

from wagtail.core.models import Page

from tests.models import M2MPage
from tests.models import SimplePage


class ImportViewTests(TransactionTestCase):
    fixtures = ['testdata.json']

    def setUp(self):
        self.client.login(username='admin', password='admin')

    def test_import_form_errors(self):
        data = {
            'page_type': 4242,
        }
        response = self.client.post('/admin/csv-import/import_from_file/', data)
        self.assertContains(response, b'Select a valid choice. 4242 is not one of the available choices.')
        self.assertEqual(response.status_code, 200)

    def test_import_get(self):
        # need to use dynamic values for the content types because
        # this being a TransactionTestCase they change after each test
        # runs, so their values are not static
        page_ct_id = ContentType.objects.get_for_model(Page).pk
        simplepage_ct_id = ContentType.objects.get_for_model(SimplePage).pk
        m2mpage_ct_id = ContentType.objects.get_for_model(M2MPage).pk

        response = self.client.get('/admin/csv-import/import_from_file/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<form action="/admin/csv-import/import_from_file/" method="GET"')
        self.assertContains(response, f'<option value="{page_ct_id}">Page</option>')
        self.assertContains(response, f'<option value="{simplepage_ct_id}">Simple page</option>')
        self.assertContains(response, f'<option value="{m2mpage_ct_id}">M2M page</option>')
        self.assertContains(response, '<form action="/admin/csv-import/import_from_file/" enctype="multipart/form-data" method="POST"')
        self.assertContains(response, '<input type="file" name="file"')
        # check explanations
        self.assertContains(response, 'These are all the fields accepted in the CSV header: <pre>id,content_type,parent,title,slug,full_url,live,draft_title,expire_at,expired,first_published_at,go_live_at,has_unpublished_changes,last_published_at,latest_revision_created_at,live_revision,locked,owner,search_description,seo_title,show_in_menus</pre>')
        self.assertContains(response, 'Please note that date fields will be interpreted in the user\'s current timezone: UTC')

    def test_import_post(self):
        # create a page to update it
        simple_page = SimplePage(title='Existing Page', int_field=79)
        home = Page.objects.get(slug='home')
        home.add_child(instance=simple_page)

        csv_data = (
            'id,content_type,parent,title,int_field\r\n'
            f',tests.simplepage,{home.pk},New Page,42\r\n'
            f'{simple_page.pk},tests.simplepage,{home.pk},Updated Existing Page,27\r\n'
            f',tests.simplepage,,Orphan,\r\n'
            f',tests.m2mpage,{home.pk},Wrong Type,\r\n'
        )
        csv_file = SimpleUploadedFile("test_import_post.csv",
                                      csv_data.encode('utf-8'),
                                      content_type="text/csv")
        data = {
            'file': csv_file,
            'page_type': ContentType.objects.get_for_model(SimplePage).pk,
        }
        response = self.client.post('/admin/csv-import/import_from_file/', data)
        self.assertEqual(response.status_code, 200)
        print(response.content[response.content.index(b'<div class="messages">'):])
        self.assertContains(response, 'Created page New Page')
        self.assertContains(response, 'Updated page Updated Existing Page')
        self.assertContains(response, 'Errors processing row number 3: need parent')
        self.assertContains(response, 'Errors processing row number 4: wrong type')

        # because there is an error, the successes were not committed to DB
        self.assertQuerysetEqual(SimplePage.objects.all(),
                                 ['<SimplePage: Existing Page>'])

    def test_import_post_not_csv_file(self):
        wrong_file = SimpleUploadedFile("not_a_csv.txt",
                                        b'\x00\x10\x20\x30\x40\x50\x60\x70\x80\x90',
                                        content_type="text/csv")
        data = {
            'file': wrong_file,
            'page_type': ContentType.objects.get_for_model(SimplePage).pk,
        }
        response = self.client.post('/admin/csv-import/import_from_file/', data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Error decoding file, make sure it&#39;s an UTF-8 encoded CSV file')
