# Operations Guide

The operations guide describes how to install, configure and maintain *django-esi*.

## Installation

To install django-esi into your Django project please follow the these steps:

### Step 1: Install the latest version directly from PyPI

```bash
pip install django-esi
```

### Step 2: Add `esi` to your `INSTALLED_APPS` setting

```python
INSTALLED_APPS += [
    # other apps
    'esi',
    # other apps
]
```

### Step 3: Include the esi urlconf in your project's urls

```python
url(r'^sso/', include('esi.urls', namespace='esi')),
```

### Step 4: Register an application with the [EVE Developers site](https://developers.eveonline.com/applications)

If your application requires scopes, select **Authenticated API Access** and register all possible scopes your app can request. Otherwise **Authentication Only** will suffice.

Set the **Callback URL** to `https://example.com/sso/callback`

### Step 4: Add SSO client settings to your project settings

```python
ESI_SSO_CLIENT_ID = "my client id"
ESI_SSO_CLIENT_SECRET = "my client secret"
ESI_SSO_CALLBACK_URL = "https://example.com/sso/callback"
```

### Step 5: Run migrations to create models

```bash
python manage.py migrate
```

## Upgrade

To update an existing installation please first make sure that you are in your virtual environment and in the main project folder (the one that has `manage.py`). Then run the following commands one by one:

```bash
pip install -U django-esi
```

```bash
python manage.py migrate
```

```bash
python manage.py collectstatic
```

Finally restart your Django application, e.g. by restarting your supervisors.

## Settings

Django-esi can be configured through settings by adding them to your Django settings file. Here is the list of the most commonly used settings:

### Required settings

Required settings need to be set in order for django-esi to function.

```{eval-rst}
.. automodule:: esi.app_settings
    :members: ESI_SSO_CLIENT_ID, ESI_SSO_CLIENT_SECRET, ESI_SSO_CALLBACK_URL
    :noindex:
```

```{hint}

These settings can be left blank if DEBUG is set to True.
```

### Optional settings

Optional settings will use the documented default if they are not set.

```{eval-rst}
.. automodule:: esi.app_settings
    :members:
    :exclude-members: ESI_SSO_CLIENT_ID, ESI_SSO_CLIENT_SECRET, ESI_SSO_CALLBACK_URL
```

```{seealso}

For a list of all settings please see ``esi.app_settings``.
```
