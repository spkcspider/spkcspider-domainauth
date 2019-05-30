__all__ = ("ReverseTokenView", )

import logging
from importlib import import_module

from django.conf import settings
from django.apps import apps
from django.shortcuts import get_object_or_404
from django.http import Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View


logger = logging.getLogger(__name__)


def stubhttp404_handler(*args, **kwargs):
    pass


_http404_handler = stubhttp404_handler

if "spkcspider.apps.spider" in settings.INSTALLED_APPS:
    _http404_handler = "spkcspider.apps.spider.functions.rate_limit_default"

if "spkcspider.apps.spider.apps.SpiderBaseConfig" in settings.INSTALLED_APPS:
    _http404_handler = "spkcspider.apps.spider.functions.rate_limit_default"

if getattr(settings, "SPIDER_RATELIMIT_FUNC", None):
    _http404_handler = settings.SPIDER_RATELIMIT_FUNC

if isinstance(_http404_handler, str):
    module, name = _http404_handler.rsplit(".", 1)
    _http404_handler = getattr(import_module(module), name)


class ReverseTokenView(View):
    model = apps.get_model(
        *getattr(
            settings,
            "DOMAIN_AUTH_MODEL",
            "spider_domainauth.ReverseToken"
        ).split(".", 1)
    )
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Http404:
            return _http404_handler(self, request)

    def post(self, request, *args, **kwargs):
        payload = self.request.POST.get(
            "payload"
        )
        newtoken = self.request.POST.get("token", None)
        if not payload or not newtoken:
            raise Http404()

        self.object = get_object_or_404(
            self.model, token=payload
        )
        self.object.token = "{}_{}".format(self.object.id, newtoken)
        self.object.save(update_fields=["token"])
        return HttpResponse(status=200)

    def options(self, request, *args, **kwargs):
        ret = super().options()
        ret["Access-Control-Allow-Origin"] = "*"
        ret["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        return ret
