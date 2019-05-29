from django.urls import path

from .views import ReverseTokenView

app_name = "spider_domainauth"


urlpatterns = [
    path(
        'db/',
        ReverseTokenView.as_view(),
        name='db-domainauth'
    )
]
