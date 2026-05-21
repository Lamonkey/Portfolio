"""MCP server exposing read-only access to the portfolio Project model.

Mounted under /mcp by Portfolio.asgi via Starlette routing.
"""
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


mcp_app = mcp.streamable_http_app()
