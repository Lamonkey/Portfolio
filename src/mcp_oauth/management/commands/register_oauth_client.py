"""Register a new OAuth client for the Portfolio MCP server.

Prints the client_id and client_secret to stdout once. The secret is stored
plaintext in the DB and cannot be retrieved later; copy it immediately into
the client (e.g. claude.ai's custom-connector form).

Example:
    python manage.py register_oauth_client \\
        --name "Claude.ai" \\
        --redirect-uri "https://claude.ai/api/mcp/auth/callback"
"""
from __future__ import annotations

import secrets

from django.core.management.base import BaseCommand, CommandError

from mcp_oauth.models import OAuthClient


class Command(BaseCommand):
    help = "Register a new OAuth client and print its credentials once."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True, help="Human-friendly client name.")
        parser.add_argument(
            "--redirect-uri",
            required=True,
            action="append",
            help="Allowed redirect URI. Pass multiple times for multiple URIs.",
        )
        parser.add_argument(
            "--scope",
            action="append",
            default=[],
            help="Allowed scope. Pass multiple times for multiple scopes. Empty means unrestricted.",
        )

    def handle(self, *args, **options):
        name: str = options["name"]
        redirect_uris: list[str] = options["redirect_uri"]
        scopes: list[str] = options["scope"]

        if any(not (u.startswith("http://") or u.startswith("https://")) for u in redirect_uris):
            raise CommandError("redirect-uri values must be absolute http(s) URLs.")

        client_id = "mcl_" + secrets.token_urlsafe(16)
        client_secret = "mcs_" + secrets.token_urlsafe(40)

        OAuthClient.objects.create(
            client_id=client_id,
            client_secret=client_secret,
            name=name,
            redirect_uris=redirect_uris,
            scopes=scopes,
        )

        self.stdout.write(self.style.SUCCESS(f"Registered OAuth client '{name}'."))
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Copy these now — the secret will not be shown again:"))
        self.stdout.write("")
        self.stdout.write(f"  client_id:     {client_id}")
        self.stdout.write(f"  client_secret: {client_secret}")
        self.stdout.write("")
        self.stdout.write(f"  redirect_uris: {', '.join(redirect_uris)}")
        if scopes:
            self.stdout.write(f"  scopes:        {', '.join(scopes)}")
