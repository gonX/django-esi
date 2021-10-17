# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased] - yyyy-mm-dd

## [3.0.0] - 2021-10-17

### Changed

- Updated to SSOv2, A manual migration task (see below) is provided for maximum compatability and reliability

## Migrating to Django-ESI v3.0.0
**Please don't run this close to DT, Larger installs are encouraged to run in batches**
 1. Stop services. `supervisorctl stop myauth:*`
 2. Purge celery queue. `celery -A myauth purge`
 3. Pip install. `pip install -U django-esi`
 4. Migrations. `python myauth/manage.py migrate`
 5. Update command. `python myauth/manage.py migrate_to_ssov2`
    - Additional Options
      - `--purge` Deletes invalid tokens
      - `--skip-v1-checks` Skips SSOv1 verifications
      - `-n #` Migrate a batch, where # is the number of tokens to migrate
 6. Restart everything. `supervisorctl start myauth:*`

## [2.1.1] - 2021-09-30

### Changed

- Capped version of `jsonschema` below 4.0.0 due to incompatibilities. [49](https://gitlab.com/allianceauth/django-esi/-/merge_requests/49)

## [2.1.0] - 2021-07-24

### Important update notes

If you have recently installed django-esi with Django 3.2 and are using `BigAutoField` as default for automatically created primary keys, then Django might already have automatically created an additional migration for auto fields.

To prevent this update from creating another migration we recommend to migrate django-esi back to the previous migration and remove the auto field migration **before(!!!)** updating to this version.

You can use this command to check if you have an auto field migration:

```bash
python manage.py showmigrations esi
```

The last official migration is `0008_nullable_refresh_token`. The auto field migration would be 0009. If you do not have a 0009 migration no further action is required.

You can then migrate back to 0008 with this command:

```bash
python manage.py migrate esi 0008
```

Finally, delete the automatically generated 0009 migration for django-esi from your system.

See the [official documentation](https://docs.djangoproject.com/en/3.2/releases/3.2/#customizing-type-of-auto-created-primary-keys) for more information about the new default for automatically creates primary keys.

### Added

- Add support for Django 3.2
- Add support for Python 3.9
- Add documentation on read-the-docs incl. API docs

### Changed

- Remove support for Django 3.0 (EOL on 01 Apr 2021)

### Changed

- Reduce load time, add filters and default ordering for token admin page

## [2.0.5] - 2020-11-11

### Changed

- Display improvements to the token selection screen https://gitlab.com/allianceauth/django-esi/-/merge_requests/38

## [2.0.4] - 2020-11-11

### Added

- Adds a User-Agent header as per the ESI Developer best practice https://gitlab.com/allianceauth/django-esi/-/merge_requests/42

### Developer

- Code Style changes, Implementing Pre-Commit Flake8 Checks https://gitlab.com/allianceauth/django-esi/-/merge_requests/43

## [2.0.3] - 2020-11-11

### Fixed

- Migration support for MySQL8 https://gitlab.com/allianceauth/django-esi/-/merge_requests/37
- Retry fixes, Adds Custom Retries https://gitlab.com/allianceauth/django-esi/-/merge_requests/39
- Cache Exception handling https://gitlab.com/allianceauth/django-esi/-/merge_requests/40

## [2.0.2] - 2020-10-01

### Fixed

- Django 3.0,3.1 Support and Testing https://gitlab.com/allianceauth/django-esi/-/merge_requests/35
- use image.evetech CDN https://gitlab.com/allianceauth/django-esi/-/merge_requests/36

## [2.0.1] - 2020-09-09

### Fixed

- Fails with "UnicodeDecodeError" if a system's default encoding is not UTF-8

## [2.0.0] - 2020-06-28

### Added

- New approach for creating a client that prevents memory leaks and is faster. (See also `EsiClientProvider`)
- New "result" method `results()` that automatically handles paging of the response
- New "result" method `results_localized()` that automatically returns the response in all supported languages and with paging
- New Token method `valid_access_token()` to directly get a valid access token
- Automatic retries on common HTTP and connection errors
- Default timeouts for all connections
- Option for increasing the connection pool to enable many parallel requests
- (optional) info and debug logging

### Changed

- Dropped support for Python 3.5. Django-esi now requires Python 3.6 or higher.
- Breaking change: The approach for getting the full response from ESI has changed. (See also section "Advanced Usage"):
  - Before: `operation.also_return_response = True`.
  - Now: `operation.request_config.also_return_response = True`

### Fixed

- Several bugfixes and performance improvements

## [1.6.1] - 2020-04-15

### Fixed

- ESI does not support redirect URLs longer than 254 chars [#8](https://gitlab.com/allianceauth/django-esi/issues/8)

## [1.6.0] - 2020-02-18

### Changed

- Updated Token select screen to be more mobile friendly. [!15](https://gitlab.com/allianceauth/django-esi/-/merge_requests/15)

### Added

- Single use token view decorator. [!16](https://gitlab.com/allianceauth/django-esi/-/merge_requests/16)
- Test App for full development testing. [#4](https://gitlab.com/allianceauth/django-esi/issues/4)

## [1.5.2] - 2020-01-14

### Changed

- Decoupled Django template from the AllianceAuth template structure [#6](https://gitlab.com/allianceauth/django-esi/issues/6)

## [1.5.1] - 2020-01-10

### Added

- Add automated tests for all supported Python versions [#5](https://gitlab.com/allianceauth/django-esi/issues/5)

### Fixed

- Minor bug in views.sso_redirect function related to sessions

## [1.5.0] - 2020-01-08

### Added

- Unit test suite
- Fix for caching bug [#2](https://gitlab.com/allianceauth/django-esi/issues/2)
- Test framework to enable CI/CD
- Change Log

### Changed

- Package renamed from adarnauth-esi to django-esi [#3](https://gitlab.com/allianceauth/django-esi/issues/3)
- Adopt app to work with requests-oauthlib 1.3.0 [#1](https://gitlab.com/allianceauth/django-esi/issues/1)

### Fixed


## [1.4.14] - 2018-06-06

- Initial fork from [adarnauth-esi](https://gitlab.com/Adarnof/adarnauth-esi)
