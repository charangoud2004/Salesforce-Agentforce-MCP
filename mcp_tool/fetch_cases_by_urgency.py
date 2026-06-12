"""
Salesforce Case MCP Server
───────────────────────────
An MCP (Model Context Protocol) server that exposes a single tool to
query Salesforce Cases by urgency level using the Salesforce CLI (`sf`).

Architecture:
    MCP Client (VS Code / Claude)  ←—stdio—→  This Server  ←—shell—→  sf CLI  ←—REST—→  Salesforce

Transport: stdio (compatible with VS Code, Cursor, Claude Desktop)
"""

import asyncio
import json
import os

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# ── Constants ────────────────────────────────────────────────────────────

DEFAULT_ORG_ALIAS = "ticketing-org"
CLI_TIMEOUT_SECONDS = 30

URGENCY_TO_PRIORITY = {
    "low": "Low",
    "medium": "Medium",
    "high": "High",
    "critical": "High",  # Same priority, but sorted oldest-first to surface aging cases
}

# ── MCP Server ───────────────────────────────────────────────────────────

app = Server("salesforce-ticketing-tools")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """Register available tools with the MCP client."""
    return [
        Tool(
            name="fetch_cases_by_urgency",
            description=(
                "Fetches Salesforce Cases filtered by urgency level. "
                "Supports: low, medium, high, critical. "
                "'critical' returns High priority cases sorted oldest-first."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "urgency": {
                        "type": "string",
                        "description": "Urgency level to filter by",
                        "enum": ["low", "medium", "high", "critical"],
                    },
                    "org_alias": {
                        "type": "string",
                        "description": f"Salesforce org alias (default: {DEFAULT_ORG_ALIAS})",
                        "default": DEFAULT_ORG_ALIAS,
                    },
                },
                "required": ["urgency"],
            },
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Route incoming tool calls to the appropriate handler."""
    if name == "fetch_cases_by_urgency":
        return await _fetch_cases_by_urgency(arguments)
    return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


# ── Tool Implementation ─────────────────────────────────────────────────

async def _fetch_cases_by_urgency(arguments: dict) -> list[TextContent]:
    """Query Salesforce Cases via the sf CLI, filtered by urgency."""
    urgency = arguments.get("urgency", "high").lower()
    org_alias = arguments.get("org_alias", DEFAULT_ORG_ALIAS)

    priority = URGENCY_TO_PRIORITY.get(urgency, "High")
    sort_order = "ASC" if urgency == "critical" else "DESC"

    soql = (
        f"SELECT Id, CaseNumber, Subject, Status, Priority, CreatedDate "
        f"FROM Case WHERE Priority = '{priority}' "
        f"ORDER BY CreatedDate {sort_order}"
    )

    # Run sf CLI asynchronously to keep the MCP event loop responsive
    data, error = await _run_sf_query(soql, org_alias)
    if error:
        return error

    records = data.get("result", {}).get("records", [])

    result = {
        "urgency_requested": urgency,
        "priority_queried": priority,
        "total_cases": len(records),
        "cases": [
            {
                "case_number": r["CaseNumber"],
                "subject": r["Subject"],
                "status": r["Status"],
                "priority": r["Priority"],
                "created_at": r["CreatedDate"],
            }
            for r in records
        ],
    }
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ── Salesforce CLI Helper ────────────────────────────────────────────────

async def _run_sf_query(soql: str, org_alias: str) -> tuple[dict | None, list[TextContent] | None]:
    """
    Execute a SOQL query via the sf CLI asynchronously.

    Returns:
        (parsed_data, None) on success
        (None, error_response) on failure
    """
    escaped_query = soql.replace('"', '\\"')
    cmd = f'sf data query --query "{escaped_query}" --target-org {org_alias} --json'

    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ},
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=CLI_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            proc.kill()
            return None, [TextContent(type="text", text=json.dumps({"error": "sf CLI timed out"}))]

        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")

        if proc.returncode != 0:
            return None, [TextContent(type="text", text=json.dumps({"error": stderr_text.strip() or "sf CLI failed"}))]

        if not stdout_text.strip():
            return None, [TextContent(type="text", text=json.dumps({"error": "sf CLI returned empty output"}))]

        data = json.loads(stdout_text)

        if data.get("status") != 0:
            return None, [TextContent(type="text", text=json.dumps({"error": data.get("message", "Query failed")}))]

        return data, None

    except json.JSONDecodeError as exc:
        return None, [TextContent(type="text", text=json.dumps({"error": f"Parse error: {exc}"}))]




# ── Entry Point ──────────────────────────────────────────────────────────

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())