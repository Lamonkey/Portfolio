"""MCP server exposing CRUD access to the portfolio Project model.

Mounted under /mcp by Portfolio.asgi via Starlette routing.
"""
from typing import Optional

from asgiref.sync import sync_to_async
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("portfolio", stateless_http=True)


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
