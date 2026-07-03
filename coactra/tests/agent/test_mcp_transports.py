from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from pydantic_ai.models.test import TestModel

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Team
from coactra.agent import MCPServer

pytest.importorskip("mcp")
pytest.importorskip("pydantic_ai.mcp")


def _unused_port() -> int:
    try:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])
    except PermissionError:
        pytest.skip("local sockets are blocked in this sandbox")


@pytest.mark.xfail(
    reason="some sandboxes block subprocess MCP stdio initialize",
    strict=False,
)
async def test_team_agent_uses_real_stdio_mcp_server():
    server = Path(__file__).resolve().parents[1] / "fixtures" / "math_mcp_server.py"
    team = Team(
        scope=Scope(tenant_id="acme", namespace="mcp"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver([
            ModelRoute(capability="mcp", profile=ModelProfile(name="mcp", model=TestModel()))
        ]),
    )
    agent = await team.add_agent(
        model_capability="mcp",
        name="mcp-agent",
        tools=[MCPServer(url=str(server), name="math")],
    )

    try:
        result = await agent.run("Use the MCP tool.")
    finally:
        await agent.aclose()

    assert result


async def test_team_agent_uses_real_streamable_http_mcp_server():
    server = Path(__file__).resolve().parents[1] / "fixtures" / "math_mcp_server.py"
    fastmcp = Path(sys.executable).with_name("fastmcp")
    port = _unused_port()
    process = subprocess.Popen(
        [
            str(fastmcp),
            "run",
            str(server),
            "--transport",
            "streamable-http",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--path",
            "/mcp",
            "--no-banner",
            "--skip-env",
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        text=True,
    )
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            with socket.socket() as sock:
                sock.settimeout(0.2)
                if sock.connect_ex(("127.0.0.1", port)) == 0:
                    break
            time.sleep(0.1)
        else:
            process.terminate()
            _, stderr = process.communicate(timeout=5)
            raise AssertionError(f"FastMCP HTTP server did not start: {stderr}")

        team = Team(
            scope=Scope(tenant_id="acme", namespace="mcp"),
            policy=Policy.permissive(),
            model_resolver=ModelResolver([
                ModelRoute(capability="mcp", profile=ModelProfile(name="mcp", model=TestModel()))
            ]),
        )
        agent = await team.add_agent(
            model_capability="mcp",
            name="mcp-http-agent",
            tools=[MCPServer(url=f"http://127.0.0.1:{port}/mcp", name="math-http")],
        )

        try:
            result = await agent.run("Use the MCP tool.")
        finally:
            await agent.aclose()

        assert result
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
