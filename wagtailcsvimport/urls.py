from django.conf import settings
from django.conf.urls import url

from wagtailcsvimport import views


app_name = 'wagtailcsvimport'
urlpatterns = [
    url(r'^export/(?P<page_id>\d+)/$', views.export, name='export'),
]

if getattr(settings, "WAGTAILCSVIMPORT_EXPORT_UNPUBLISHED", False):
    urlpatterns += urlpatterns + [
        url(r'^export/(?P<page_id>\d+)/all/$', views.export, {'export_unpublished': True}, name='export'),
    ]
