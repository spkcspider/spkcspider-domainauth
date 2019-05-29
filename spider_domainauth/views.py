__all__ = ("ReverseTokenView", )

import logging

from django.shortcuts import get_object_or_404
from django.http import Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View

from .models import ReverseToken
from spkcspider.apps.spider.helpers import get_settings_func


logger = logging.getLogger(__name__)


class ReverseTokenView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Http404:
            return get_settings_func(
                "SPIDER_RATELIMIT_FUNC",
                "spkcspider.apps.spider.functions.rate_limit_default"
            )(self, request)

    def post(self, request, *args, **kwargs):
        payload = self.request.POST.get(
            "payload"
        )
        newtoken = self.request.POST.get("token", None)
        if not payload or not newtoken:
            raise Http404()

        self.object = get_object_or_404(
            ReverseToken, token=payload
        )
        self.object.token = "{}_{}".format(self.object.id, newtoken)
        self.object.save(update_fields=["token"])
        return HttpResponse(status=200)

    def options(self, request, *args, **kwargs):
        ret = super().options()
        ret["Access-Control-Allow-Origin"] = "*"
        ret["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        return ret
