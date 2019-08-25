__all__ = ["ReverseTokenManager", "BaseReverseToken"]

from django.db import models
from django.conf import settings
from django.urls import reverse

from .utils import create_domainauth_token

hex_size_of_bigid = 16
_striptoken = getattr(settings, "TOKEN_SIZE", 30)*4//3


class ReverseTokenManager(models.Manager):

    def create(self, *, secret=None, token=None, **kwargs):
        ret = self.get_queryset().create(**kwargs)
        ret.initialize_token(secret or token)
        ret.save(update_fields=["token"])
        return ret


class BaseReverseToken(models.Model):
    token = models.CharField(
        max_length=255, null=True,
        blank=True, unique=True
    )

    objects = ReverseTokenManager()

    class Meta:
        abstract = True

    def __str__(self):
        if self.token:
            return "{}...".format(self.token[:-_striptoken])
        else:
            return "<empty>"

    def get_absolute_url(self):
        return reverse("spider_domainauth:db-domainauth")

    def initialize_token(self, secret=None):
        if secret:
            assert len(secret) <= 239, "Secret too big"
            self.token = "{}_{}".format(self.id, secret)
        else:
            self.token = create_domainauth_token(
                self.id, "_"
            )

    def _get_secret(self):
        if not self.token:
            return None
        return self.token.split("_", 1)[1]

    secret = property(fget=_get_secret, fset=initialize_token)
