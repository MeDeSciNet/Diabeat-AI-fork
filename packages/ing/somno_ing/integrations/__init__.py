"""Outbound integration interfaces (PRD 8.2).

v1 ships interfaces and mock implementations only. Nothing here talks to a real
hospital system, and the mocks record what they would have sent so the shape can
be reviewed before anyone wires up a live endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


class FhirExporter(Protocol):
    def observation(self, session: dict, risk: dict) -> dict: ...
    def detected_issue(self, alert: dict) -> dict: ...


class NurseCallGateway(Protocol):
    def notify(self, alert: dict) -> dict: ...


@dataclass
class MockFhirExporter:
    """Builds FHIR R4 resources without transmitting them anywhere."""

    sent: list[dict] = field(default_factory=list)

    def observation(self, session: dict, risk: dict) -> dict:
        res = {
            "resourceType": "Observation",
            "status": "preliminary",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "procedure",
                        }
                    ]
                }
            ],
            "code": {
                "text": "Overnight swallowing signal index (research use only)",
            },
            "subject": {"identifier": {"value": session.get("subject_code")}},
            "effectiveDateTime": session.get("started_at"),
            "valueQuantity": (
                {"value": risk.get("score"), "unit": "index", "system": "urn:somnoswallow"}
                if risk.get("score") is not None
                else None
            ),
            "dataAbsentReason": (
                {"coding": [{"code": "insufficient-data"}]}
                if risk.get("score") is None
                else None
            ),
            "note": [
                {
                    "text": (
                        "Research use only. Not a diagnosis and not a measure of "
                        "aspiration or pneumonia risk."
                    )
                }
            ],
            "component": [
                {
                    "code": {"text": name},
                    "valueQuantity": {"value": comp["value"], "unit": "normalised"},
                }
                for name, comp in (risk.get("components") or {}).items()
            ],
        }
        self.sent.append(res)
        return res

    def detected_issue(self, alert: dict) -> dict:
        res = {
            "resourceType": "DetectedIssue",
            "status": "preliminary",
            # Never 'high': this system does not assert clinical urgency.
            "severity": "low" if alert.get("severity") != "attention" else "moderate",
            "code": {"text": alert.get("rule_id")},
            "detail": alert.get("title"),
            "identifiedDateTime": alert.get("created_at"),
            "mitigation": [
                {"action": {"text": action}} for action in alert.get("recommended_actions", [])
            ],
        }
        self.sent.append(res)
        return res


@dataclass
class MockNurseCallGateway:
    """Records what a nurse-call webhook would have received.

    Deliberately inert. Wiring this to a real nurse-call system would turn the
    product into an active patient monitor, which PRD 2.1 R1 rules out.
    """

    sent: list[dict] = field(default_factory=list)

    def notify(self, alert: dict) -> dict:
        payload = {
            "at": datetime.now(UTC).isoformat(),
            "bed_id": alert.get("bed_id"),
            "kind": "observation_prompt",
            "urgent": False,
            "title": alert.get("title"),
            "actions": alert.get("recommended_actions", []),
        }
        self.sent.append(payload)
        return {"delivered": False, "reason": "mock gateway - v1 does not transmit", "payload": payload}


_fhir = MockFhirExporter()
_nurse_call = MockNurseCallGateway()


def get_fhir_exporter() -> FhirExporter:
    return _fhir


def get_nurse_call() -> NurseCallGateway:
    return _nurse_call
