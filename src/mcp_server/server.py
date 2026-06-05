"""MCP server exposing CRUD access to the portfolio Project model.

Mounted under /mcp by Portfolio.asgi via Starlette routing.
"""
import os
from typing import Optional

from asgiref.sync import sync_to_async
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl


def _build_transport_security() -> TransportSecuritySettings | None:
    """Build DNS-rebinding-protection settings from env vars.

    FastMCP auto-enables DNS rebinding protection with a localhost-only
    allowlist when ``transport_security`` is ``None``. That works in
    local development but rejects every request in production with a
    421 "Invalid Host header" response. Override by supplying:

    - ``MCP_ALLOWED_HOSTS``: comma-separated host header values to allow
      (e.g. ``example.com,api.example.com``). Wildcard ports via ``:*``.
    - ``MCP_ALLOWED_ORIGINS``: comma-separated Origin header values for
      browser-based clients (e.g. ``https://example.com``).

    When neither env var is set, ``None`` is returned so FastMCP falls
    back to its built-in localhost defaults.
    """
    extra_hosts = [h.strip() for h in os.getenv("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]
    extra_origins = [o.strip() for o in os.getenv("MCP_ALLOWED_ORIGINS", "").split(",") if o.strip()]
    if not extra_hosts and not extra_origins:
        return None
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "127.0.0.1:*",
            "localhost:*",
            "[::1]:*",
            *extra_hosts,
        ],
        allowed_origins=[
            "http://127.0.0.1:*",
            "http://localhost:*",
            "http://[::1]:*",
            *extra_origins,
        ],
    )


def _build_auth() -> tuple[object | None, AuthSettings | None]:
    """Optionally enable OAuth 2.0 on the MCP endpoint.

    ``MCP_OAUTH_ISSUER_URL`` is the toggle: when set, FastMCP wires up
    ``/authorize``, ``/token``, and the well-known metadata endpoints, and
    every ``/mcp`` request is validated via ``DjangoOAuthProvider.load_access_token``.
    When unset, the server falls back to the legacy ``BearerAuthMiddleware``
    + ``MCP_TOKEN`` flow (kept for local dev convenience).
    """
    issuer = os.getenv("MCP_OAUTH_ISSUER_URL")
    if not issuer:
        return None, None

    # Imports kept lazy so the module can be imported without Django set up
    # (e.g. by sphinx, ad-hoc scripts).
    from mcp_oauth.provider import DjangoOAuthProvider

    resource = os.getenv("MCP_OAUTH_RESOURCE_URL", issuer)
    return DjangoOAuthProvider(), AuthSettings(
        issuer_url=AnyHttpUrl(issuer),
        resource_server_url=AnyHttpUrl(resource),
        # Enable Dynamic Client Registration (RFC 7591). OAuth-only clients like
        # Claude.ai self-register at /token-less /register instead of accepting a
        # hand-issued client_id/secret. Secrets never expire (matches the model,
        # which has no expiry column). The /authorize superuser gate, not
        # registration, is the security boundary.
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            client_secret_expiry_seconds=None,
        ),
    )


_provider, _auth_settings = _build_auth()

mcp = FastMCP(
    "portfolio",
    stateless_http=True,
    transport_security=_build_transport_security(),
    auth_server_provider=_provider,
    auth=_auth_settings,
)


def _project_to_dict(project, include_description: bool) -> dict:
    image_url = None
    try:
        if project.image:
            image_url = project.image.url
    except ValueError:
        image_url = None

    data = {
        "id": project.id,
        "title": project.title,
        "subtitle": project.subtitle,
        "type": project.type,
        "link": project.link,
        "github_link": project.github_link,
        "image_url": image_url,
    }
    if include_description:
        data["description"] = project.description
        data["meta_description"] = project.meta_description
    return data


@mcp.tool()
async def list_projects() -> list[dict]:
    """List every portfolio project with summary fields (no description body)."""
    from homepage.models import Project

    def _fetch():
        return [
            _project_to_dict(p, include_description=False)
            for p in Project.objects.all().order_by("-id")
        ]

    return await sync_to_async(_fetch)()


@mcp.tool()
async def get_project(project_id: int) -> dict:
    """Get full details for one project by its database id, including the raw markdown description."""
    from homepage.models import Project

    def _fetch():
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return None
        return _project_to_dict(project, include_description=True)

    result = await sync_to_async(_fetch)()
    if result is None:
        raise ValueError(f"Project {project_id} not found")
    return result


@mcp.tool()
async def create_project(
    title: str,
    subtitle: str = "",
    type: str = "",
    link: Optional[str] = None,
    github_link: Optional[str] = None,
    description: Optional[str] = None,
    meta_description: str = "",
) -> dict:
    """Create a new portfolio project.

    `subtitle` is a short one-liner shown on the list-page card.
    `description` is the long-form story/markdown shown on the detail page.
    `meta_description` is the SEO snippet (~120-160 chars) used in
    <meta name="description"> and og:description; if blank it falls back
    to subtitle then to a truncated description.

    Image upload is not supported via MCP; the project is created without an image.
    """
    from homepage.models import Project

    def _create():
        project = Project.objects.create(
            title=title,
            subtitle=subtitle,
            type=type,
            link=link,
            github_link=github_link,
            description=description,
            meta_description=meta_description,
        )
        return _project_to_dict(project, include_description=True)

    return await sync_to_async(_create)()


