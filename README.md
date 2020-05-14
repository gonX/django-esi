# django-esi

Django app for easy access to the EVE Swagger Interface (ESI)

[![version](https://img.shields.io/pypi/v/django-esi)](https://pypi.org/project/django-esi/)
[![python](https://img.shields.io/pypi/pyversions/django-esi)](https://pypi.org/project/django-esi/)
[![django](https://img.shields.io/pypi/djversions/django-esi)](https://pypi.org/project/django-esi/)
[![license](https://img.shields.io/badge/license-GPLv3-green)](https://pypi.org/project/django-esi/)
[![pipeline-status](https://gitlab.com/allianceauth/django-esi/badges/master/pipeline.svg)](https://gitlab.com/allianceauth/django-esi/pipelines)
[![coverage](https://gitlab.com/allianceauth/django-esi/badges/master/coverage.svg)](https://gitlab.com/allianceauth/django-esi/pipelines)
[![Chat on Discord](https://img.shields.io/discord/399006117012832262.svg)](https://discord.gg/fjnHAmk)

## Contents

- [Overview](#overview)
- [Installation](#installation)
- [Usage in views](#usage-in-views)
- [Accessing ESI](#accessing-esi)
- [Cleaning the database](#cleaning-the-database)
- [Operating on singularity](#operating-on-singularity)
- [History of this app](#operating-on-singularity)
- [Change log](CHANGELOG.md)

## Overview

Django-esi is a Django app that provides an interface for easy access to the EVE Swagger Interface (ESI), the official API for the game [EVE Online](https://www.eveonline.com/).

It is build upon [Bravado](https://github.com/Yelp/bravado) - a python client library for Swagger 2.0 services.  

Django-esi adds the following main functionalities to a Django site:

- Dynamically generated client for interacting with public and private ESI endpoints
- Support for adding EVE SSO to authenticate characters and retrieve tokens
- Control over ESI endpoint versions

## Installation

1. Install the latest version directly from PyPI:

    `pip install django-esi`

1. Add `esi` to your `INSTALLED_APPS` setting:

   `INSTALLED_APPS += 'esi'`

1. Include the esi urlconf in your project's urls:

    `url(r'^sso/', include('esi.urls', namespace='esi')),`

1. Register an application with the [EVE Developers site](https://developers.eveonline.com/applications)

    If your application requires scopes, select `Authenticated API Access` and register all possible scopes your app can request. Otherwise `Authentication Only` will suffice.
    Set the `Callback URL` to `https://example.com/sso/callback`

1. Add SSO client settings to your project settings:

    `ESI_SSO_CLIENT_ID = "my client id"`<br>
    `ESI_SSO_CLIENT_SECRET = "my client secret"`<br>
    `ESI_SSO_CALLBACK_URL = "https://example.com/sso/callback"`

1. Run `python manage.py migrate` to create models.

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

## Usage in views

When views require a token, wrap with the `token_required` decorator and accept a `token` arg:

```python
from esi.decorators import token_required

@token_required()
def my_view(request, token):
    ...
```

This will prompt the user to either select a token from their current ones, or if none exist create a new one via SSO.

To specify scopes, add either a list of names or a space-delimited string:

```python
@token_required(scopes=['esi-location.read_ship_type.v1', 'esi-location.read_location.v1'])
@token_required(scopes='esi-location.read_ship_type.v1 esi-location.read_location.v1')
```

To require a new token, such as for logging in, add the `new` argument:

```python
@token_required(new=True)
```

To request all of a user's tokens which have the required scopes, wrap instead with the `tokens_required` decorator and accept a `tokens` arg:

```python
@tokens_required(scopes='esi-location.read_ship_type.v1')
def my_view(request, tokens):
    # my code
```

This skips prompting for token selection and instead passes that responsibility to the view. Tokens are provided as a queryset.

To require a single use token regardless of login state, add the `single_use_token` decorator with the scopes required:

```python
from esi.decorators import single_use_token

@single_use_token(scopes=['publicData'])
my_view(request, token):
    # my code
```

## Accessing ESI

django-esi provides a convenience wrapper around the [bravado SwaggerClient](https://github.com/Yelp/bravado), and a basic client provider that can be extended.

The **recommended** way of using a client is to create a provider and in the provider expose a client. creating clients on the fly is slow and also can create memory leaks.

For example in its most basic form;

### Example `providers.py`
```python
from esi.clients import EsiClientProvider

esi = EsiClientProvider()
```

### Using public endpoints
```python
from . import providers

# call the endpoint
result = providers.esi.client.Status.get_status().result()

# ... do stuff with the data
print(result)
```

### Using authenticated endpoints
Simply add the token param to the operation.
```python
from . import providers
from esi.models import Token

character_id = 1234
required_scopes = ['esi-characters.read_notifications.v1']

# get a token 
token = Token.get_token(character_id, required_scopes)

# call the endpoint
notifications = providers.esi.client.Character.get_characters_character_id_notifications(
    character_id = character_id,  # required paramater for endpoint
    token = token.valid_access_token()  # refresh the token if required and auth the endpoint
    ).result()

# ... do stuff with the data
```

### Getting all pages of an endpoint
`djagno-esi` has a convenient wrapper that will fetch all the pages of data from an ESI endpoint are return it as if it was a single page.

One caveat being that you will only get the last pages response if you ask for response with the result data.

```python
from . import providers
from esi.models import Token

character_id = 1234
corporation_id = 5678
required_scopes = ['esi-assets.read_corporation_assets.v1']

# get a token 
token = Token.get_token(character_id, required_scopes)

# call the endpoint
assets = providers.esi.client.Assets.get_corporations_corporation_id_assets(
    corporation_id=corporation_id,
    token=token.valid_access_token()
    ).result_all_pages()

# ... do stuff with the data
```

### Specifying resource versions

As explained on the [EVE Developers Blog](https://developers.eveonline.com/blog/article/breaking-changes-and-you), it's best practice to call a specific version of the resource and allow the ESI router to map it to the correct route, being `legacy`, `latest` or `dev`.

Client initialization begins with a base swagger spec. By default this is the version defined in settings (`ESI_API_VERSION`), but can be overridden with an extra argument to the factory:

```python
client = esi_client_factory(version='v4')
```

Only resources with the specified version number will be available. For instance, if you specify `v4` but `Universe` does not have a `v4` version, it will not be available to that specific client. Only `legacy`, `latest` and `dev` are guaranteed to have all resources available.

Individual resources are versioned and can be accessed by passing additional arguments to the factory:

```python
client = esi_client_factory(Universe='v1', Character='v3')
```

A list of available resources is available on the [EVE Swagger Interface browser](https://esi.tech.ccp.is). If the resource is not available with the specified version, an `AttributeError` will be raised.

This version of the resource replaces the resource originally initialized. If the requested base version does not have the specified resource, it will be added.

Note that only one old revision of each resource is kept available through the legacy route. Keep an eye on the [deployment timeline](https://github.com/ccpgames/esi-issues/projects/2/) for resource updates.

## Cleaning the database

Two tasks are available:

- `cleanup_callbackredirect` removes all `CallbackRedirect` models older than a specified age (in seconds). Default is 300.
- `cleanup_token` checks all `Token` models, and if expired, attempts to refresh. If expired and cannot refresh, or fails to refresh, the model is deleted.

To schedule these automatically with celerybeat, add them to your settings.py `CELERYBEAT_SCHEDULE` dict like so:

```python
from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    ...
    'esi_cleanup_callbackredirect': {
        'task': 'esi.tasks.cleanup_callbackredirect',
        'schedule': crontab(hour='*/4'),
    },
    'esi_cleanup_token': {
        'task': 'esi.tasks.cleanup_token',
        'schedule': crontab(day_of_month='*/1'),
    },
}
```

Recommended intervals are four hours for callback redirect cleanup and daily for token cleanup (token cleanup can get quite slow with a large database, so adjust as needed). If your app does not require background token validation, it may be advantageous to not schedule the token cleanup task, instead relying on the validation check when using `@token_required` decorators or adding `.require_valid()` to the end of a query.

## Advanced Use

### Using a local spec file

Specifying resource versions introduces one major problem for shared code: not all resources nor all their operations are available on any given version. This can be addressed by shipping a copy of the [versioned latest spec](https://esi.tech.ccp.is/_latest/swagger.json) with your app. **This is the preferred method for deployment.**

To build a client using this local spec, pass an additional kwarg `spec_file` which contains the path to your local swagger.json:

```python
c = esi_client_factory(spec_file='/path/to/swagger.json')
```

For example, a swagger.json in the current file's directory would look like:

```python
c = esi_client_factory(
    spec_file=os.path.join(os.path.dirname(os.path.abspath(__file__)),
    'swagger.json')
)
```

If a `spec_file` is specified all other versioning is unavailable: ensure you ship a spec with resource versions your app can handle.

### Example `providers.py` with a spec file.

You can also use a spec file with the included `BaseEsiResponseClient` class to create a provider class with a local spec file.

```python
import os
from esi.providers import BaseEsiResponseClient

SWAGGER_SPEC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'swagger.json')

esi = BaseEsiResponseClient(spec_file=SWAGGER_SPEC)
```

### Getting Response Data
Simply set the `request_config.also_return_response` to `True` and then call the endpoint. This works int eh same way for both `.result()` and `.result_all_pages()`

```python
from . import providers
from esi.models import Token

character_id = 1234
required_scopes = ['esi-characters.read_notifications.v1']

# get a token 
token = Token.get_token(character_id, required_scopes)

# call the endpoint but don't request data.
operation = providers.esi.client.Character.get_characters_character_id_notifications(
    character_id = character_id,  # required paramater for endpoint
    token = token.valid_access_token()  # refresh the token if required and auth the endpoint
    )

# set to get the response as well
operation.request_config.also_return_response = True

# get your data
notifications, response = operation.result()

# ... do stuff with the data
print(response.headers['Expires'])

```

### Accessing alternate data sources

ESI data source can also be specified during client creation:

```python
client = esi_client_factory(datasource='tranquility')
```

Currently the only available data source is `tranquility`. The `singularity` was shutdown by CCP.

## History of this app

This app is a fork from [adarnauth-esi](https://gitlab.com/Adarnof/adarnauth-esi). Since this app is an important component of the [Alliance Auth](https://gitlab.com/allianceauth/allianceauth) system and Adarnof - the original author - was no longer able to maintain it the AA dev team has decided in December 2019 to take over maintenance and further developing for this app within the Alliance Auth project.
