from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


EXPERT_AUTHORITY_HARD_GATE = "hard_gate"
EXPERT_AUTHORITY_ADVISORY = "advisory"

EXPERT_DECISION_APPROVED = "approved"
EXPERT_DECISION_APPROVED_WITH_NOTES = "approved_with_notes"
EXPERT_DECISION_REQUESTS_CHANGES = "requests_changes"
EXPERT_DECISION_BLOCKED = "blocked"

SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"
SEVERITY_CRITICAL = "critical"

SEVERITY_ORDER = {SEVERITY_LOW: 0, SEVERITY_MEDIUM: 1, SEVERITY_HIGH: 2, SEVERITY_CRITICAL: 3}

COUNCIL_DECISION_READY = "ready"
COUNCIL_DECISION_NEEDS_CHANGES = "needs_changes"
COUNCIL_DECISION_BLOCKED = "blocked"

ROLE_SECURITY = "security"
ROLE_ARCHITECTURE = "architecture_reliability"
ROLE_PRIVACY = "privacy_data_protection"
ROLE_QA = "qa_verification"
ROLE_PRODUCT_UX = "product_ux"

V0_ROLES = frozenset({ROLE_SECURITY, ROLE_ARCHITECTURE, ROLE_PRIVACY, ROLE_QA, ROLE_PRODUCT_UX})


@dataclass(slots=True)
class ExpertTrigger:
    trigger_type: str
    description: str
    matched: bool = False
    evidence_refs: list[str] = field(default_factory=list)
    weight: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExpertTrigger:
        return cls(
            trigger_type=str(data.get("trigger_type") or ""),
            description=str(data.get("description") or ""),
            matched=bool(data.get("matched", False)),
            evidence_refs=list(data.get("evidence_refs") or []),
            weight=float(data.get("weight") or 1.0),
        )


@dataclass(slots=True)
class ExpertFinding:
    severity: str
    summary: str
    category: str
    blocking: bool = False
    evidence_ref: str | None = None
    file_path: str | None = None
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExpertFinding:
        return cls(
            severity=str(data.get("severity") or SEVERITY_LOW),
            summary=str(data.get("summary") or ""),
            category=str(data.get("category") or ""),
            blocking=bool(data.get("blocking", False)),
            evidence_ref=data.get("evidence_ref"),
            file_path=data.get("file_path"),
            detail=str(data.get("detail") or ""),
        )


@dataclass(slots=True)
class ExpertApproval:
    scope: str
    description: str
    confidence: float = 1.0
    evidence_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExpertApproval:
        return cls(
            scope=str(data.get("scope") or ""),
            description=str(data.get("description") or ""),
            confidence=float(data.get("confidence") or 1.0),
            evidence_ref=data.get("evidence_ref"),
        )


@dataclass(slots=True)
class ExpertOptionScore:
    option: str
    score: float
    reasoning: str = ""
    weight: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExpertOptionScore:
        return cls(
            option=str(data.get("option") or ""),
            score=float(data.get("score") or 0.0),
            reasoning=str(data.get("reasoning") or ""),
            weight=float(data.get("weight") or 1.0),
        )


@dataclass(slots=True)
class ArtifactPatchProposal:
    artifact_key: str
    patch_description: str
    proposed_content: str = ""
    rationale: str = ""
    severity: str = SEVERITY_LOW
    auto_apply: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArtifactPatchProposal:
        return cls(
            artifact_key=str(data.get("artifact_key") or ""),
            patch_description=str(data.get("patch_description") or ""),
            proposed_content=str(data.get("proposed_content") or ""),
            rationale=str(data.get("rationale") or ""),
            severity=str(data.get("severity") or SEVERITY_LOW),
            auto_apply=bool(data.get("auto_apply", False)),
        )


@dataclass(slots=True)
class ExpertConflict:
    role_a: str
    role_b: str
    topic: str
    description: str
    severity: str = SEVERITY_MEDIUM

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExpertConflict:
        return cls(
            role_a=str(data.get("role_a") or ""),
            role_b=str(data.get("role_b") or ""),
            topic=str(data.get("topic") or ""),
            description=str(data.get("description") or ""),
            severity=str(data.get("severity") or SEVERITY_MEDIUM),
        )


