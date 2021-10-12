from datetime import datetime
from django.core.management.base import BaseCommand, CommandError

from django.db.migrations.recorder import MigrationRecorder
from django.utils import timezone

from esi.models import Token
from esi.errors import (
    TokenInvalidError,
    IncompleteResponseError,
    NotRefreshableTokenError
)
from esi import app_settings
from oauthlib.oauth2.rfc6749.errors import (
    InvalidClientIdError,
    InvalidGrantError,
    InvalidTokenError,
)
from requests.auth import HTTPBasicAuth

from tqdm import tqdm

from requests_oauthlib import OAuth2Session

import pytz

EVE_SSOV1_END_DATE = datetime(
    year=2021, month=11, day=1, hour=0, minute=0, tzinfo=pytz.UTC)


def _sso_v1_refresh(session: OAuth2Session, auth: HTTPBasicAuth, token: Token, message: str):
    """
    SSOv1 Refresh.
    """
    try:
        _data = session.refresh_token(
            "https://login.eveonline.com/oauth/token",
            refresh_token=token.refresh_token,
            auth=auth
        )

        token.access_token = _data['access_token']
        token.refresh_token = _data['refresh_token']
        token.sso_version = 1
        token.created = timezone.now()
        token.save()
        return True
    except (InvalidGrantError):
        return ("ID:%s '%s' %s refresh failed"
                " (InvalidGrant)" % (token.id, token.character_name, message))
    except (InvalidTokenError, InvalidClientIdError):
        return ("ID:%s '%s' %s SSOv1 Refresh Failed "
                "(InvalidToken, InvalidClientId)" % (token.id, token.character_name, message))
    except Exception as e:
        return ("ID:%s '%s' %s SSOv1 "
                "Refresh Failed (%s)" % (token.id, token.character_name, message, e))


class Command(BaseCommand):
    help = 'Attempt to Migrate all SSOv1 Tokens to SSOv2, and report failures.'
    requires_migrations_checks = True
    requires_system_checks = True

    def add_arguments(self, parser):
        parser.add_argument('--skip-v1-checks', action='store_true',
                            help="Do not test on SSOv1 Endpoints, both before"
                            " updating to SSOv2 and after a failure.")
        parser.add_argument('--purge', action='store_true',
                            help='Purge Tokens that fail the SSOv2 Update')

    def handle(self, *args, **options):
        use_v1 = options.get('skip-v1-checks', True) and (timezone.now() <= EVE_SSOV1_END_DATE)
        purge = options.get('purge', False)

        migration_10 = MigrationRecorder.Migration.objects.filter(
            app='esi', name="0010_set_new_tokens_to_sso_v2").exists()

        if not migration_10:
            raise CommandError("Run migrations first and try again!")
        else:
            self.stdout.write("\n\nMigrations up to date. Proceeding to updates!")

        if not use_v1:
            self.stdout.write("\n\nSkipping SSOv1 pre/post error Verification!")

        # lets reuse our own session and auth
        session = OAuth2Session(app_settings.ESI_SSO_CLIENT_ID)
        auth = HTTPBasicAuth(
            app_settings.ESI_SSO_CLIENT_ID, app_settings.ESI_SSO_CLIENT_SECRET
        )

        # only do tokens that are SSOv1
        tokens = Token.objects.filter(sso_version=1)
        total = tokens.count()

        if total > 0:
            self.stdout.write(
                "There are %s Tokens to update." % (total)
            )
        else:
            return self.stdout.write("There are no Tokens to update.")

        failures = []
        # Nice Progress bar as this may take a while.
        with tqdm(total=total) as t:
            for token in tokens:
                if use_v1:
                    result = _sso_v1_refresh(session, auth, token, "Initial")
                    if result is not True:
                        failures.append(result)
                        if purge:
                            token.delete()
                        t.update(1)
                        continue
                try:
                    token.refresh(session=session, auth=auth)
                except (TokenInvalidError, IncompleteResponseError):
                    if use_v1:
                        result = _sso_v1_refresh(session, auth, token, "Post v2 Failure")
                        if result is not True:
                            failures.append(result)
                            if purge:
                                token.delete()
                    else:
                        if purge:
                            token.delete()
                except NotRefreshableTokenError:
                    if purge:
                        token.delete()
                t.update(1)

        self.stdout.write("Completed Updates!")
        self.stdout.write("%s Failures!" % (
            len(failures)
        ))
        self.stdout.write("\n".join(failures))
