from __future__ import annotations

from mcp_server.tools import appointments
from mcp_server.tools import scheduling

TOOL_GROUPS: dict[str, dict[str, object]] = {
    "appointments": appointments.TOOLS,
    "scheduling": scheduling.TOOLS,
}