"""Bearer-token ASGI middleware for the MCP endpoint."""


def _extract_bearer(scope) -> str | None:
    for name, value in scope.get("headers", []):
        if name == b"authorization":
            decoded = value.decode("latin-1")
            if decoded.startswith("Bearer "):
                return decoded[7:].strip()
            return None
    return None


async def _send_status(send, status: int, message: bytes, extra_headers=()) -> None:
    headers = [(b"content-type", b"text/plain; charset=utf-8")]
    headers.extend(extra_headers)
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": message})


class BearerAuthMiddleware:
    def __init__(self, app, expected_token: str | None) -> None:
        self.app = app
        self.expected_token = expected_token

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if not self.expected_token:
            await _send_status(send, 503, b"MCP_TOKEN is not configured on the server.\n")
            return

        if _extract_bearer(scope) != self.expected_token:
            await _send_status(
                send,
                401,
                b"Unauthorized\n",
                extra_headers=[(b"www-authenticate", b'Bearer realm="mcp"')],
            )
            return

        await self.app(scope, receive, send)
