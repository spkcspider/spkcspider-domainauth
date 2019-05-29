__all__ = ["ReverseToken"]

from django.db import models
from django.conf import settings

from spkcspider.apps.spider.constants import (
    hex_size_of_bigid
)
from spkcspider.apps.spider.helpers import create_b64_id_token

MAX_TOKEN_B64_SIZE = 90
_striptoken = getattr(settings, "TOKEN_SIZE", 30)*4//3


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
        related_name="reversetokens", null=True, blank=True
    )

    def __str__(self):
        if self.token:
            return "{}...".format(self.token[:-_striptoken])
        else:
            return "<empty>"

    def initialize_token(self):
        self.token = create_b64_id_token(
            self.id, "_", getattr(settings, "TOKEN_SIZE", 30)
        )

    @classmethod
    def create(cls, assignedcontent=None):
        ret = cls.objects.create(assignedcontent=assignedcontent)
        ret.initialize_token()
        ret.save()
        return ret

    @property
    def secret(self):
        if not self.token:
            return None
        return self.token.split("_", 1)[1]
