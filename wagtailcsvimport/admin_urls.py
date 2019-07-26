from django.conf.urls import url

from wagtailcsvimport import views


app_name = 'wagtailcsvimport'

urlpatterns = [
    url(r'^import-from-file/$', views.import_from_file, name='import_from_file'),
    url(r'^export-to-file/$', views.export_to_file, name='export_to_file'),
]
