from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any

from backend.app.models.expert_council import (
    COUNCIL_DECISION_BLOCKED,
    COUNCIL_DECISION_NEEDS_CHANGES,
    COUNCIL_DECISION_READY,
    EXPERT_AUTHORITY_ADVISORY,
    EXPERT_AUTHORITY_HARD_GATE,
    EXPERT_DECISION_APPROVED,
    EXPERT_DECISION_APPROVED_WITH_NOTES,
    EXPERT_DECISION_BLOCKED,
    EXPERT_DECISION_REQUESTS_CHANGES,
    ROLE_ARCHITECTURE,
    ROLE_PRIVACY,
    ROLE_PRODUCT_UX,
    ROLE_QA,
    ROLE_SECURITY,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    SEVERITY_ORDER,
    ArtifactPatchProposal,
    CouncilSummary,
    ExpertApproval,
    ExpertConflict,
    ExpertDecision,
    ExpertFinding,
    ExpertRoleManifest,
    ExpertTrigger,
)
from backend.app.repository import utcnow


def _build_default_role_manifests() -> dict[str, ExpertRoleManifest]:
    return {
        ROLE_SECURITY: ExpertRoleManifest(
            role=ROLE_SECURITY,
            display_name="Security Reviewer",
            authority=EXPERT_AUTHORITY_HARD_GATE,
            description="Reviews for secret exposure, unsafe dependencies, dangerous permission flags, and auth/security-sensitive path changes.",
            default_active=True,
            triggers=[
                ExpertTrigger(trigger_type="security_sensitive_path", description="Changed files touch auth, security, or credential paths", weight=2.0),
                ExpertTrigger(trigger_type="secret_exposure_indicator", description="Detected .env, credentials, or secret-related file changes", weight=3.0),
                ExpertTrigger(trigger_type="unsafe_dependency_change", description="Dependency file changes detected", weight=1.5),
                ExpertTrigger(trigger_type="dangerous_permission_flag", description="Permission or config flags indicate elevated privileges", weight=2.0),
            ],
        ),
        ROLE_ARCHITECTURE: ExpertRoleManifest(
            role=ROLE_ARCHITECTURE,
            display_name="Architecture & Reliability Reviewer",
            authority=EXPERT_AUTHORITY_HARD_GATE,
            description="Reviews blast radius, migration safety, rollback readiness, and template drift signals.",
            default_active=True,
            triggers=[
                ExpertTrigger(trigger_type="high_blast_radius", description="More than 10 files changed or core modules impacted", weight=2.0),
                ExpertTrigger(trigger_type="migration_like_change", description="Database migration or schema change detected", weight=2.5),
                ExpertTrigger(trigger_type="missing_rollback", description="Migration-like changes lack rollback evidence", weight=2.0),
                ExpertTrigger(trigger_type="template_drift", description="Template version mismatch or guardrail violations", weight=1.5),
            ],
        ),
        ROLE_PRIVACY: ExpertRoleManifest(
            role=ROLE_PRIVACY,
            display_name="Privacy & Data Protection Reviewer",
            authority=EXPERT_AUTHORITY_HARD_GATE,
            description="Reviews customer-data handling, analytics changes, retention/consent/data-map evidence.",
            default_active=True,
            triggers=[
                ExpertTrigger(trigger_type="customer_data_change", description="Changes touch customer data models or APIs", weight=2.5),
                ExpertTrigger(trigger_type="analytics_change", description="Analytics, tracking, or telemetry changes detected", weight=1.5),
                ExpertTrigger(trigger_type="privacy_sensitive_field", description="Privacy-sensitive fields modified without retention/consent evidence", weight=2.0),
            ],
        ),
        ROLE_QA: ExpertRoleManifest(
            role=ROLE_QA,
            display_name="QA & Verification Reviewer",
            authority=EXPERT_AUTHORITY_HARD_GATE,
            description="Reviews test pass/fail status, verification evidence, and graphify health.",
            default_active=True,
            triggers=[
                ExpertTrigger(trigger_type="test_failure", description="Verification runs report test failures", weight=3.0),
                ExpertTrigger(trigger_type="graphify_status_unhealthy", description="Graphify status is not 'updated' when expected", weight=2.0),
                ExpertTrigger(trigger_type="missing_verification_evidence", description="Required verification commands have no results", weight=2.5),
            ],
        ),
        ROLE_PRODUCT_UX: ExpertRoleManifest(
            role=ROLE_PRODUCT_UX,
            display_name="Product & UX Reviewer",
            authority=EXPERT_AUTHORITY_ADVISORY,
            description="Advisory reviewer for customer-facing UI/UX changes, billing, and a11y flags.",
            default_active=True,
            triggers=[
                ExpertTrigger(trigger_type="customer_facing_ui", description="Frontend or UI component files changed", weight=1.5),
                ExpertTrigger(trigger_type="billing_stripe_change", description="Billing, Stripe, or webhook changes detected", weight=2.0),
                ExpertTrigger(trigger_type="a11y_flag", description="Accessibility-related changes or potential a11y regressions", weight=1.0),
            ],
        ),
    }


