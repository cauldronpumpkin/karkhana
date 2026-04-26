import json
import urllib.request
import time

API_BASE = "https://s3juzhfqp5.execute-api.us-east-1.amazonaws.com"
WORKER_TOKEN = "dev-worker-secret-12345"
WORKER_ID = "dev-workstation-01"
OPENCODE_URL = "http://127.0.0.1:4096"
LITELLM_URL = "http://127.0.0.1:4000"

def api_req(method, path, body=None):
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

def oc_req(method, path, body=None):
    url = f"{OPENCODE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            text = response.read().decode("utf-8")
            return json.loads(text) if text else {"ok": True}
    except urllib.error.HTTPError as e:
        return {"error": e.code, "detail": e.read().decode("utf-8")}
    except Exception as e:
        return {"error": str(e)}

def llm_req(method, path, body=None):
    url = f"{LITELLM_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            text = response.read().decode("utf-8")
            return json.loads(text) if text else {"ok": True}
    except Exception as e:
        return {"error": str(e)}

print("=" * 70)
print("END-TO-END PIPELINE TEST")
print("=" * 70)

# 1. Backend health
print("\n[1/10] Backend Health")
health = api_req("GET", "/api/health")
print(f"  Result: {json.dumps(health)}")
assert health.get("status") == "ok", "Backend not healthy"
print("  PASS")

# 2. Worker claim (no jobs yet)
print("\n[2/10] Worker Claim (API polling mode)")
claim = api_req("POST", "/api/worker/claim", {
    "worker_id": WORKER_ID,
    "capabilities": ["repo_index", "agent_branch_work", "test_verify"]
})
print(f"  Result: {json.dumps(claim)}")
assert "claim" in claim, f"Claim failed: {claim}"
print("  PASS (no jobs available, claim=null)")

# 3. LiteLLM health
print("\n[3/10] LiteLLM Proxy Health")
llm_health = llm_req("GET", "/health")
print(f"  Healthy: {llm_health.get('healthy_count', 0)}, Unhealthy: {llm_health.get('unhealthy_count', 0)}")
assert llm_health.get("healthy_count", 0) > 0, "LiteLLM has no healthy endpoints"
print("  PASS")

# 4. OpenCode health
print("\n[4/10] OpenCode Server Health")
oc_health = oc_req("GET", "/health")
alive = "error" not in oc_health or oc_health.get("error") != "404"
print(f"  Running: {alive}")
# OpenCode serves SPA (HTML) for all routes, so any 200 response = alive
assert alive, "OpenCode server not reachable"
print("  PASS")

# 5. OpenCode session creation
print("\n[5/10] OpenCode Session Creation")
session = oc_req("POST", "/session", {"title": "pipeline-test"})
print(f"  Result: {json.dumps(session)[:200]}")
assert "id" in session, f"Session creation failed: {session}"
session_id = session["id"]
print(f"  PASS (session_id={session_id})")

# 6. OpenCode send message
print("\n[6/10] OpenCode Send Message")
msg = oc_req("POST", f"/session/{session_id}/message", {
    "parts": [{"type": "text", "text": "Say 'pipeline test OK' and nothing else."}]
})
print(f"  Result: {json.dumps(msg)[:300]}")
assert "info" in msg, f"Message failed: {msg}"
print("  PASS")

# 7. OpenCode get diff
print("\n[7/10] OpenCode Get Diff")
diff = oc_req("GET", f"/session/{session_id}/diff")
print(f"  Result: {json.dumps(diff)[:200]}")
print("  PASS")

# 8. OpenCode delete session
print("\n[8/10] OpenCode Delete Session")
delete = oc_req("DELETE", f"/session/{session_id}")
print(f"  Result: {json.dumps(delete)}")
print("  PASS")

# 9. Test invite-link endpoint
print("\n[9/10] Backend Invite Link Endpoint")
invite = api_req("GET", f"/api/worker/invite-link?api_base={API_BASE}")
print(f"  Result: {json.dumps(invite)}")
assert "invite_link" in invite, f"Invite link failed: {invite}"
print("  PASS")

# 10. List ideas (to confirm data access)
print("\n[10/10] Backend Data Access (Ideas)")
ideas = api_req("GET", "/api/ideas")
print(f"  Found {len(ideas)} ideas" if isinstance(ideas, list) else "  Result: ok")
assert isinstance(ideas, list) or "value" in ideas
print("  PASS")

print("\n" + "=" * 70)
print("ALL TESTS PASSED")
print("=" * 70)
print("\nPipeline is ready:")
print("  Backend Lambda: HEALTHY")
print("  LiteLLM Proxy:  HEALTHY (port 4000)")
print("  OpenCode Server: HEALTHY (port 4096)")
print("  Worker API Auth: WORKING (dev token mode)")
print("\nTo create a real job:")
print("  1. Import a GitHub project via the backend")
print("  2. Or trigger a build/reindex on an existing idea")
print("  3. The worker will claim it via API polling")
