from app.core.config import Settings
from app.main import create_app


def test_create_app_applies_settings_to_metadata() -> None:
    app = create_app(
        Settings(
            app_name="Evalynx Local",
            environment="test",
            debug=True,
            api_prefix="/api",
            database_url="sqlite:///./test-app.db",
        )
    )

    route_paths = {route.path for route in app.routes}

    assert app.title == "Evalynx Local"
    assert app.debug is True
    assert "/api/health" in route_paths
    assert "/api/projects" in route_paths
    assert "/api/runs" in route_paths
    assert "/api/runs/{run_id}" in route_paths
    assert "/api/projects/{project_id}/runs" in route_paths
