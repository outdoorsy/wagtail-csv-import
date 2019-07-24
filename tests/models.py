from django.db import models

from wagtail.core.models import Page
from wagtail.core.fields import RichTextField


class SimplePage(Page):
    """Simplest page possible, no hierarchy, simple fields"""
    bool_field = models.BooleanField(default=True, verbose_name='Boolean field')
    char_field = models.CharField(blank=True, max_length=100, verbose_name='Char field')
    int_field = models.IntegerField(null=True, verbose_name='Integer field')
    rich_text_field = RichTextField(blank=True, verbose_name='Rich text field')


class M2MPage(Page):
    """Page with M2M and foreign key fields"""
    fk = models.ForeignKey(SimplePage, blank=True, null=True,
                           related_name='+', on_delete=models.PROTECT)
    m2m = models.ManyToManyField(SimplePage, related_name='+')

    class Meta:
        verbose_name = 'M2M page'
        verbose_name_plural = 'M2M pages'


class NotAPage(models.Model):
    """Model that is not a Wagtail Page"""
    pass