DEFAULT_ROLE_MANIFESTS = _build_default_role_manifests()

_SECURITY_PATHS = re.compile(
    r"(auth|security|credential|secret|token|session|password|jwt|oauth|api[_-]?key)",
    re.IGNORECASE,
)
_SECRET_PATTERNS = re.compile(
    r"(\.env|credentials|secret|private[_-]?key|cert|pem|\.p12)",
    re.IGNORECASE,
)
_DEPENDENCY_FILES = re.compile(
    r"(package\.json|requirements\.txt|pyproject\.toml|cargo\.toml|go\.mod|pnpm-lock|yarn\.lock|poetry\.lock|uv\.lock)",
    re.IGNORECASE,
)
_MIGRATION_PATTERNS = re.compile(
    r"(migration|alembic|schema|ddl|\.sql)",
    re.IGNORECASE,
)
_CUSTOMER_DATA_PATTERNS = re.compile(
    r"(customer|user[_-]?data|pii|personal|gdpr|consent|retention|analytics|tracking|telemetry|stripe|billing|webhook|payment)",
    re.IGNORECASE,
)
_FRONTEND_PATTERNS = re.compile(
    r"(\.svelte|\.vue|\.jsx|\.tsx|\.css|\.scss|components?[/\\]|pages?[/\\]|frontend[/\\]|src[/\\]lib)",
    re.IGNORECASE,
)


def evaluate_triggers(
    *,
    changed_files: list[str],
    safety_net: dict[str, Any],
    blast_radius: dict[str, Any],
    decision_gates: dict[str, Any],
    role_manifests: dict[str, ExpertRoleManifest] | None = None,
) -> dict[str, list[ExpertTrigger]]:
    manifests = role_manifests or DEFAULT_ROLE_MANIFESTS
    results: dict[str, list[ExpertTrigger]] = {}

    tests_passed = safety_net.get("tests_passed", True)
    graphify_status = safety_net.get("graphify_status", "pending")
    error_count = safety_net.get("error_count", 0)
    verification_expectations = list(decision_gates.get("verification_expectations") or [])
    verification_commands = list(safety_net.get("verification_commands") or [])
    guardrail_pass = safety_net.get("guardrail_pass", True)
    template_version = decision_gates.get("template_version")
    guardrail_result = safety_net.get("guardrail_result") or {}
    impacted_modules = list(blast_radius.get("impacted_modules") or [])
    impact_score = blast_radius.get("impact_score", "low")
    total_files = blast_radius.get("total_files_changed", len(changed_files))

    all_file_text = " ".join(changed_files)
    joined_lower = all_file_text.lower()

    for role_key, manifest in manifests.items():
        matched: list[ExpertTrigger] = []
        for trigger in manifest.triggers:
            t = ExpertTrigger(
                trigger_type=trigger.trigger_type,
                description=trigger.description,
                weight=trigger.weight,
            )
            hit = False
            refs: list[str] = []

            if trigger.trigger_type == "security_sensitive_path":
                sec_files = [f for f in changed_files if _SECURITY_PATHS.search(f)]
                if sec_files:
                    hit = True
                    refs = sec_files[:5]

            elif trigger.trigger_type == "secret_exposure_indicator":
                sec_files = [f for f in changed_files if _SECRET_PATTERNS.search(f)]
                if sec_files:
                    hit = True
                    refs = sec_files[:5]

            elif trigger.trigger_type == "unsafe_dependency_change":
                dep_files = [f for f in changed_files if _DEPENDENCY_FILES.search(f)]
                if dep_files:
                    hit = True
                    refs = dep_files

            elif trigger.trigger_type == "dangerous_permission_flag":
                if decision_gates.get("policy_result"):
                    pr = decision_gates["policy_result"]
                    if isinstance(pr, dict) and pr.get("status") in ("block", "warn"):
                        hit = True
                        refs = [f"policy_result:{pr.get('status')}"]

            elif trigger.trigger_type == "high_blast_radius":
                if total_files > 10 or impact_score == "high":
                    hit = True
                    refs = [f"files:{total_files}", f"impact:{impact_score}"]

            elif trigger.trigger_type == "migration_like_change":
                mig_files = [f for f in changed_files if _MIGRATION_PATTERNS.search(f)]
                if mig_files:
                    hit = True
                    refs = mig_files[:5]

            elif trigger.trigger_type == "missing_rollback":
                has_mig = any(_MIGRATION_PATTERNS.search(f) for f in changed_files)
                has_down = any("down" in f.lower() or "rollback" in f.lower() for f in changed_files)
                if has_mig and not has_down:
                    hit = True
                    refs = ["migration_without_rollback"]

            elif trigger.trigger_type == "template_drift":
                if not guardrail_pass:
                    hit = True
                    refs = ["guardrail_failed"]
                elif guardrail_result.get("drift_detected"):
                    hit = True
                    refs = ["template_drift"]

            elif trigger.trigger_type == "customer_data_change":
                data_files = [f for f in changed_files if _CUSTOMER_DATA_PATTERNS.search(f)]
                if data_files:
                    hit = True
                    refs = data_files[:5]

            elif trigger.trigger_type == "analytics_change":
                analytics_files = [f for f in changed_files if any(
                    kw in f.lower() for kw in ("analytics", "tracking", "telemetry", "segment", "mixpanel")
                )]
                if analytics_files:
                    hit = True
                    refs = analytics_files[:5]

            elif trigger.trigger_type == "privacy_sensitive_field":
                if "model" in joined_lower and any(
                    kw in joined_lower for kw in ("customer", "user", "pii", "personal", "consent")
                ):
                    hit = True
                    refs = ["data_model_with_privacy_fields"]

            elif trigger.trigger_type == "test_failure":
                if not tests_passed or error_count > 0:
                    hit = True
                    refs = [f"errors:{error_count}", f"tests_passed:{tests_passed}"]

            elif trigger.trigger_type == "graphify_status_unhealthy":
                if graphify_status != "updated" and bool(decision_gates.get("graphify_expectations")):
                    hit = True
                    refs = [f"graphify:{graphify_status}"]

            elif trigger.trigger_type == "missing_verification_evidence":
                if verification_expectations:
                    covered = set(verification_commands)
                    missing = [e for e in verification_expectations if e not in covered]
                    if missing:
                        hit = True
                        refs = [f"missing:{len(missing)}"]

            elif trigger.trigger_type == "customer_facing_ui":
                ui_files = [f for f in changed_files if _FRONTEND_PATTERNS.search(f)]
                if ui_files:
                    hit = True
                    refs = ui_files[:5]

            elif trigger.trigger_type == "billing_stripe_change":
                billing_files = [f for f in changed_files if any(
                    kw in f.lower() for kw in ("stripe", "billing", "webhook", "payment", "subscription", "checkout")
                )]
                if billing_files:
                    hit = True
                    refs = billing_files[:5]

            elif trigger.trigger_type == "a11y_flag":
                a11y_files = [f for f in changed_files if any(
                    kw in f.lower() for kw in ("a11y", "accessibility", "aria", "screen-reader", "focus")
                )]
                if a11y_files:
                    hit = True
                    refs = a11y_files[:5]

            t.matched = hit
            t.evidence_refs = refs
            if hit:
                matched.append(t)

        results[role_key] = matched

    return results


