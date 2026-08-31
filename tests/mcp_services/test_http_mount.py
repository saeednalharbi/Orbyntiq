from starlette.routing import Mount

from orbyntiq.api.app import app


def test_mcp_streamable_http_is_mounted() -> None:
    mounts = [
        route
        for route in app.routes
        if isinstance(route, Mount)
    ]

    assert any(route.path == "/mcp" for route in mounts)
