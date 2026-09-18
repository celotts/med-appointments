import pytest

from mcp_server.config import load_config
from mcp_server.server import build_server


@pytest.mark.anyio
async def test_registers_enabled_tools():
    server = build_server()
    tool_names = [t.name for t in await server.list_tools()]
    assert "appointment_list" in tool_names
    assert "appointment_get" in tool_names
    assert "appointment_create" in tool_names
    assert "appointment_update" in tool_names
    assert "get_available_slots" in tool_names
    assert "check_conflict" in tool_names
    assert "suggest_reschedule" in tool_names
    assert "suggest_followup" in tool_names


@pytest.mark.anyio
async def test_include_list_excludes_non_selected_tools():
    config = load_config()
    config["tools"]["appointments"]["include"] = ["appointment_list", "appointment_get"]
    server = build_server(config)
    tool_names = [t.name for t in await server.list_tools()]
    assert "appointment_list" in tool_names
    assert "appointment_get" in tool_names
    assert "appointment_create" not in tool_names
    assert "appointment_update" not in tool_names
    assert "appointment_delete" not in tool_names


@pytest.mark.anyio
async def test_disabled_group_is_excluded():
    config = load_config()
    config["tools"]["scheduling"]["enabled"] = False
    server = build_server(config)
    tool_names = [t.name for t in await server.list_tools()]
    assert any(name.startswith("appointment_") for name in tool_names)
    assert not any(
        name in ("get_available_slots", "check_conflict", "suggest_reschedule", "suggest_followup")
        for name in tool_names
    )


@pytest.mark.anyio
async def test_delete_absent_by_default():
    server = build_server()
    tool_names = [t.name for t in await server.list_tools()]
    assert "appointment_delete" not in tool_names


def test_env_override_transport():
    config = load_config(env={"MCP_TRANSPORT": "streamable-http", "MCP_PORT": "9000"})
    assert config["transport"] == "streamable-http"
    assert config["port"] == "9000"