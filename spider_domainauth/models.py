__all__ = ["ReverseToken"]

from django.db import models
from django.conf import settings
from django.urls import reverse

from spkcspider.apps.spider.constants import (
    hex_size_of_bigid
)
from spkcspider.apps.spider.helpers import create_b64_id_token

MAX_TOKEN_B64_SIZE = 90
_striptoken = getattr(settings, "TOKEN_SIZE", 30)*4//3


class ReverseTokenManager(models.Manager):

    def create(self, *, secret=None, token=None, **kwargs):
        ret = self.get_queryset().create(**kwargs)
        ret.initialize_token(secret or token)
        ret.save(update_fields=["token"])
        return ret


class ReverseToken(models.Model):
    id = models.BigAutoField(primary_key=True, editable=False)
    token = models.CharField(
        max_length=MAX_TOKEN_B64_SIZE+hex_size_of_bigid*2+4, null=True,
        blank=True, unique=True
    )
    created = models.DateTimeField(auto_now_add=True, editable=False)
    # for automatic deletion
    assignedcontent = models.ForeignKey(
        "spider_base.AssignedContent", on_delete=models.CASCADE,
        related_name="+", null=True, blank=True
    )

    objects = ReverseTokenManager()

    def __str__(self):
        if self.token:
            return "{}...".format(self.token[:-_striptoken])
        else:
            return "<empty>"

    def get_absolute_url(self):
        return reverse("spider_domainauth:db-domainauth")

    def initialize_token(self, secret=None):
        if secret:
            self.token = "{}_{}".format(self.id, secret)
        else:
            self.token = create_b64_id_token(
                self.id, "_", getattr(settings, "TOKEN_SIZE", 30)
            )

    def _get_secret(self):
        if not self.token:
            return None
        return self.token.split("_", 1)[1]

    secret = property(fget=_get_secret, fset=initialize_token)
