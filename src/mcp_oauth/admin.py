from django.contrib import admin

from .models import OAuthAccessToken, OAuthAuthCode, OAuthClient


@admin.register(OAuthClient)
class OAuthClientAdmin(admin.ModelAdmin):
    list_display = ("client_id", "name", "created_at")
    search_fields = ("client_id", "name")
    readonly_fields = ("created_at",)
    # client_secret is hidden from list view but visible on the detail page so
    # the admin can copy it if a credential is lost (still plaintext on disk).


@admin.register(OAuthAuthCode)
class OAuthAuthCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "client", "expires_at", "used", "created_at")
    list_filter = ("used", "client")
    search_fields = ("code", "client__name")
    readonly_fields = ("code", "client", "code_challenge", "redirect_uri", "scopes", "expires_at", "created_at")


@admin.register(OAuthAccessToken)
class OAuthAccessTokenAdmin(admin.ModelAdmin):
    list_display = ("token", "client", "expires_at", "issued_at")
    list_filter = ("client",)
    search_fields = ("token", "client__name")
    readonly_fields = ("token", "client", "scopes", "expires_at", "issued_at")
