from django.contrib import admin
from django.contrib.auth import get_user_model

from .models import Token, Scope, CallbackRedirect

admin.site.register(CallbackRedirect)


@admin.register(Scope)
class ScopeAdmin(admin.ModelAdmin):
    list_display = ('name', 'help_text')


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    def get_scopes(self, obj):
        return ", ".join([x.name for x in obj.scopes.all()])

    get_scopes.short_description = 'Scopes'

    User = get_user_model()
    list_display = ('user', 'character_name', 'get_scopes')
    search_fields = ['user__%s' % User.USERNAME_FIELD, 'character_name', 'scopes__name']