def generate_deterministic_review(
    role_key: str,
    manifest: ExpertRoleManifest,
    matched_triggers: list[ExpertTrigger],
    *,
    safety_net: dict[str, Any],
    blast_radius: dict[str, Any],
    changed_files: list[str],
    decision_gates: dict[str, Any],
) -> ExpertDecision:
    if not matched_triggers:
        return ExpertDecision(
            role=role_key,
            display_name=manifest.display_name,
            authority=manifest.authority,
            decision=EXPERT_DECISION_APPROVED,
            confidence=1.0,
            activated=False,
            summary=f"No triggers activated for {manifest.display_name}.",
            source="deterministic_placeholder",
            reviewed_at=utcnow().isoformat(),
        )

    findings: list[ExpertFinding] = []
    approvals: list[ExpertApproval] = []
    patch_proposals: list[ArtifactPatchProposal] = []
    evidence_refs: list[str] = []

    for trigger in matched_triggers:
        evidence_refs.extend(trigger.evidence_refs)

    generator = _REVIEW_GENERATORS.get(role_key)
    if generator:
        generator(
            manifest=manifest,
            matched_triggers=matched_triggers,
            findings=findings,
            approvals=approvals,
            patch_proposals=patch_proposals,
            safety_net=safety_net,
            blast_radius=blast_radius,
            changed_files=changed_files,
            decision_gates=decision_gates,
        )
    else:
        findings.append(ExpertFinding(
            severity=SEVERITY_LOW,
            summary=f"Triggers activated for {manifest.display_name} but no specialized review logic.",
            category="generic",
            blocking=False,
        ))

    findings = _enforce_anti_bloat(findings, manifest)

    decision = _derive_expert_decision(findings, manifest.authority, manifest.role)

    confidence = _compute_confidence(findings, matched_triggers)

    summary = _build_decision_summary(decision, findings, approvals, manifest)

    return ExpertDecision(
        role=role_key,
        display_name=manifest.display_name,
        authority=manifest.authority,
        decision=decision,
        confidence=confidence,
        activated=True,
        triggers_matched=matched_triggers,
        findings=findings,
        approvals=approvals,
        artifact_patch_proposals=patch_proposals,
        summary=summary,
        evidence_refs=list(dict.fromkeys(evidence_refs)),
        source="deterministic_placeholder",
        reviewed_at=utcnow().isoformat(),
    )


def _enforce_anti_bloat(
    findings: list[ExpertFinding], manifest: ExpertRoleManifest
) -> list[ExpertFinding]:
    blockers = [f for f in findings if f.blocking]
    non_blockers = [f for f in findings if not f.blocking]

    valid_blockers: list[ExpertFinding] = []
    for f in blockers:
        if f.severity in (SEVERITY_HIGH, SEVERITY_CRITICAL) and (f.evidence_ref or f.file_path or f.detail):
            valid_blockers.append(f)
            if len(valid_blockers) >= manifest.max_blockers:
                break
        else:
            f.blocking = False
            non_blockers.append(f)

    capped_non_blockers = non_blockers[:manifest.max_nonblocking_findings]

    return valid_blockers + capped_non_blockers


