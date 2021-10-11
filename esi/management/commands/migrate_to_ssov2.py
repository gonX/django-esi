from django.core.management.base import BaseCommand, CommandError

from django.db.migrations.recorder import MigrationRecorder
from django.utils import timezone

from esi.models import Token
from esi.errors import TokenInvalidError, IncompleteResponseError, \
    NotRefreshableTokenError
from esi import app_settings
from oauthlib.oauth2.rfc6749.errors import (
    InvalidClientIdError,
    InvalidGrantError,
    InvalidTokenError,
)
from requests.auth import HTTPBasicAuth

from tqdm import tqdm

from requests_oauthlib import OAuth2Session


class Command(BaseCommand):
    help = 'Attempt to Migrate all SSOv1 Tokens to SSOv2, and report failures.'
    requires_migrations_checks = True
    requires_system_checks = True

    def handle(self, *args, **options):
        migration_10 = MigrationRecorder.Migration.objects.filter(
            app='esi', name="0010_set_new_tokens_to_sso_v2").exists()

        if not migration_10:
            raise CommandError("Run migrations first and try again!")
        else:
            self.stdout.write("\n\nMigrations up to date. Proceeding to updates!")

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
        non_refreshables = 0
        # Nice Progress bar as this may take a while.
        with tqdm(total=total) as t:
            for token in tokens:
                try:
                    token.refresh(session=session, auth=auth)

                except (TokenInvalidError, IncompleteResponseError):
                    try:
                        token = session.refresh_token(
                            "https://login.eveonline.com/v2/oauth/token",
                            refresh_token=token.refresh_token,
                            auth=auth
                        )

                        token.access_token = token['access_token']
                        token.refresh_token = token['refresh_token']
                        token.sso_version = 1
                        token.created = timezone.now()
                        token.save()
                        failures.append("ID:%s for %s SSOv1 Refresh Successful" % (token.id, token.character_name))

                    except (InvalidGrantError):
                        # self.stdout.write("InvalidGrantError Fail SSOv1")
                        failures.append("ID:Deleted for %s" % (token.character_name))
                        token.delete()
                        non_refreshables += 1
                    except (InvalidTokenError, InvalidClientIdError):
                        # self.stdout.write("InvalidTokenError, InvalidClientIdError Fail SSOv1")
                        failures.append(
                            "ID:%s for %s SSOv1 Refresh Failed "
                            "(InvalidTokenError, InvalidClientIdError)" % (token.id, token.character_name))
                    except Exception as e:
                        # self.stdout.write("Exception Fail SSOv1 %s" % e)
                        failures.append(
                            "ID:%s for %s SSOv1 Refresh Failed (%s)" % (token.id, token.character_name, e))

                except NotRefreshableTokenError:
                    non_refreshables += 1  # wat do FC...
                t.update(1)

        self.stdout.write("Completed Updates!")
        self.stdout.write("%s Failures and %s non-refreshable tokens!" % (
            len(failures), non_refreshables
        ))
        self.stdout.write("\n".join(failures))
