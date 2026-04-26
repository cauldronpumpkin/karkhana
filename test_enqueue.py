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

# Get ideas and their projects
print("Getting ideas...")
ideas = req("GET", "/api/ideas")
for idea in ideas[:2]:
    idea_id = idea["id"]
    print(f"\nIdea: {idea['title']} ({idea_id})")
    
    # Get projects for this idea
    projects = req("GET", f"/api/projects?idea_id={idea_id}")
    print(f"Projects: {json.dumps(projects, indent=2)[:500]}")
    
    # Get jobs for this idea
    jobs = req("GET", f"/api/projects/{idea_id}/jobs")
    print(f"Jobs: {json.dumps(jobs, indent=2)[:500]}")

# Try to enqueue a job directly
print("\n" + "=" * 60)
print("ENQUEUE TEST JOB")
print("=" * 60)

# Get first idea with a project
idea_id = ideas[0]["id"] if ideas else None
if idea_id:
    # Try to get the project twin
    project = req("GET", f"/api/projects/{idea_id}")
    print(f"Project detail: {json.dumps(project, indent=2)[:1000]}")
    
    # Try importing a GitHub project to get a real project
    print("\nTrying to enqueue a job for idea...")
    # The backend uses ProjectTwinService.enqueue_job
    # Let's try the build queue endpoint
    build = req("POST", f"/api/build/queue", {
        "idea_id": idea_id,
        "job_type": "repo_index",
        "payload": {"test": True}
    })
    print(f"Build queue response: {json.dumps(build, indent=2)[:1000]}")