def _derive_expert_decision(
    findings: list[ExpertFinding], authority: str, role: str
) -> str:
    has_blockers = any(f.blocking for f in findings)
    high_severity = any(f.severity in (SEVERITY_HIGH, SEVERITY_CRITICAL) for f in findings)

    if has_blockers:
        if authority == EXPERT_AUTHORITY_ADVISORY and role == ROLE_PRODUCT_UX:
            if not any(f.severity == SEVERITY_CRITICAL and f.blocking for f in findings):
                return EXPERT_DECISION_REQUESTS_CHANGES
        return EXPERT_DECISION_BLOCKED

    if high_severity:
        return EXPERT_DECISION_REQUESTS_CHANGES

    if findings and not has_blockers:
        return EXPERT_DECISION_APPROVED_WITH_NOTES

    return EXPERT_DECISION_APPROVED


def _compute_confidence(
    findings: list[ExpertFinding], triggers: list[ExpertTrigger]
) -> float:
    if not findings:
        return 1.0
    blocking_count = sum(1 for f in findings if f.blocking)
    if blocking_count > 0:
        return max(0.4, 0.9 - (blocking_count * 0.15))
    return max(0.6, 0.95 - (len(findings) * 0.05))


def _build_decision_summary(
    decision: str,
    findings: list[ExpertFinding],
    approvals: list[ExpertApproval],
    manifest: ExpertRoleManifest,
) -> str:
    parts = [f"{manifest.display_name}: {decision}"]
    blockers = [f for f in findings if f.blocking]
    if blockers:
        parts.append(f"{len(blockers)} blocker(s)")
    non_block = [f for f in findings if not f.blocking]
    if non_block:
        parts.append(f"{len(non_block)} finding(s)")
    if approvals:
        parts.append(f"{len(approvals)} approval(s)")
    return ". ".join(parts)


def _generate_security_review(
    *,
    manifest: ExpertRoleManifest,
    matched_triggers: list[ExpertTrigger],
    findings: list[ExpertFinding],
    approvals: list[ExpertApproval],
    patch_proposals: list[ArtifactPatchProposal],
    safety_net: dict[str, Any],
    blast_radius: dict[str, Any],
    changed_files: list[str],
    decision_gates: dict[str, Any],
) -> None:
    for trigger in matched_triggers:
        if trigger.trigger_type == "secret_exposure_indicator":
            findings.append(ExpertFinding(
                severity=SEVERITY_CRITICAL,
                summary="Secret or credential file detected in changed files",
                category="secret_exposure",
                blocking=True,
                evidence_ref=trigger.evidence_refs[0] if trigger.evidence_refs else None,
                detail="Files matching secret/credential patterns detected. Verify no secrets are committed.",
            ))
        elif trigger.trigger_type == "security_sensitive_path":
            findings.append(ExpertFinding(
                severity=SEVERITY_HIGH,
                summary="Auth/security-sensitive paths modified",
                category="auth_change",
                blocking=False,
                evidence_ref=trigger.evidence_refs[0] if trigger.evidence_refs else None,
                detail="Changes to auth/security modules require careful review.",
            ))
        elif trigger.trigger_type == "unsafe_dependency_change":
            findings.append(ExpertFinding(
                severity=SEVERITY_MEDIUM,
                summary="Dependency files changed",
                category="dependency",
                blocking=False,
                evidence_ref=trigger.evidence_refs[0] if trigger.evidence_refs else None,
            ))
        elif trigger.trigger_type == "dangerous_permission_flag":
            findings.append(ExpertFinding(
                severity=SEVERITY_HIGH,
                summary="Policy result indicates elevated permissions or block",
                category="permission",
                blocking=True,
                detail="Dangerous permission flags detected in policy result.",
            ))

    if not any(f.blocking for f in findings):
        approvals.append(ExpertApproval(
            scope="security_scan",
            description="No critical security issues detected in deterministic review",
            confidence=0.85,
        ))


