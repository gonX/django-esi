===============
API
===============

This chapter contains the developer reference documentation of the public API for *django-esi*.

clients
===========

.. _api-esiclientprovider:

.. autoclass:: esi.clients.CachingHttpFuture
    :members:

.. autoclass:: esi.clients.EsiClientProvider

.. _api-esiclientfactory:

.. autofunction:: esi.clients.esi_client_factory

.. _api-decorators:

decorators
===========

.. automodule:: esi.decorators
    :members:
    :undoc-members:

errors
===========

.. automodule:: esi.errors
    :members:
    :undoc-members:


models
===========

.. autoclass:: esi.models.Token
    :members:
    :exclude-members: DoesNotExist, MultipleObjectsReturned, get_token_data, update_token_data


managers
===========

.. autoclass:: esi.managers.TokenQueryset
    :members:
    :undoc-members:
