---
description: Infrastructure as code — Docker, CI/CD, Terraform, Kubernetes (skill-loaded)
agent: build
model: codex-lb/gpt-5.4-mini
---

Use the devops-engineer skill for this infrastructure task:

$ARGUMENTS

**Workflow:**
1. Load the `devops-engineer` skill using the skill tool.
2. If the task involves Kubernetes, ALSO load `kubernetes-specialist` skill.
3. If the task involves Terraform, ALSO load `terraform-engineer` skill.
4. If the task involves cloud architecture, ALSO load `cloud-architect` skill.
5. Delegate to `explore-cheap` with SPECIFIC instructions — e.g., "Find existing Dockerfiles, docker-compose files, and CI/CD configs. Ignore application source code."
6. Implement following the loaded skill instructions.
7. Delegate to `review-cheap` to review the infrastructure changes.
8. If architecture concerns arise, escalate to `architect-premium`.
