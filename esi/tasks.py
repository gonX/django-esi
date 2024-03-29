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
    orphaned_tokens = Token.objects.filter(user__isnull=True)
    if orphaned_tokens.exists():
        logger.info("Deleting %d orphaned tokens.", orphaned_tokens.count())
        orphaned_tokens.delete()
    expired_tokens = Token.objects.exclude(user__isnull=True).get_expired()
    if expired_tokens.exists():
        logger.info(
            "Triggering bulk refresh of %d expired tokens.", expired_tokens.count()
        )
        for token_pk in (
            expired_tokens.filter(refresh_token__isnull=False)
            .values_list("pk", flat=True)
        ):
            refresh_or_delete_token.apply_async(args=[token_pk], priority=8)


@shared_task
def refresh_or_delete_token(token_pk: int):
    token = Token.objects.get(pk=token_pk)
    token.refresh_or_delete()
