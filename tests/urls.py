from django.urls import include
from django.urls import path

from wagtail.admin import urls as wagtailadmin_urls
from wagtail.core import urls as wagtail_urls


urlpatterns = [
    path('admin/', include(wagtailadmin_urls)),
    path('', include(wagtail_urls)),
]
