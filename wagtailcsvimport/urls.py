from django.conf import settings
from django.conf.urls import url

from . import views


app_name = 'wagtailcsvimport'
urlpatterns = [
    url(r'^export/(?P<page_id>\d+)/$', views.export, {'only_published': True}, name='export'),
]

if getattr(settings, "WAGTAILCSVIMPORT_EXPORT_UNPUBLISHED", False):
    urlpatterns += urlpatterns + [
        url(r'^export/(?P<page_id>\d+)/all/$', views.export, {'only_published': False}, name='export'),
    ]
