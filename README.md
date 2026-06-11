# Salesforce Agentforce MCP


## Agentforce Service Agent

### What it does
A Service Agent built in Salesforce Agentforce Builder that:
- Accepts incoming customer support requests
- Routes them to the correct subagent based on content
- Classifies urgency as low / medium / high / critical

### Subagents
| Subagent | Handles |
|---|---|
| Case Management | Billing errors, technical problems, general service inquiries |
| Critical Issue Escalation | Safety hazards, frustrated customers, requests for live human agent |

### Setup Steps
1. Provision a free [Salesforce Developer Edition org](https://developer.salesforce.com/)
2. Enable Einstein and Agentforce in Setup
3. Open Agentforce Builder → create a new Service Agent (`ticketing_agent`)
4. Create two subagents with the Classification Descriptions below
5. Activate and test via Conversation Preview

### Subagent Configuration

**Case Management**
- Classification Description: `This topic handles customer support requests including billing errors, incorrect charges, invoice issues, technical problems, product malfunctions, and general service inquiries`
- Scope: `Billing, technical support, and general service inquiries`

**Critical Issue Escalation**
- Classification Description: `This topic handles urgent situations where the customer needs to be transferred to a live human agent, including critical system failures, safety hazards, highly frustrated customers, or repeated unresolved issues`
- Scope: `Critical escalations and live human agent transfers`

### Test Results
| Input | Expected Route | Result |
|---|---|---|
| "My billing statement has an error" | Case Management | ✅ |
| "My internet is not working" | Case Management | ✅ |
| "I am extremely frustrated and need help immediately" | Critical Issue Escalation | ✅ |

---

## Custom MCP Tool

### What it does
A custom MCP tool (`fetch_cases_by_urgency`) that queries Salesforce Cases filtered by urgency level (low / medium / high / critical) using the Salesforce CLI.

### Prerequisites
- [Salesforce CLI](https://developer.salesforce.com/tools/salesforcecli) installed
- Authenticated Salesforce org (`sf org login web`)
- Python 3.8+

### Setup

```bash
# Clone the repo
git clone <your-repo-url>
cd salesforce-agentforce

# Authenticate your org
sf org login web --alias ticketing-org

# Test the MCP tool directly
cd mcp_tool
python fetch_cases_by_urgency.py high
python fetch_cases_by_urgency.py low
python fetch_cases_by_urgency.py medium
```

### MCP Server Configuration

Add to your MCP client config (Claude Desktop, Cursor, or VS Code):

```json
{
  "servers": {
    "salesforce": {
      "command": "npx",
      "args": [
        "@salesforce/mcp",
        "-o",
        "<your-org-username>",
        "--toolsets",
        "all"
      ]
    }
  }
}
```

### Usage

```bash
python fetch_cases_by_urgency.py <urgency>
# urgency: low | medium | high | critical
```

### Sample Output

```json
{
  "urgency_requested": "high",
  "priority_queried": "High",
  "total_cases": 6,
  "cases": [
    {
      "case_number": "00001001",
      "subject": "Starting generator after electrical failure",
      "status": "Closed",
      "priority": "High",
      "created_at": "2026-06-02T10:22:04.000+0000"
    }
  ]
}
```

### Urgency Mapping
| Input | Salesforce Priority |
|---|---|
| low | Low |
| medium | Medium |
| high | High |
| critical | High |

---

## Project Structure

```
salesforce-agentforce/
├── README.md
└── mcp_tool/
    └── fetch_cases_by_urgency.py
```

## AI Tool Usage

This project was built with assistance from:
- **Claude (Anthropic)** — Agentforce subagent configuration guidance, Classification Description text, debugging routing issues, README generation
- **Salesforce Agentforce Builder** — Agent and subagent creation UI
- **Salesforce CLI** — Org authentication and SOQL queries

