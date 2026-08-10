"""Claimed and verified competency are deliberately separate."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping


class CompetencyProfile:
    @staticmethod
    def claim(skill: str, level: float = 0.5, existing: Mapping[str, Any] | None = None) -> dict[str, Any]:
        value = dict(existing or {})
        value.update({"skill": skill, "claimed": True, "claimed_level": max(0.0, min(1.0, float(level))), "verified_level": float(value.get("verified_level", 0.0)), "evidence": list(value.get("evidence", [])), "history": list(value.get("history", [])), "last_updated": datetime.now(timezone.utc).isoformat()})
        return value

    @staticmethod
    def apply_evidence(existing: Mapping[str, Any] | None, evidence: Mapping[str, Any]) -> dict[str, Any]:
        value = dict(existing or {"skill": evidence.get("skill"), "claimed": False, "claimed_level": 0.0, "verified_level": 0.0, "evidence": [], "history": []})
        evidence_ids = list(value.get("evidence", []))
        evidence_ids.append(str(evidence["evidence_id"]))
        value["evidence"] = list(dict.fromkeys(evidence_ids))
        value["last_evidence_level"] = str(evidence.get("verification_level", "SELF_REPORTED"))
        if evidence.get("verification_status") != "verified":
            value["last_updated"] = datetime.now(timezone.utc).isoformat()
            return value
        old = float(value.get("verified_level", 0.0)); strength = max(0.0, min(1.0, float(evidence.get("strength", 0.0))))
        updated = max(old, round(old + (1 - old) * strength * 0.5, 4))
        verified_ids = list(value.get("verified_evidence", [])); verified_ids.append(str(evidence["evidence_id"])); value["verified_evidence"] = list(dict.fromkeys(verified_ids))
        value.setdefault("history", []).append({"from": old, "to": updated, "evidence_id": evidence["evidence_id"], "at": datetime.now(timezone.utc).isoformat()})
        value.update({"verified_level": updated, "last_updated": datetime.now(timezone.utc).isoformat()})
        return value
