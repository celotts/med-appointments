from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from . import tools as tool_registry
from .config import load_config


def build_server(config: dict | None = None) -> MCPServer:
    cfg = config if config is not None else load_config()

    server = MCPServer(
        name=cfg["name"],
        title=cfg.get("title") or cfg["name"],
        description=cfg.get("description"),
        instructions=cfg.get("instructions"),
        log_level=cfg["log_level"],
    )

    tools_config = cfg.get("tools", {})
    for group, registry in tool_registry.TOOL_GROUPS.items():
        group_config = tools_config.get(group) or {}
        if not group_config.get("enabled", False):
            continue
        include = group_config.get("include")
        for name, fn in registry.items():
            if include is not None and name not in include:
                continue
            server.add_tool(fn, name=name)

    return server


def main() -> None:
    cfg = load_config()
    server = build_server(cfg)
    server.run(transport=cfg["transport"], host=cfg["host"], port=cfg["port"])


if __name__ == "__main__":
    main()