@dataclass(slots=True)
class ExpertRoleManifest:
    role: str
    display_name: str
    authority: str
    description: str
    default_active: bool = True
    triggers: list[ExpertTrigger] = field(default_factory=list)
    max_blockers: int = 3
    max_nonblocking_findings: int = 5

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "display_name": self.display_name,
            "authority": self.authority,
            "description": self.description,
            "default_active": self.default_active,
            "triggers": [t.to_dict() for t in self.triggers],
            "max_blockers": self.max_blockers,
            "max_nonblocking_findings": self.max_nonblocking_findings,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExpertRoleManifest:
        return cls(
            role=str(data.get("role") or ""),
            display_name=str(data.get("display_name") or ""),
            authority=str(data.get("authority") or EXPERT_AUTHORITY_ADVISORY),
            description=str(data.get("description") or ""),
            default_active=bool(data.get("default_active", True)),
            triggers=[ExpertTrigger.from_dict(t) for t in data.get("triggers") or []],
            max_blockers=int(data.get("max_blockers") or 3),
            max_nonblocking_findings=int(data.get("max_nonblocking_findings") or 5),
        )


@dataclass(slots=True)
class ExpertDecision:
    role: str
    display_name: str
    authority: str
    decision: str
    confidence: float
    activated: bool = True
    triggers_matched: list[ExpertTrigger] = field(default_factory=list)
    findings: list[ExpertFinding] = field(default_factory=list)
    approvals: list[ExpertApproval] = field(default_factory=list)
    option_scores: list[ExpertOptionScore] = field(default_factory=list)
    artifact_patch_proposals: list[ArtifactPatchProposal] = field(default_factory=list)
    summary: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    source: str = "deterministic_placeholder"
    reviewed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "display_name": self.display_name,
            "authority": self.authority,
            "decision": self.decision,
            "confidence": self.confidence,
            "activated": self.activated,
            "triggers_matched": [t.to_dict() for t in self.triggers_matched],
            "findings": [f.to_dict() for f in self.findings],
            "approvals": [a.to_dict() for a in self.approvals],
            "option_scores": [o.to_dict() for o in self.option_scores],
            "artifact_patch_proposals": [p.to_dict() for p in self.artifact_patch_proposals],
            "summary": self.summary,
            "evidence_refs": list(self.evidence_refs),
            "source": self.source,
            "reviewed_at": self.reviewed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExpertDecision:
        return cls(
            role=str(data.get("role") or ""),
            display_name=str(data.get("display_name") or ""),
            authority=str(data.get("authority") or EXPERT_AUTHORITY_ADVISORY),
            decision=str(data.get("decision") or EXPERT_DECISION_APPROVED),
            confidence=float(data.get("confidence") or 1.0),
            activated=bool(data.get("activated", True)),
            triggers_matched=[ExpertTrigger.from_dict(t) for t in data.get("triggers_matched") or []],
            findings=[ExpertFinding.from_dict(f) for f in data.get("findings") or []],
            approvals=[ExpertApproval.from_dict(a) for a in data.get("approvals") or []],
            option_scores=[ExpertOptionScore.from_dict(o) for o in data.get("option_scores") or []],
            artifact_patch_proposals=[ArtifactPatchProposal.from_dict(p) for p in data.get("artifact_patch_proposals") or []],
            summary=str(data.get("summary") or ""),
            evidence_refs=list(data.get("evidence_refs") or []),
            source=str(data.get("source") or "deterministic_placeholder"),
            reviewed_at=str(data.get("reviewed_at") or ""),
        )


@dataclass(slots=True)
class CouncilSummary:
    overall_decision: str = COUNCIL_DECISION_READY
    highest_severity: str = SEVERITY_LOW
    unresolved_blockers_count: int = 0
    active_roles_count: int = 0
    conflict_count: int = 0
    conflicts: list[ExpertConflict] = field(default_factory=list)
    artifact_patch_proposals: list[ArtifactPatchProposal] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_decision": self.overall_decision,
            "highest_severity": self.highest_severity,
            "unresolved_blockers_count": self.unresolved_blockers_count,
            "active_roles_count": self.active_roles_count,
            "conflict_count": self.conflict_count,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "artifact_patch_proposals": [p.to_dict() for p in self.artifact_patch_proposals],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CouncilSummary:
        return cls(
            overall_decision=str(data.get("overall_decision") or COUNCIL_DECISION_READY),
            highest_severity=str(data.get("highest_severity") or SEVERITY_LOW),
            unresolved_blockers_count=int(data.get("unresolved_blockers_count") or 0),
            active_roles_count=int(data.get("active_roles_count") or 0),
            conflict_count=int(data.get("conflict_count") or 0),
            conflicts=[ExpertConflict.from_dict(c) for c in data.get("conflicts") or []],
            artifact_patch_proposals=[ArtifactPatchProposal.from_dict(p) for p in data.get("artifact_patch_proposals") or []],
        )
