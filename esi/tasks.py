from datetime import timedelta
import logging

from celery import shared_task

from django.utils import timezone

from .models import CallbackRedirect, Token


logger = logging.getLogger(__name__)


@shared_task
def cleanup_callbackredirect(max_age=300):
    """
    Delete old :model:`esi.CallbackRedirect` models.
    Accepts a max_age parameter, in seconds (default 300).
    """
    max_age = timezone.now() - timedelta(seconds=max_age)
    logger.debug(
        "Deleting all callback redirects created before %s",
        max_age.strftime("%b %d %Y %H:%M:%S")
    )
    CallbackRedirect.objects.filter(created__lte=max_age).delete()


@shared_task
def cleanup_token():
    """
    Delete expired :model:`esi.Token` models.
    """
    logger.debug("Clearring Userless Tokens.")
    Token.objects.filter(user__isnull=True).delete()
    logger.debug("Triggering bulk refresh of all expired tokens.")
    Token.objects.all().get_expired().bulk_refresh()
