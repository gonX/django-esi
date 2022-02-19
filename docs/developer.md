# Developer Guide

The developer guide describes how to develop apps with *django-esi*.

(section-usage-in-views)=
## Usage in views

### Single token

When views require a token, wrap with the `token_required` decorator and accept a `token` arg:

```python
from esi.decorators import token_required

@token_required(scopes="esi-characters.read_medals.v1")
def my_view(request, token):
    # my code
```

This will prompt the user to either select a token from their current ones, or if none exist create a new one via SSO.

To specify scopes, add either a list of names or a space-delimited string:

```python
@token_required(scopes=['esi-location.read_ship_type.v1', 'esi-location.read_location.v1'])
@token_required(scopes='esi-location.read_ship_type.v1 esi-location.read_location.v1')
```

### New token

To require a new token, such as for logging in, add the `new` argument:

```python
@token_required(new=True)
```

### Multiple tokens

To request all of a user's tokens which have the required scopes, wrap instead with the `tokens_required` decorator and accept a `tokens` arg:

```python
@tokens_required(scopes='esi-location.read_ship_type.v1')
def my_view(request, tokens):
    # my code
```

This skips prompting for token selection and instead passes that responsibility to the view. Tokens are provided as a queryset.

### Single use token

It is also possible to request a token for single use. Single use tokens do not require a user to be logged in and are only available to the current view.

```python
from esi.decorators import single_use_token

@single_use_token(scopes=['publicData'])
my_view(request, token):
    # my code
```

```{seealso}

See API section {ref}`decorators <api-decorators>` for more details on all provided decorators.
```

## Accessing ESI

