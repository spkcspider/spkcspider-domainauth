__all__ = ("ReverseTokenView", )

import logging
import datetime
from urllib.parse import parse_qs, urlencode
from importlib import import_module

import requests

from django.conf import settings
from django.apps import apps
from django.shortcuts import get_object_or_404
from django.http import Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.views import View


logger = logging.getLogger(__name__)


def stubhttp404_handler(*args, **kwargs):
    pass


_http404_handler = stubhttp404_handler

if (
    "spkcspider.apps.spider" in settings.INSTALLED_APPS or
    "spkcspider.apps.spider.apps.SpiderBaseConfig"
):
    _http404_handler = "spkcspider.apps.spider.functions.rate_limit_default"
    from spkcspider.apps.spider.models import (
        AssignedContent, UserComponent, AuthToken, ReferrerObject
    )
    try:
        from spkcspider.constants import static_token_matcher
    except ImportError:
        from spkcspider.apps.spider.constants import static_token_matcher
    try:
        from spkcspider.apps.spider.conf import get_requests_params
    except ImportError:
        from spkcspider.apps.spider.helpers import get_requests_params
else:
    AssignedContent = None
    def get_requests_params(url):
        return (
            {
                "timeout": 3,
                "proxies": {}
            },
            False
        )

if getattr(settings, "SPIDER_RATELIMIT_FUNC", None):
    _http404_handler = settings.SPIDER_RATELIMIT_FUNC

if isinstance(_http404_handler, str):
    module, name = _http404_handler.rsplit(".", 1)
    _http404_handler = getattr(import_module(module), name)


class ReverseTokenView(View):
    model = apps.get_model(
        *getattr(
            settings,
            "DOMAINAUTH_MODEL",
            "spider_domainauth.ReverseToken"
        ).split(".", 1)
    )
    lifetime = getattr(
        settings,
        "DOMAINAUTH_LIFETIME",
        datetime.timedelta(hours=1)
    )
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Http404:
            return _http404_handler(self, request)

    def _clean_old(self, lifetime):
        expired = timezone.now() - lifetime
        self.model.filter(created__lte=expired)

    def request_urls(self, urls):
        if not self.request.user.is_authenticated:
            return HttpResponse(status=401)
        if self.lifetime:
            self._clean_old(self.lifetime)
        content = None
        if contenttoken and AssignedContent:
            content = get_object_or_404(
                AssignedContent, token=contenttoken
            )

        tokens = {}
        selfurl = request.get_full_path().split("?", 1)[0]
        with requests.Session() as session:
            rtoken = ReverseToken.objects.create(
                assignedcontent=content
            )
            for url in urls:
                params, can_inline = get_requests_params(url)
                if can_inline:
                    match = static_token_matcher.match(url)
                    # ignore invalid requests
                    if not match:
                        continue
                    if match.groupdict()["access"] == "list":
                        uc = UserComponent.objects.filter(
                            token=match["static_token"]
                        ).first()
                    else:
                        uc = UserComponent.objects.filter(
                            contents__token=match["static_token"]
                        ).first()
                    if not uc:
                        continue
                    t = AuthToken(
                        usercomponent=uc,
                        referrer=ReferrerObject.objects.get_or_create(
                            url=selfurl
                        )
                    )
                    t.save()
                    tokens[url] = t.token
                else:
                    splitted = url.split("?", 1)
                    if len(splitted) == 2:
                        getparams = parse_qs(splitted[1])
                    else:
                        getparams = {}
                    rtoken.initialize_token()
                    rtoken.save(update_fields=["token"])
                    getparams["referrer"] = selfurl
                    getparams["payload"] = rtoken.token
                    newurl = "{}?{}".format(
                        splitted[0], urlencode(getparams, doseq=True)
                    )
                    try:
                        with session.get(
                            newurl,
                            **params
                        ) as resp:
                            resp.raise_for_status()
                            rtoken.refresh_from_db()
                            tokens[url] = rtoken.token
                    except Exception:
                        if settings.DEBUG:
                            logging.exception(
                                "domain_auth failed for %s", newurl
                            )
                        ret = False
                rtoken.delete()
            return JsonResponse({
                "tokens": tokens
            })

    def answer_requests(self, oldtoken, newtoken):
        if self.lifetime:
            self._clean_old(self.lifetime)
        self.object = get_object_or_404(
            self.model, token=oldtoken
        )
        self.object.token = "{}_{}".format(self.object.id, newtoken)
        self.object.save(update_fields=["token"])
        return HttpResponse(status=200)

    def post(self, request, *args, **kwargs):
        oldtoken = request.POST.get("payload")
        newtoken = request.POST.get("token")
        urls = request.POST.getlist("urls")
        if urls:
            return self.request_urls(urls)
        elif oldtoken and newtoken:
            return self.answer_requests(oldtoken, newtoken)
        else:
            raise Http404()

    def options(self, request, *args, **kwargs):
        ret = super().options()
        ret["Access-Control-Allow-Origin"] = "*"
        ret["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        return ret
