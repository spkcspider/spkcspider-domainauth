__all__ = ["create_domainauth_token"]


import os
import logging
import base64

from django.conf import settings

MAX_TOKEN_SIZE = 236
DEFAULT_SIZE = getattr(settings, "TOKEN_SIZE", 30)

logger = logging.getLogger(__name__)


def create_domainauth_token(id, sep="_", size=DEFAULT_SIZE):
    if size > MAX_TOKEN_SIZE:
        logger.warning("Nonce too big")
    return sep.join(
        (
            hex(id)[2:],
            base64.urlsafe_b64encode(
                os.urandom(size)
            ).decode('ascii').rstrip("=")
        )
    )
