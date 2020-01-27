# Test app for django esi

App for manual testing of key django-esi functionality

## Purpose

The purpose of this app is to allow testing of features of the django-esi app that require user interaction and can therefore not be tested with automated unit tests. This test will try to first acquire an ESI token for the current user and then call an ESI endpoint with that token.

Note that all ESI tokens for that user will be automatically removed at start of the test.

## Installation

This is a normal Django app and can be installed into any existing Django site.

### 1. Install this app into your python environment

```bash
pip install git+https://gitlab.com/allianceauth/django-esi.git/#egg=pkg&subdirectory=esi-test-app
```

### 2. Add this app to your Django site

```python
INSTALLED_APPS += [
    # ...
    'esi_test_app',
    # ...
]
```

### 3. Restart your Django site

Restart your django server.

### 4. Add staff user

If you have not already done so make sure to add a staff user, which is needed to run the test.

The easiest is to just to create a superuser:

```bash
python manage.py createsuperuser
```

## Running the test

The app is locations at `/esi_test_app/`. So when you run it locally the full URL would be: `http://localhost:8000/esi_test_app/`

To run the test open the start page of this app and follow the instructions.

In addition to feedback on screen about the result of the test there will also be a log file created. The name of the log file is `esi_test_api.log` and you find it in your main Django project folder.
