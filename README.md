# Salesforce Agentforce — MCP Utility


# Salesforce Agentforce + MCP Demo

## Part 1 — Agentforce Agent

### What it does
A Service Agent built in Salesforce Agentforce Builder that:
- Accepts incoming customer support requests
- Classifies urgency as low / medium / high / critical
- Routes to the correct subagent automatically using Salesforce's built-in LLM

### Subagents
| Subagent | Handles |
|---|---|
| Case Management | Billing errors, technical problems, general service inquiries |
| Critical Issue Escalation | Safety hazards, frustrated customers, critical system failures |

### How Routing Works
No code. Each subagent has a Classification Description in plain English. When a message comes in, Salesforce's LLM reads it, matches it to the closest description, and routes automatically.

### Subagent Configuration

**Case Management**
- Classification Description: `This topic handles customer support requests including billing errors, incorrect charges, invoice issues, technical problems, product malfunctions, and general service inquiries`
- Scope: `Billing, technical support, and general service inquiries`

**Critical Issue Escalation**
- Classification Description: `This topic handles urgent situations where the customer needs to be transferred to a live human agent, including critical system failures, safety hazards, highly frustrated customers, or repeated unresolved issues`
- Scope: `Critical escalations and live human agent transfers`

### Setup
1. Provision a free [Salesforce Developer Edition org](https://developer.salesforce.com/)
2. Enable Einstein and Agentforce in Setup
3. Open Agentforce Builder → New Agent → Service Agent
4. Add two subagents with Classification Descriptions above
5. Activate and test via Conversation Preview

### Test Results
| Input | Routed To | Result |
|---|---|---|
| "My billing statement has an error" | Case Management | ✅ |
| "My internet is not working" | Case Management | ✅ |
| "I need help immediately, this is critical" | Critical Issue Escalation | ✅ |

### Configuration Screenshots
See `agentforce-config/` folder for:
- Subagents overview
- Case Management configuration
- Critical Issue Escalation configuration
- Live routing test results


> **Part 2** — A custom MCP tool that lets AI assistants query Salesforce Cases by urgency level using natural language.

---

## Architecture

```
┌─────────────────────────┐
│  VS Code (MCP Client)   │
│  ┌───────────────────┐  │
│  │  Copilot / Chat   │  │
│  └────────┬──────────┘  │
│           │ spawns       │
│  ┌────────▼──────────┐  │
│  │  Python process   │  │   ┌──────────────┐      ┌──────────────────┐
│  │  (MCP stdio)      │──┼──→│  sf CLI       │─────→│  Salesforce Org   │
│  │  fetch_cases_by_  │  │   │  (data query) │  REST│  (DE Edition)    │
│  │  urgency.py       │  │   └──────────────┘  API  └──────────────────┘
│  └───────────────────┘  │
└─────────────────────────┘
```

**There's no standalone server.** VS Code spawns the Python script as a child process and talks to it over stdin/stdout (stdio). The script shells out to the `sf` CLI, which handles authentication and REST API calls to Salesforce.

---

## Project Structure

```
salesforce-agentforce/
├── mcp_tool/
│   └── fetch_cases_by_urgency.py   # MCP tool (Python, stdio transport)
└── README.md
```

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.10+ | [python.org](https://python.org) |
| Salesforce CLI (`sf`) | v2+ | `npm install -g @salesforce/cli` |
| MCP SDK | latest | `pip install mcp` |

---

## Setup

### 1. Authenticate your Salesforce org

```bash
sf org login web --alias ticketing-org
```

Verify it's connected:

```bash
sf org list
```

### 2. Install Python dependencies

```bash
pip install mcp
```

### 3. Configure the MCP client

Add the following to your VS Code MCP config (`Settings > MCP` or `.vscode/mcp.json`):

```json
{
  "servers": {
    "salesforce-ticketing-tools": {
      "command": "python",
      "args": ["<full-path-to>/mcp_tool/fetch_cases_by_urgency.py"]
    }
  }
}
```

### 4. Start the MCP tool

In VS Code, open the MCP panel and click **Restart** on `salesforce-ticketing-tools`. You should see `1 tool` detected.

---

## Usage

Once connected, ask your AI assistant natural language questions:

| Prompt | What happens |
|--------|-------------|
| *"How many urgent cases are there?"* | Fetches all **High** priority cases |
| *"Show me low priority cases"* | Fetches all **Low** priority cases |
| *"List critical cases"* | Fetches **High** priority cases sorted oldest-first |

### Example Output

```
Prompt: "How many urgent cases are there?"

→ Tool call: fetch_cases_by_urgency(urgency="high")

Result:
  Total: 6 high-priority cases
  - 00001001: Performance inadequate for second consecutive week
  - 00001000: Starting generator after electrical failure
  - 00001014: Delay in installation; spare parts unavailable
  - 00001019: Structural failure of generator base
  - 00001021: Generator GC3060 platform structure is weakening
  - 00001023: Electric surge damaging adjacent equipment
```

---

## How It Works

1. **`list_tools()`** — Registers the tool schema with the MCP client (name, description, accepted parameters)
2. **`call_tool()`** — Receives the invocation when the AI decides to use the tool, maps urgency → Salesforce Priority
3. **`_fetch_cases_by_urgency()`** — Builds the SOQL query based on the urgency input
4. **`_run_sf_query()`** — Runs `sf data query` as an async subprocess and parses the JSON result
5. Returns structured case data back to the AI client

### Key Design Decisions

- **Async subprocess** (`asyncio.create_subprocess_shell`) instead of blocking `subprocess.run` — keeps the MCP event loop alive so the client doesn't think the tool is dead
- **sf CLI** for Salesforce access — no need to manage OAuth tokens manually; uses the org auth already set up via `sf org login`
- **stdio transport** — the simplest MCP transport; works with VS Code, Cursor, and Claude Desktop

---

## AI Tools Used

Building this tool was a hands-on process — I designed the tool, wrote the core logic, and used AI assistants as debugging and productivity aids:

- **Designed the tool schema myself** — decided on the urgency-to-priority mapping, SOQL query structure, and the JSON response format the AI client would receive. The idea was to keep the interface simple (just pass `high` or `low`) while handling the Salesforce-specific translation internally.

- **Wrote the MCP server from scratch** — set up the `Server`, `list_tools()`, and `call_tool()` handlers using the MCP Python SDK docs. Chose the low-level `mcp.server.Server` class over `FastMCP` for finer control over tool registration.

- **Used Gemini (Antigravity IDE) for debugging** — Hit a critical issue where the tool would hang indefinitely with no output. Gemini helped diagnose that `subprocess.run()` was blocking the async event loop, and suggested switching to `asyncio.create_subprocess_shell()`. Also caught a hardcoded `sf.cmd` path that didn't match my system.

- **Used GitHub Copilot for code completion** — autocomplete for repetitive patterns like `TextContent` responses and SOQL string formatting. Saved time on boilerplate, but all the logic decisions were mine.

- **Manually tested and iterated** — ran `sf org list` and `sf data query` from the terminal to verify authentication, tested the tool through VS Code's MCP panel, and refined the output format based on what looked clean in the chat response.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Tool hangs / no output | Run `sf org list` — your org auth may have expired. Re-auth with `sf org login web --alias ticketing-org` |
| "Unknown tool" error | Restart the MCP server in VS Code after making code changes |
| sf CLI not found | Ensure `sf` is in your system PATH: `sf --version` |