def _generate_qa_review(
    *,
    manifest: ExpertRoleManifest,
    matched_triggers: list[ExpertTrigger],
    findings: list[ExpertFinding],
    approvals: list[ExpertApproval],
    patch_proposals: list[ArtifactPatchProposal],
    safety_net: dict[str, Any],
    blast_radius: dict[str, Any],
    changed_files: list[str],
    decision_gates: dict[str, Any],
) -> None:
    tests_passed = safety_net.get("tests_passed", True)
    error_count = safety_net.get("error_count", 0)
    graphify_status = safety_net.get("graphify_status", "pending")
    repair_triggered = safety_net.get("repair_loop_triggered", False)

    if not tests_passed:
        findings.append(ExpertFinding(
            severity=SEVERITY_CRITICAL,
            summary="Tests failed — blocking",
            category="test_failure",
            blocking=True,
            detail=f"{error_count} verification error(s) reported. All tests must pass before approval.",
        ))
    elif error_count > 0:
        findings.append(ExpertFinding(
            severity=SEVERITY_HIGH,
            summary=f"{error_count} verification error(s) detected",
            category="verification_error",
            blocking=False,
        ))

    if graphify_status != "updated" and bool(decision_gates.get("graphify_expectations")):
        findings.append(ExpertFinding(
            severity=SEVERITY_HIGH,
            summary=f"Graphify status is '{graphify_status}', expected 'updated'",
            category="graphify",
            blocking=True,
            detail="Graphify knowledge graph update expected but not confirmed.",
        ))

    if repair_triggered:
        findings.append(ExpertFinding(
            severity=SEVERITY_MEDIUM,
            summary="Repair loop was triggered during this run",
            category="repair_loop",
            blocking=False,
        ))

    verification_expectations = list(decision_gates.get("verification_expectations") or [])
    verification_commands = list(safety_net.get("verification_commands") or [])
    missing = [e for e in verification_expectations if e not in verification_commands]
    if missing:
        findings.append(ExpertFinding(
            severity=SEVERITY_HIGH,
            summary=f"Missing verification evidence for {len(missing)} command(s)",
            category="missing_verification",
            blocking=len(missing) == len(verification_expectations) if verification_expectations else False,
            detail=f"Expected: {verification_expectations}. Covered: {verification_commands}.",
        ))

    if not any(f.blocking for f in findings):
        approvals.append(ExpertApproval(
            scope="verification",
            description="All tests passed and verification evidence present",
            confidence=0.9 if tests_passed else 0.5,
        ))


def _generate_architecture_review(
    *,
    manifest: ExpertRoleManifest,
    matched_triggers: list[ExpertTrigger],
    findings: list[ExpertFinding],
    approvals: list[ExpertApproval],
    patch_proposals: list[ArtifactPatchProposal],
    safety_net: dict[str, Any],
    blast_radius: dict[str, Any],
    changed_files: list[str],
    decision_gates: dict[str, Any],
) -> None:
    impact_score = blast_radius.get("impact_score", "low")
    total_files = blast_radius.get("total_files_changed", len(changed_files))

    if total_files > 10 or impact_score == "high":
        findings.append(ExpertFinding(
            severity=SEVERITY_HIGH,
            summary=f"High blast radius: {total_files} file(s) changed, impact={impact_score}",
            category="blast_radius",
            blocking=True,
            detail="Large changeset detected. Consider splitting into smaller PRs or verifying rollback plan.",
        ))

    has_migration = any(_MIGRATION_PATTERNS.search(f) for f in changed_files)
    has_rollback = any("down" in f.lower() or "rollback" in f.lower() for f in changed_files)
    if has_migration and not has_rollback:
        findings.append(ExpertFinding(
            severity=SEVERITY_HIGH,
            summary="Migration detected without corresponding rollback",
            category="migration_safety",
            blocking=True,
            detail="Database migration changes should include rollback/downgrade paths.",
        ))

    if not safety_net.get("guardrail_pass", True):
        findings.append(ExpertFinding(
            severity=SEVERITY_HIGH,
            summary="Path guardrails failed",
            category="guardrail",
            blocking=True,
            detail="Guardrail validation failed. Changed files may violate path restrictions.",
        ))

    if not any(f.blocking for f in findings):
        approvals.append(ExpertApproval(
            scope="architecture",
            description="No architectural concerns detected",
            confidence=0.8,
        ))


