import os
from setuptools import find_packages, setup
from esi import __version__

this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-esi',
    version=__version__,
    python_requires='~=3.7',
    install_requires=[
        'requests>=2.9.1,<3.0',
        'requests_oauthlib>=0.8.0,<2.0',
        'django>=2.2,<5',
        'jsonschema<4.0.0',
        'bravado>=10.6.0,<11.0',
        'celery>=4.0.2',
        'python-jose>=3.3.0,<4.0.0',
        'tqdm>=4.62.3,<5'
    ],
    packages=find_packages(),
    include_package_data=True,
    license='GNU General Public License v3 (GPLv3)',
    description='Django app for accessing the EVE Swagger Interface (ESI).',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://gitlab.com/allianceauth/django-esi',
    author='Alliance Auth',
    author_email='adarnof@gmail.com',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 2.2',
        'Framework :: Django :: 3.2',
        'Framework :: Django :: 4.0',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
