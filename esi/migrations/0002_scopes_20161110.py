# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-11-10 23:31
from __future__ import unicode_literals

from django.db import migrations

SCOPES = {
    'read_calendar_events': "Allows reading a character's calendar, including corporate events.",
    'read_character_wallet': "Allows reading of a character's wallet, journal and transaction history.",
    'read_clones': "Allows reading the locations of a character's jump clones and their implants.",
    'read_contacts': "Allows reading of a character's contacts list, and calculation of CSPA charges.",
    'read_skillqueue': "Allows reading of a character's currently training skill queue.",
    'read_skills': "Allows reading of a character's currently known skills.",
    'read_structures': 'Allows querying the location and type of structures that the character has docking access at.',
    'respond_calendar_events': "Allows updating of a character's calendar event responses.",
}


def generate_scopes(apps, schema_editor):
    Scope = apps.get_model('esi', 'Scope')
    for s in SCOPES:
        Scope.objects.update_or_create(name=s, defaults={'help_text': SCOPES[s]})


def delete_scopes(apps, schema_editor):
    Scope = apps.get_model('esi', 'Scope')
    for s in SCOPES:
        try:
            Scope.objects.get(name=s).delete()
        except Scope.DoesNotExist:
            pass


class Migration(migrations.Migration):
    dependencies = [
        ('esi', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(generate_scopes, delete_scopes)
    ]
