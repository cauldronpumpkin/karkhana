import json
import urllib.request

API_BASE = "https://s3juzhfqp5.execute-api.us-east-1.amazonaws.com"
WORKER_TOKEN = "dev-worker-secret-12345"
WORKER_ID = "dev-workstation-01"

def req(method, path, body=None):
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    request.add_header("X-IdeaRefinery-Worker-Token", WORKER_TOKEN)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        return {"error": e.code, "detail": e.read().decode("utf-8")}
    except Exception as e:
        return {"error": str(e)}

print("=" * 60)
print("1. Health Check")
print("=" * 60)
health = req("GET", "/api/health")
print(json.dumps(health, indent=2))

print()
print("=" * 60)
print("2. Claim Job (should return null claim if no jobs)")
print("=" * 60)
claim = req("POST", "/api/worker/claim", {
    "worker_id": WORKER_ID,
    "capabilities": ["repo_index", "agent_branch_work", "test_verify"]
})
print(json.dumps(claim, indent=2))

print()
print("=" * 60)
print("3. List Ideas (to find a project to create a job for)")
print("=" * 60)
ideas = req("GET", "/api/ideas")
print(json.dumps(ideas, indent=2)[:2000])

print()
print("=" * 60)
print("4. Local Workers Dashboard")
print("=" * 60)
workers = req("GET", "/api/local-workers")
print(json.dumps(workers, indent=2)[:2000])

print()
print("=" * 60)
print("5. Test SQS Event Send")
print("=" * 60)
event = req("POST", f"/api/local-workers/{WORKER_ID}/events", {
    "type": "test_event",
    "payload": {"message": "pipeline test"}
})
print(json.dumps(event, indent=2))

print()
print("=" * 60)
print("PIPELINE TEST COMPLETE")
print("=" * 60)
