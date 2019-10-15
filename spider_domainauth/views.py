__all__ = ("ReverseTokenView", )

import os
import time
import logging
import datetime
from urllib.parse import parse_qs, urlencode, urlsplit
from importlib import import_module
import random

import requests

from django.conf import settings
from django.apps import apps
from django.shortcuts import get_object_or_404
from django.http import Http404, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.views import View
from django.test import Client
from django.http.request import validate_host


logger = logging.getLogger(__name__)

# seed with real random
_nonexhaustRandom = random.Random(os.urandom(30))


def default_ratelimit_handler(request, view):
    # can raise 404 for stopping processing
    # with 0.4% chance reseed
    if _nonexhaustRandom.randint(0, 249) == 0:
        _nonexhaustRandom.seed(os.urandom(10))
    time.sleep(_nonexhaustRandom.random()/8)


try:
    from ratelimit import decorate, get_ratelimit
    # trigger TypeError if django-fast-ratelimit is too old
    get_ratelimit(key=False, group="abc", rate=(1, 1), empty_to=1)
    default_ratelimit_handler = decorate(
        func=default_ratelimit_handler,
        key="user",
        rate="1/10s",
        block=True,
        methods=("POST",),
        empty_to=0
    )
except (ImportError, TypeError):
    pass

_request_ratelimit_handler = default_ratelimit_handler

if (
    "spkcspider.apps.spider" in settings.INSTALLED_APPS or
    "spkcspider.apps.spider.apps.SpiderBaseConfig"
):
    from spkcspider.apps.spider.models import AssignedContent
    try:
        from spkcspider.apps.spider.conf import get_requests_params
    except ImportError:
        from spkcspider.apps.spider.helpers import get_requests_params
else:
    AssignedContent = None

    _default_allowed_hosts = ['localhost', '127.0.0.1', '[::1]']

    def get_requests_params(url):

        allowed_hosts = settings.ALLOWED_HOSTS
        if settings.DEBUG and not allowed_hosts:
            allowed_hosts = _default_allowed_hosts

        if validate_host(url, allowed_hosts):
            inline_domain = urlsplit(url)
            inline_domain = \
                inline_domain.netloc or inline_domain.path.split("/", 1)[0]
        else:
            inline_domain = None
        return (
            {
                "timeout": 3,
                "proxies": {}
            },
            inline_domain
        )


if getattr(settings, "DOMAINAUTH_RATELIMIT_FUNC", None):
    _request_ratelimit_handler = settings.DOMAINAUTH_RATELIMIT_FUNC

if isinstance(_request_ratelimit_handler, str):
    module, name = _request_ratelimit_handler.rsplit(".", 1)
    _request_ratelimit_handler = getattr(import_module(module), name)


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
    assert isinstance(lifetime, datetime.timedelta), "not a timedelta"

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        _request_ratelimit_handler(self.request, self)
        return super().dispatch(request, *args, **kwargs)

    def _clean_old(self, lifetime):
        expired = timezone.now() - lifetime
        self.model.objects.filter(created__lte=expired)

    def request_urls(self, contenttoken, urls):
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
        selfurl = self.request.build_absolute_uri().split("?", 1)[0]
        with requests.Session() as session:
            rtoken = self.model.objects.create(
                assignedcontent=content
            )
            for url in urls:
                splitted = url.split("?", 1)
                if len(splitted) == 2:
                    getparams = parse_qs(splitted[1])
                else:
                    getparams = {}
                rtoken.initialize_token()
                rtoken.save(update_fields=["token"])
                # can only handle domain auth
                getparams["intention"] = "domain"
                getparams["referrer"] = selfurl
                getparams["payload"] = rtoken.token
                newurl = "{}?{}".format(
                    splitted[0], urlencode(getparams, doseq=True)
                )
                params, inline_domain = get_requests_params(newurl)
                if inline_domain:
                    response = Client().get(
                        newurl, secure=True, follow=True, Connection="close",
                        SERVER_NAME=inline_domain
                    )
                    if response.status_code >= 400:
                        if settings.DEBUG:
                            logging.exception(
                                "domain_auth failed for %s", newurl
                            )
                    else:
                        rtoken.refresh_from_db()
                        tokens[url] = rtoken.secret
                else:
                    try:
                        with session.get(
                            newurl,
                            **params
                        ) as resp:
                            resp.raise_for_status()
                            rtoken.refresh_from_db()
                            tokens[url] = rtoken.secret
                    except Exception:
                        if settings.DEBUG:
                            logging.exception(
                                "domain_auth failed for %s", newurl
                            )
                rtoken.delete()
            return JsonResponse({
                "tokens": tokens
            })

    def answer_domainauth(self, oldtoken, newtoken):
        if self.lifetime:
            self._clean_old(self.lifetime)
        self.object = get_object_or_404(
            self.model, token=oldtoken
        )
        # use wrapper
        self.object.secret = newtoken
        self.object.save(update_fields=["token"])
        return HttpResponse(status=200)

    def get(self, request, *args, **kwargs):
        # domainauth redirects clients here, so add stub
        return HttpResponse(status=200)

    def post(self, request, *args, **kwargs):
        oldtoken = request.POST.get("payload")
        token = request.POST.get("token")
        urls = request.POST.getlist("urls")
        if urls:
            return self.request_urls(token, urls)
        elif oldtoken and token:
            return self.answer_domainauth(oldtoken, token)
        else:
            raise Http404()

    def options(self, request, *args, **kwargs):
        ret = super().options()
        ret["Access-Control-Allow-Origin"] = "*"
        ret["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return ret