@mcp.tool()
async def update_project(
    project_id: int,
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    type: Optional[str] = None,
    link: Optional[str] = None,
    github_link: Optional[str] = None,
    description: Optional[str] = None,
    meta_description: Optional[str] = None,
) -> dict:
    """Partial-update an existing project. Only fields explicitly passed (non-null) are written.

    To clear a field, pass an empty string explicitly (e.g. `subtitle=""`).
    """
    from homepage.models import Project

    def _update():
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return None
        if title is not None:
            project.title = title
        if subtitle is not None:
            project.subtitle = subtitle
        if type is not None:
            project.type = type
        if link is not None:
            project.link = link
        if github_link is not None:
            project.github_link = github_link
        if description is not None:
            project.description = description
        if meta_description is not None:
            project.meta_description = meta_description
        project.save()
        return _project_to_dict(project, include_description=True)

    result = await sync_to_async(_update)()
    if result is None:
        raise ValueError(f"Project {project_id} not found")
    return result


@mcp.tool()
async def delete_project(project_id: int) -> dict:
    """Delete a project by id. Returns the deleted project's id and title for confirmation."""
    from homepage.models import Project

    def _delete():
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return None
        snapshot = {"id": project.id, "title": project.title}
        project.delete()
        return snapshot

    result = await sync_to_async(_delete)()
    if result is None:
        raise ValueError(f"Project {project_id} not found")
    return {"deleted": True, **result}


# -----------------------------------------------------------------------------
# Blog posts (jchen42.com/blog/)
# -----------------------------------------------------------------------------


def _post_to_dict(post, include_body: bool) -> dict:
    data = {
        "id": post.id,
        "title": post.title,
        "slug": post.slug,
        "subtitle": post.subtitle,
        "published": post.published,
        "published_at": post.published_at.isoformat() if post.published_at else None,
    }
    if include_body:
        data["content_markdown"] = post.content_markdown
        data["meta_description"] = post.meta_description
    return data


@mcp.tool()
async def list_posts(include_unpublished: bool = False) -> list[dict]:
    """List blog posts, newest-first.

    Returns summary fields only — the markdown body is omitted to keep responses small.
    Set ``include_unpublished=True`` to also surface drafts.
    """
    from homepage.models import BlogPost

    def _fetch():
        qs = BlogPost.objects.all()
        if not include_unpublished:
            qs = qs.filter(published=True)
        return [_post_to_dict(p, include_body=False) for p in qs]

    return await sync_to_async(_fetch)()


@mcp.tool()
async def get_post(slug: str) -> dict:
    """Get full details for one blog post by slug, including the markdown body."""
    from homepage.models import BlogPost

    def _fetch():
        try:
            return BlogPost.objects.get(slug=slug)
        except BlogPost.DoesNotExist:
            return None

    post = await sync_to_async(_fetch)()
    if post is None:
        raise ValueError(f"Blog post {slug!r} not found")
    return _post_to_dict(post, include_body=True)


@mcp.tool()
async def create_post(
    title: str,
    content_markdown: str,
    subtitle: str = "",
    meta_description: str = "",
    slug: str = "",
    published: bool = True,
) -> dict:
    """Create a new blog post.

    Leave ``slug`` blank to auto-generate from the title. Posts default to
    ``published=True`` (the casual / "post whatever" flow); set ``published=False``
    to save a draft. ``published_at`` is auto-set to now when a post is first
    published.
    """
    from homepage.models import BlogPost

    def _create():
        post = BlogPost(
            title=title,
            content_markdown=content_markdown,
            subtitle=subtitle,
            meta_description=meta_description,
            slug=slug,
            published=published,
        )
        post.save()  # save() auto-generates slug + published_at when needed
        return _post_to_dict(post, include_body=True)

    return await sync_to_async(_create)()


@mcp.tool()
async def update_post(
    slug: str,
    title: Optional[str] = None,
    new_slug: Optional[str] = None,
    subtitle: Optional[str] = None,
    content_markdown: Optional[str] = None,
    meta_description: Optional[str] = None,
    published: Optional[bool] = None,
) -> dict:
    """Partial-update an existing post. Only fields explicitly passed (non-null) are written.

    To rename the URL slug, pass ``new_slug``. To clear a field, pass an empty string.
    """
    from homepage.models import BlogPost

    def _update():
        try:
            post = BlogPost.objects.get(slug=slug)
        except BlogPost.DoesNotExist:
            return None
        if title is not None:
            post.title = title
        if new_slug is not None:
            post.slug = new_slug
        if subtitle is not None:
            post.subtitle = subtitle
        if content_markdown is not None:
            post.content_markdown = content_markdown
        if meta_description is not None:
            post.meta_description = meta_description
        if published is not None:
            post.published = published
        post.save()
        return _post_to_dict(post, include_body=True)

    result = await sync_to_async(_update)()
    if result is None:
        raise ValueError(f"Blog post {slug!r} not found")
    return result


@mcp.tool()
async def delete_post(slug: str) -> dict:
    """Delete a blog post by slug. Returns the deleted post's slug and title for confirmation."""
    from homepage.models import BlogPost

    def _delete():
        try:
            post = BlogPost.objects.get(slug=slug)
        except BlogPost.DoesNotExist:
            return None
        snapshot = {"slug": post.slug, "title": post.title}
        post.delete()
        return snapshot

    result = await sync_to_async(_delete)()
    if result is None:
        raise ValueError(f"Blog post {slug!r} not found")
    return {"deleted": True, **result}


mcp_app = mcp.streamable_http_app()
