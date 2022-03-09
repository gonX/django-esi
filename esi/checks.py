from django.core.checks import Error, Warning, register, Tags
from django.conf import settings


@register(Tags.security)
def check_sso_application_settings(*args, **kwargs):
    errors = []
    if (
        not hasattr(settings, "ESI_SSO_CLIENT_ID")
        or not hasattr(settings, "ESI_SSO_CLIENT_SECRET")
        or not hasattr(settings, "ESI_SSO_CALLBACK_URL")
    ):
        if settings.DEBUG:
            errors.append(
                Warning(
                    'ESI SSO application settings are not configured.',
                    hint='SSO features will not work.',
                    id='esi.W001'
                )
            )
        else:
            errors.append(
                Error(
                    'ESI SSO application settings cannot be blank.',
                    hint=(
                        'Register an application at https://developers.eveonline.com '
                        'and add ESI_SSO_CLIENT_ID, ESI_SSO_CLIENT_SECRET, and '
                        'ESI_SSO_CALLBACK_URL to your project settings.'
                    ),
                    id='esi.E001'
                )
            )
    return errors
