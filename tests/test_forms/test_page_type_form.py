from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from wagtail.core.models import Page

from tests.models import NotAPage
from tests.models import SimplePage


class PageTypeFormTests(TestCase):

    def test_choices(self):
        from wagtailcsvimport.forms import PageTypeForm
        form = PageTypeForm()
        self.assertEqual(
            form.fields['page_type'].choices,
            [
                (7, 'M2M page'),
                (1, 'Page'),
                (6, 'Simple page'),
            ]
        )
        self.assertEqual(form.fields['page_type'].initial, 1)

    def test_get_content_type_with_empty_page_type(self):
        from wagtailcsvimport.forms import PageTypeForm
        ct = ContentType.objects.get_for_model(Page)
        data = {}
        form = PageTypeForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.get_content_type(), ct)

    def test_get_content_type_with_valid_page_type(self):
        from wagtailcsvimport.forms import PageTypeForm
        ct = ContentType.objects.get_for_model(SimplePage)
        data = {
            'page_type': ct.id,
        }
        form = PageTypeForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.get_content_type(), ct)

    def test_get_page_model_with_empty_page_type(self):
        from wagtailcsvimport.forms import PageTypeForm
        data = {}
        form = PageTypeForm(data)
        self.assertTrue(form.is_valid())
        self.assertIs(form.get_page_model(), Page)

    def test_get_page_model_with_valid_page_type(self):
        from wagtailcsvimport.forms import PageTypeForm
        ct = ContentType.objects.get_for_model(SimplePage)
        data = {
            'page_type': ct.id,
        }
        form = PageTypeForm(data)
        self.assertTrue(form.is_valid())
        self.assertIs(form.get_page_model(), SimplePage)

    def test_invalid_page_type_error(self):
        from wagtailcsvimport.forms import PageTypeForm
        data = {
            'page_type': 4242,
        }
        form = PageTypeForm(data)
        form.is_valid()
        self.assertEqual(
            form.errors,
            {'page_type': ['Select a valid choice. 4242 is not one of the available choices.']}
        )

    def test_not_a_wagtail_page_error(self):
        from wagtailcsvimport.forms import PageTypeForm
        ct = ContentType.objects.get_for_model(NotAPage)
        data = {
            'page_type': ct.id,
        }
        form = PageTypeForm(data)
        form.is_valid()
        self.assertEqual(
            form.errors,
            {'page_type': [f'Select a valid choice. {ct.id} is not one of the available choices.']}
        )