def _generate_privacy_review(
    *,
    manifest: ExpertRoleManifest,
    matched_triggers: list[ExpertTrigger],
    findings: list[ExpertFinding],
    approvals: list[ExpertApproval],
    patch_proposals: list[ArtifactPatchProposal],
    safety_net: dict[str, Any],
    blast_radius: dict[str, Any],
    changed_files: list[str],
    decision_gates: dict[str, Any],
) -> None:
    customer_data_files = [f for f in changed_files if _CUSTOMER_DATA_PATTERNS.search(f)]

    if customer_data_files:
        findings.append(ExpertFinding(
            severity=SEVERITY_HIGH,
            summary="Customer-data or privacy-related files changed",
            category="customer_data",
            blocking=True,
            file_path=customer_data_files[0],
            detail="Changes touching customer data, billing, or privacy-sensitive areas require retention/consent/data-map evidence.",
        ))

    analytics_files = [f for f in changed_files if any(
        kw in f.lower() for kw in ("analytics", "tracking", "telemetry", "segment", "mixpanel")
    )]
    if analytics_files:
        findings.append(ExpertFinding(
            severity=SEVERITY_MEDIUM,
            summary="Analytics/tracking changes detected",
            category="analytics",
            blocking=False,
            detail="Verify consent and data-map documentation for analytics changes.",
        ))

    if not any(f.blocking for f in findings):
        approvals.append(ExpertApproval(
            scope="privacy",
            description="No privacy concerns detected in deterministic review",
            confidence=0.75,
        ))


def _generate_product_ux_review(
    *,
    manifest: ExpertRoleManifest,
    matched_triggers: list[ExpertTrigger],
    findings: list[ExpertFinding],
    approvals: list[ExpertApproval],
    patch_proposals: list[ArtifactPatchProposal],
    safety_net: dict[str, Any],
    blast_radius: dict[str, Any],
    changed_files: list[str],
    decision_gates: dict[str, Any],
) -> None:
    ui_files = [f for f in changed_files if _FRONTEND_PATTERNS.search(f)]
    billing_files = [f for f in changed_files if any(
        kw in f.lower() for kw in ("stripe", "billing", "webhook", "payment", "subscription", "checkout")
    )]

    if ui_files:
        findings.append(ExpertFinding(
            severity=SEVERITY_LOW,
            summary="Customer-facing UI files changed",
            category="ui_change",
            blocking=False,
            detail="Review for UX consistency and accessibility.",
        ))
        approvals.append(ExpertApproval(
            scope="ui_review",
            description="UI changes noted for advisory review",
            confidence=0.7,
        ))

    if billing_files:
        findings.append(ExpertFinding(
            severity=SEVERITY_HIGH,
            summary="Billing/payment-related changes detected",
            category="billing",
            blocking=False,
            detail="Billing changes should be verified end-to-end. Advisory only — Product/UX cannot hard-block.",
        ))

    if not findings:
        approvals.append(ExpertApproval(
            scope="product_ux",
            description="No customer-facing concerns detected",
            confidence=0.8,
        ))


_REVIEW_GENERATORS = {
    ROLE_SECURITY: _generate_security_review,
    ROLE_QA: _generate_qa_review,
    ROLE_ARCHITECTURE: _generate_architecture_review,
    ROLE_PRIVACY: _generate_privacy_review,
    ROLE_PRODUCT_UX: _generate_product_ux_review,
}