django-esi provides a convenience wrapper around the [bravado SwaggerClient](https://github.com/Yelp/bravado).

### New approach for getting a client object

All access to ESI happens through a client object that is automatically generated for you and contains all of ESI's routes. The new and **recommended** way of getting that client object is through a single provider instance from the {ref}`EsiClientProvider <api-esiclientprovider>` class.

The new provider approach has two main advantages: First, creating a new client is slow (e.g. can takes up to 5 seconds). So, for maximum performance you want to avoid creating multiple clients in your app. Using the provider automatically ensures this.

Second, the previous approach of creating multiple clients can cause memory leaks.  Especially when used in concurrent environment (e.g. threads or celery tasks), where each worker is creating it's own client.

### Example for creating a provider

The provider needs to be instantiated at "import time", so it must be defined in the global scope of a module.

```python
from esi.clients import EsiClientProvider

# create your own provider
esi = EsiClientProvider()

def main():
    # do stuff with your provider
```

If you need to use the provider in several module than a good pattern is to define it in it's own module, e.g. `providers.py`, and then import the provider instance into all other modules that need an ESI client.

### Using public endpoints

Here is a complete example how to use a public endpoint. Public endpoints can in general be accessed without any authentication.

```python
from esi.clients import EsiClientProvider

# create your own provider
esi = EsiClientProvider()

def main():
    # call the endpoint
    result = esi.client.Status.get_status().results()

    # ... do stuff with the data
    print(result)
```

### Using authenticated endpoints

Non-public endpoints will require authentication. You will therefore need to provide a valid access token with your request.

The following example shows how to retrieve data from a non-public endpoint using an already existing token in your database.

```{seealso}

See also the section {ref}`section-usage-in-views` on how to create tokens in your app.
```

```python
from esi.clients import EsiClientProvider
from esi.models import Token

# create your own provider
esi = EsiClientProvider()

def main():
    character_id = 1234
    required_scopes = ['esi-characters.read_notifications.v1']

    # get a token
    token = Token.get_token(character_id, required_scopes)

    # call the endpoint
    notifications = esi.client.Character.get_characters_character_id_notifications(
        # required parameter for endpoint
        character_id = character_id,
        # provide a valid access token, which wil be refresh the token if required
        token = token.valid_access_token()
    ).results()

    # ... do stuff with the data
```

### results() vs. result()

django-esi offers two similar methods for requesting the response from an endpoint: results() and result(). Here is a quick overview how they differ:

Topic | results() | result()
-- | -- | --
Paging | Automatically returns all pages<br>if they are more than one | Only returns the fist page or the<br>requested page<br>(when specified with page parameter)
Headers | Returns the headers for<br>the last retrieved page | Returns the headers for the first /<br>requested page
Backwards compatibility | New feature in 2.0 | Works mostly as in 1.6

In general we recommend to use results(), so you don't have to worry about paging. Nevertheless, result() gives you more direct control of your API request and has it's uses, e.g when you are only interested in the first page and do not want to wait for all pages to download from the API.

### Getting localized responses from ESI

Some ESI endpoints support localization, which means they are able to return the content localized in one of the supported languages.

To retrieve localized content just provide the language code in your request. The following example will retrieve the type info for the Svipul in Korean:

```Python
result = (
    esi.client.Universe
    .get_universe_types_type_id(type_id=30004984, language='ko')
    .results()
)
```

A common use case it to retrieve localizations for all languages for the current request. For this django-esi provides the convenience method `results_localized()`. It substitutes `results()` and will return the response in all officially supported languages by default.

```Python
result = (
    esi.client.Universe
    .get_universe_types_type_id(type_id=30004984)
    .results_localized()
)
```

Alternatively you can pass the list of languages (as language code) that you are interested in:

```Python
result = (
    esi.client.Universe
    .get_universe_types_type_id(type_id=30004984)
    .results_localized(languages=['ko', 'de'])
)
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

## User Agent header

CCP asks developers to provide a "good User-Agent header" with all requests to ESI, so that CCP can identify which app the request belongs to and is able to contact the server owner running the app in case of any issues. This requirement is specified in the CCP's [Developer Guidelines](https://developers.eveonline.com/resource/resources) and detailed in the [ESI guidelines](https://docs.esi.evetech.net/docs/guidelines.html).

Django-esi provides two features for setting the User-Agent header:

### Application Info

You configure the User-Agent to represent your application by setting the `app_info_text` parameter when creating a client with {ref}`EsiClientProvider <api-esiclientprovider>` or with {ref}`esi_client_factory <api-esiclientfactory>`.

There is no official format for the User-Agent, but we would suggest including the distribution name (same as e.g. in your `setup.py`) and current version of your application like so:

```Python
"my-app v1.0.0"
```

Here is a complete example for defining an application string with your app:

```python
from esi.clients import EsiClientProvider

esi = EsiClientProvider(app_info_text="my-app v1.0.0")
```

```{hint}

Spaces are used as delimiter in the User Agent, so your application name should not include any.
```

```{note}

If you do not define an application string, the application string used will be `"django-esi vX.Y.Z"`.
```

### Contact email

To enable CCP to contact the maintainer of a server that is using ESI it is important to specify a contact email. This can be done through the setting ESI_USER_CONTACT_EMAIL.

Example:

```python
ESI_USER_CONTACT_EMAIL = "admin@example.com"
```

In case you are not hosting the app yourself, we would recommend including this setting in the installation guide for your app.

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

## Advanced Features

### Using a local spec file

Specifying resource versions introduces one major problem for shared code: not all resources nor all their operations are available on any given version. This can be addressed by shipping a copy of the [versioned latest spec](https://esi.tech.ccp.is/_latest/swagger.json) with your app. **This is the preferred method for deployment.**

To build a client using this local spec, pass an additional parameter `spec_file` which contains the path to your local swagger.json:

```python
from esi.clients import EsiClientProvider

esi = EsiClientProvider(spec_file='/path/to/swagger.json')
```

For example, a swagger.json in the current file's directory would look like:

```python
import os
from esi.clients import EsiClientProvider

SWAGGER_SPEC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'swagger.json')
esi = EsiClientProvider(spec_file=SWAGGER_SPEC)

```

If a `spec_file` is specified all other versioning is unavailable: ensure you ship a spec with resource versions your app can handle.

### Getting Response Data

Sometimes you may want to also get the internal response object from an ESI response. For example to inspect the response header. For that simply set the `request_config.also_return_response` to `True` and then call the endpoint. This works in the same way for both `.result()` and `.results()`

```python
from esi.clients import EsiClientProvider
from esi.models import Token

# create your own provider
esi = EsiClientProvider()

def main():
    character_id = 1234
    required_scopes = ['esi-characters.read_notifications.v1']

    # get a token
    token = Token.get_token(character_id, required_scopes)

    # call the endpoint but don't request data.
    operation = esi.client.Character.get_characters_character_id_notifications(
        character_id = character_id,
        token = token.valid_access_token()
    )

    # set to get the response as well
    operation.request_config.also_return_response = True

    # get your data
    notifications, response = operation.results()

    # ... do stuff with the data
    print(response.headers['Expires'])

```

### Accessing alternate data sources

ESI data source can also be specified during client creation:

```python
from esi.clients import EsiClientProvider
from esi.models import Token

# create your own provider
esi = EsiClientProvider(datasource='tranquility')
```

Currently the only available data source is `tranquility`, which is also the default The previously available datasource `singularity` is no longer available.
