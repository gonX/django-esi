# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

[Unreleased] - yyyy-mm-dd

### Changed

- Dropped support for Python 3.5. Django-esi now requires Python 3.6 or higher.

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