def detect_conflicts(decisions: list[ExpertDecision]) -> list[ExpertConflict]:
    conflicts: list[ExpertConflict] = []
    for i, a in enumerate(decisions):
        for b in decisions[i + 1:]:
            if not a.activated or not b.activated:
                continue
            a_blocks = a.decision == EXPERT_DECISION_BLOCKED
            b_blocks = b.decision == EXPERT_DECISION_BLOCKED
            a_approves = a.decision in (EXPERT_DECISION_APPROVED, EXPERT_DECISION_APPROVED_WITH_NOTES)
            b_approves = b.decision in (EXPERT_DECISION_APPROVED, EXPERT_DECISION_APPROVED_WITH_NOTES)

            if (a_blocks and b_approves) or (b_blocks and a_approves):
                a_findings = [f.summary for f in a.findings if f.blocking][:2]
                b_findings = [f.summary for f in b.findings if f.blocking][:2]
                conflicts.append(ExpertConflict(
                    role_a=a.role,
                    role_b=b.role,
                    topic="blocking_disagreement",
                    description=f"{a.display_name} ({a.decision}) vs {b.display_name} ({b.decision}). "
                    f"A: {'; '.join(a_findings)}. B: {'; '.join(b_findings)}",
                    severity=SEVERITY_HIGH,
                ))
    return conflicts


def derive_council_summary(decisions: list[ExpertDecision]) -> CouncilSummary:
    active_decisions = [d for d in decisions if d.activated]
    all_findings: list[ExpertFinding] = []
    for d in active_decisions:
        all_findings.extend(d.findings)

    highest_severity = SEVERITY_LOW
    for f in all_findings:
        if SEVERITY_ORDER.get(f.severity, 0) > SEVERITY_ORDER.get(highest_severity, 0):
            highest_severity = f.severity

    unresolved_blockers = sum(
        1 for f in all_findings if f.blocking
    )

    has_blocks = any(d.decision == EXPERT_DECISION_BLOCKED for d in active_decisions)
    has_requests = any(d.decision == EXPERT_DECISION_REQUESTS_CHANGES for d in active_decisions)

    if has_blocks:
        overall = COUNCIL_DECISION_BLOCKED
    elif has_requests:
        overall = COUNCIL_DECISION_NEEDS_CHANGES
    else:
        overall = COUNCIL_DECISION_READY

    conflicts = detect_conflicts(decisions)

    all_patches: list[ArtifactPatchProposal] = []
    for d in active_decisions:
        all_patches.extend(d.artifact_patch_proposals)

    return CouncilSummary(
        overall_decision=overall,
        highest_severity=highest_severity,
        unresolved_blockers_count=unresolved_blockers,
        active_roles_count=len(active_decisions),
        conflict_count=len(conflicts),
        conflicts=conflicts,
        artifact_patch_proposals=all_patches,
    )


class ExpertCouncilService:
    def __init__(self, role_manifests: dict[str, ExpertRoleManifest] | None = None) -> None:
        self.role_manifests = role_manifests or dict(DEFAULT_ROLE_MANIFESTS)

    def run_expert_reviews(
        self,
        *,
        changed_files: list[str],
        safety_net: dict[str, Any],
        blast_radius: dict[str, Any],
        decision_gates: dict[str, Any],
        expert_policy: dict[str, Any] | None = None,
    ) -> tuple[list[ExpertDecision], CouncilSummary]:
        effective_manifests = dict(self.role_manifests)
        if expert_policy:
            for role_key, policy in expert_policy.items():
                if role_key in effective_manifests:
                    if isinstance(policy, dict):
                        if policy.get("disabled"):
                            del effective_manifests[role_key]
                        elif policy.get("authority"):
                            effective_manifests[role_key] = ExpertRoleManifest(
                                **{k: v for k, v in effective_manifests[role_key].__dict__.items() if k != "authority"},
                                authority=policy["authority"],
                            )

        trigger_results = evaluate_triggers(
            changed_files=changed_files,
            safety_net=safety_net,
            blast_radius=blast_radius,
            decision_gates=decision_gates,
            role_manifests=effective_manifests,
        )

        decisions: list[ExpertDecision] = []
        for role_key, manifest in effective_manifests.items():
            matched = trigger_results.get(role_key, [])
            decision = generate_deterministic_review(
                role_key,
                manifest,
                matched,
                safety_net=safety_net,
                blast_radius=blast_radius,
                changed_files=changed_files,
                decision_gates=decision_gates,
            )
            decisions.append(decision)

        summary = derive_council_summary(decisions)
        return decisions, summary
