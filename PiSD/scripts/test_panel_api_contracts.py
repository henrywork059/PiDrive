#!/usr/bin/env python3
"""Validate PiSD panel API contracts and safe panel actions.

This script checks that every planned final-GUI panel has a declared API contract
and that safe panel actions return expected PISD codes. It does not arm real
motor output. In hardware mode, motor channel movement should refuse safely with
PISD-MOT-008 unless the future final GUI explicitly arms it.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pisd.app import create_app  # noqa: E402
from pisd.core.errors import PiSDErrorCodes  # noqa: E402
from pisd.core.panel_contracts import get_panel_contracts  # noqa: E402

OUTPUT_DIR = PROJECT_ROOT / "test_outputs" / "panel_api_contracts"
SUMMARY_PATH = OUTPUT_DIR / "summary.json"

REQUIRED_PANELS = {
    "system-status-panel",
    "camera-preview-panel",
    "camera-settings-panel",
    "motor-settings-panel",
    "motor-channel-panel",
    "manual-drive-panel",
    "safety-stop-panel",
    "error-monitor-panel",
    "api-inspector-panel",
    "validation-panel",
    "recording-panel",
    "model-runtime-panel",
}


@dataclass
class Result:
    label: str
    ok: bool
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "ok": bool(self.ok),
            "code": self.code,
            "message": self.message,
            "details": dict(self.details),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate PiSD panel API contracts.")
    parser.add_argument("--hardware", action="store_true", help="Create app in hardware mode. Real motor output is not armed.")
    parser.add_argument("--static-only", action="store_true", help="Only check contract data; skip Flask endpoint execution.")
    parser.add_argument("--skip-camera", action="store_true", help="Skip safe camera-start/apply contract calls.")
    parser.add_argument("--output", default=str(SUMMARY_PATH), help="Summary JSON output path.")
    return parser.parse_args()


def emit(result: Result) -> None:
    print(f"{'OK' if result.ok else 'FAIL':<4} {result.code:<13} {result.label} - {result.message}")


def check_contract_data() -> list[Result]:
    contracts = get_panel_contracts()
    results: list[Result] = []
    panel_ids = {item.get("id") for item in contracts}
    missing_panels = sorted(REQUIRED_PANELS - panel_ids)
    results.append(
        Result(
            "panel_contract.registry",
            not missing_panels and len(contracts) >= len(REQUIRED_PANELS),
            PiSDErrorCodes.OK if not missing_panels else PiSDErrorCodes.TEST_PANEL_API_CONTRACT_FAILED,
            f"{len(contracts)} panel contracts declared" if not missing_panels else "panel contract registry missing panels",
            {"missing_panels": missing_panels},
        )
    )

    failures: list[dict[str, Any]] = []
    for contract in contracts:
        endpoints = contract.get("endpoints")
        safe_test = contract.get("safe_test")
        expected_codes = (safe_test or {}).get("expected_codes")
        if not contract.get("id") or not contract.get("title") or not isinstance(endpoints, list) or not isinstance(safe_test, dict) or not expected_codes:
            failures.append({"id": contract.get("id"), "problem": "missing id/title/endpoints/safe_test/expected_codes"})
        if contract.get("dangerous_action") and "danger" not in " ".join([str(contract.get("danger_note", "")), str(contract.get("responsive_behavior", ""))]).lower():
            failures.append({"id": contract.get("id"), "problem": "dangerous panel missing safety wording"})
    results.append(
        Result(
            "panel_contract.fields",
            not failures,
            PiSDErrorCodes.OK if not failures else PiSDErrorCodes.TEST_PANEL_API_CONTRACT_FAILED,
            "all panel contracts include required fields" if not failures else "one or more panel contracts are incomplete",
            {"failures": failures},
        )
    )
    return results


def _client_call(client, method: str, path: str, payload: Any) -> tuple[int, dict[str, Any]]:
    if method == "GET":
        response = client.get(path)
    elif method == "POST":
        response = client.post(path, json=payload if payload is not None else {})
    else:
        return 0, {"code": PiSDErrorCodes.TEST_PANEL_CONTRACT_SKIPPED, "message": "No endpoint for future placeholder."}
    return response.status_code, response.get_json(silent=True) or {"code": PiSDErrorCodes.OK if 200 <= response.status_code < 300 else PiSDErrorCodes.TEST_PANEL_API_CONTRACT_FAILED}


def check_manifest_route(client) -> Result:
    response = client.get("/api/panel-testing/manifest")
    payload = response.get_json(silent=True) or {}
    panels = payload.get("panels") or []
    panel_ids = {item.get("id") for item in panels if isinstance(item, dict)}
    has_contracts = all(isinstance(item.get("safe_test"), dict) for item in panels if isinstance(item, dict))
    ok = response.status_code == 200 and payload.get("code") == PiSDErrorCodes.OK and REQUIRED_PANELS.issubset(panel_ids) and has_contracts
    return Result(
        "panel_contract.manifest_route",
        ok,
        payload.get("code") or PiSDErrorCodes.TEST_PANEL_API_CONTRACT_FAILED,
        "manifest route includes panel API contracts" if ok else f"manifest route failed HTTP {response.status_code}",
        {"http_status": response.status_code, "missing_panels": sorted(REQUIRED_PANELS - panel_ids), "has_contracts": has_contracts},
    )


def check_contracts_route(client) -> Result:
    response = client.get("/api/panel-testing/contracts")
    payload = response.get_json(silent=True) or {}
    panels = payload.get("panels") or []
    ok = response.status_code == 200 and payload.get("code") == PiSDErrorCodes.OK and len(panels) >= len(REQUIRED_PANELS)
    return Result(
        "panel_contract.contracts_route",
        ok,
        payload.get("code") or PiSDErrorCodes.TEST_PANEL_API_CONTRACT_FAILED,
        "contracts route returned panel contracts" if ok else f"contracts route failed HTTP {response.status_code}",
        {"http_status": response.status_code, "panel_count": len(panels)},
    )


def check_safe_panel_actions(client, skip_camera: bool) -> list[Result]:
    results: list[Result] = []
    for contract in get_panel_contracts():
        safe_test = contract.get("safe_test") or {}
        label = safe_test.get("label") or f"panel.{contract.get('id')}.api"
        method = str(safe_test.get("method") or "NONE").upper()
        path = str(safe_test.get("path") or "")
        if skip_camera and path.startswith("/api/camera"):
            result = Result(label, True, PiSDErrorCodes.TEST_PANEL_CONTRACT_SKIPPED, "skipped by --skip-camera", {"panel": contract.get("id")})
            results.append(result)
            continue
        if method == "NONE" or not path:
            code = PiSDErrorCodes.TEST_PANEL_CONTRACT_SKIPPED
            results.append(Result(label, True, code, "future placeholder intentionally skipped", {"panel": contract.get("id")}))
            continue
        status, payload = _client_call(client, method, path, safe_test.get("payload"))
        code = str(payload.get("code") or PiSDErrorCodes.TEST_PANEL_API_CONTRACT_FAILED)
        expected = {str(item) for item in safe_test.get("expected_codes") or [PiSDErrorCodes.OK]}
        ok = code in expected
        results.append(
            Result(
                label,
                ok,
                code,
                f"safe action returned expected code via HTTP {status}" if ok else f"safe action returned HTTP {status}, expected {sorted(expected)}",
                {"panel": contract.get("id"), "method": method, "path": path, "http_status": status, "expected_codes": sorted(expected)},
            )
        )
    # Always stop at the end of safe checks.
    client.post("/api/control/stop", json={})
    client.post("/api/camera/stop", json={})
    return results


def main() -> int:
    args = parse_args()
    results: list[Result] = []
    for result in check_contract_data():
        emit(result)
        results.append(result)

    if not args.static_only:
        try:
            app = create_app(hardware_enabled=bool(args.hardware))
            client = app.test_client()
        except RuntimeError as exc:
            result = Result("panel_contract.create_app", False, PiSDErrorCodes.APP_DEPENDENCY_MISSING, f"Flask app could not be created: {exc}")
            emit(result)
            results.append(result)
        else:
            for result in [check_manifest_route(client), check_contracts_route(client), *check_safe_panel_actions(client, bool(args.skip_camera))]:
                emit(result)
                results.append(result)

    failed = [item for item in results if not item.ok]
    summary = {
        "ok": not failed,
        "code": PiSDErrorCodes.OK if not failed else PiSDErrorCodes.TEST_PANEL_API_CONTRACT_FAILED,
        "hardware_requested": bool(args.hardware),
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "results": [item.as_dict() for item in results],
    }
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("-" * 72)
    print(f"{'OK' if not failed else 'FAIL':<4} {summary['code']:<13} summary - passed={summary['passed']} failed={summary['failed']} output={output_path}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
