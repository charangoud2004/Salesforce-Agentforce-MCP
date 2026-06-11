import subprocess
import json
import sys

def fetch_cases_by_urgency(urgency: str, org_alias: str = "ticketing-org") -> dict:
    """
    Custom MCP tool that fetches Salesforce Cases filtered by urgency/priority level.
    Maps urgency levels (low/medium/high/critical) to Salesforce Priority field.
    """
    urgency_map = {
        "low": "Low",
        "medium": "Medium", 
        "high": "High",
        "critical": "High"
    }
    
    priority = urgency_map.get(urgency.lower(), "High")
    
    query = f"SELECT Id, CaseNumber, Subject, Status, Priority, CreatedDate FROM Case WHERE Priority = '{priority}' ORDER BY CreatedDate DESC"    
    result = subprocess.run(
    ["sf", "data", "query", "--query", query, "--target-org", org_alias, "--json"],
    capture_output=True,
    text=True,
    shell=True
 )
    
    data = json.loads(result.stdout)
    records = data.get("result", {}).get("records", [])
    
    return {
        "urgency_requested": urgency,
        "priority_queried": priority,
        "total_cases": len(records),
        "cases": [
            {
                "case_number": r["CaseNumber"],
                "subject": r["Subject"],
                "status": r["Status"],
                "priority": r["Priority"],
                "created_at": r["CreatedDate"]
            }
            for r in records
        ]
    }


if __name__ == "__main__":
    urgency = sys.argv[1] if len(sys.argv) > 1 else "high"
    result = fetch_cases_by_urgency(urgency)
    print(json.dumps(result, indent=2))