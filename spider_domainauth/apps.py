__all__ = ["DomainAuthConfig"]

from django.apps import AppConfig


class DomainAuthConfig(AppConfig):
    name = 'spider_domainauth'
    label = 'spider_domainauth'
    verbose_name = 'db based domain authentication'
    spider_url_path = 'domainauth/'
