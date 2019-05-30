__all__ = ["ReverseToken"]

from django.db import models

from .abstract_models import BaseReverseToken


class ReverseToken(BaseReverseToken):
    id = models.BigAutoField(primary_key=True, editable=False)
    created = models.DateTimeField(auto_now_add=True, editable=False)

    # for automatic deletion
    assignedcontent = models.ForeignKey(
        "spider_base.AssignedContent", on_delete=models.CASCADE,
        related_name="+", null=True, blank=True
    )
