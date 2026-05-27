"""MCP server exposing CRUD access to the portfolio Project model.

Mounted under /mcp by Portfolio.asgi via Starlette routing.
"""
import os
from typing import Optional

from asgiref.sync import sync_to_async
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings


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


mcp = FastMCP(
    "portfolio",
    stateless_http=True,
    transport_security=_build_transport_security(),
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
        "type": project.type,
        "link": project.link,
        "github_link": project.github_link,
        "image_url": image_url,
    }
    if include_description:
        data["description"] = project.description
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
    type: str = "",
    link: Optional[str] = None,
    github_link: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """Create a new portfolio project. Image upload is not supported via MCP; the project is created without an image."""
    from homepage.models import Project

    def _create():
        project = Project.objects.create(
            title=title,
            type=type,
            link=link,
            github_link=github_link,
            description=description,
        )
        return _project_to_dict(project, include_description=True)

    return await sync_to_async(_create)()


@mcp.tool()
async def update_project(
    project_id: int,
    title: Optional[str] = None,
    type: Optional[str] = None,
    link: Optional[str] = None,
    github_link: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """Partial-update an existing project. Only fields explicitly passed (non-null) are written."""
    from homepage.models import Project

    def _update():
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return None
        if title is not None:
            project.title = title
        if type is not None:
            project.type = type
        if link is not None:
            project.link = link
        if github_link is not None:
            project.github_link = github_link
        if description is not None:
            project.description = description
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


mcp_app = mcp.streamable_http_app()
