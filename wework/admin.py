from django.contrib import admin
from .models import AccessToken


@admin.register(AccessToken)
class AccessTokenAdmin(admin.ModelAdmin):
    list_display = ('create', 'expires_in', 'key')
