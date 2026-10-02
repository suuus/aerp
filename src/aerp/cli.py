#!/usr/bin/env python3
"""Create, bind, bundle, validate, and verify AERP evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION = "0.1.0"
RECORD_SCHEMA_VERSION = "aerp-evidence-record/v1"
BUNDLE_SCHEMA_VERSION = "aerp-evidence-bundle/v1"
ADRP_SCHEMA_VERSION = "ape-decision-record/v1"
ASRP_SCHEMA_VERSION = "ape-structure-record/v1"
IN_TOTO_STATEMENT = "https://in-toto.io/Statement/v1"
IN_TOTO_PREDICATE = "https://aerp.dev/predicate/evidence-bundle/v1"
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
DECISION_ID = re.compile(r"^[A-Z][A-Z0-9-]{2,63}$")
STRUCTURE_ID = re.compile(r"^STR-[A-Z0-9][A-Z0-9-]{1,62}$")
ADRP_REQUIRED_KEYS = {
    "schema_version",
    "decision_id",
    "record_id",
    "record_version",
    "status",
    "title",
    "decision_statement",
    "context",
    "drivers",
    "alternatives",
    "selected_alternative",
    "rationale",
    "tradeoffs",
    "authority",
    "provenance",
    "lifecycle",
    "consequences",
    "implementation",
    "relationships",
    "autonomy",
    "gaps",
    "ratification",
}
ASRP_REQUIRED_KEYS = {
    "schema_version",
    "structure_id",
    "record_id",
    "record_version",
    "status",
    "title",
    "description",
    "scope",
    "intent_bindings",
    "actors",
    "elements",
    "gates",
    "entry_points",
    "evidence_requirements",
    "artifacts",
    "relationships",
    "lifecycle",
    "integrity",
}
EVIDENCE_TYPES = {"observation", "assessment", "approval", "execution", "outcome", "drift"}
RESULTS = {
    "observed",
    "passed",
    "failed",
    "warning",
    "inconclusive",
    "error",
    "succeeded",
    "not-applicable",
}
ARTIFACT_ROLES = {"input", "output", "supporting", "report", "log", "snapshot", "policy"}
RECORD_KEYS = {
    "schema_version",
    "evidence_id",
    "evidence_type",
    "subject",
    "claim",
    "producer",
    "method",
    "timing",
    "environment",
    "decision_bindings",
    "structure_bindings",
    "policy_refs",
    "control_refs",
    "artifacts",
    "relationships",
    "integrity",
}
BUNDLE_KEYS = {
    "schema_version",
    "bundle_id",
    "created_at",
    "producer",
    "subject",
    "records",
    "integrity",
}
GIT_APE_ARTIFACTS = {
    "requirements.json": ("observation", "input"),
    "template.json": ("execution", "output"),
    "parameters.json": ("execution", "input"),
    "architecture.md": ("observation", "report"),
    "security-analysis.md": ("assessment", "report"),
    "security-gate.json": ("assessment", "report"),
    "policy-assessment.md": ("assessment", "report"),
    "policy-recommendations.json": ("assessment", "supporting"),
    "availability-report.md": ("assessment", "report"),
    "preflight-report.md": ("assessment", "report"),
    "cost-estimate.json": ("assessment", "report"),
    "waf-review.md": ("assessment", "report"),
    "metadata.json": ("execution", "supporting"),
    "deployment.log": ("execution", "log"),
    "tests.json": ("outcome", "report"),
    "error.log": ("outcome", "log"),
    "architecture-live.md": ("observation", "snapshot"),
}
GIT_APE_DRIFT_ARTIFACTS = {
    "current-state.json": ("observation", "snapshot"),
    "drift-report.md": ("drift", "report"),
    "drift-details.json": ("drift", "report"),
    "known-drift.json": ("approval", "supporting"),
    "drift-log.jsonl": ("drift", "log"),
}


class EvidenceError(RuntimeError):
    """Raised when evidence violates AERP."""


def fail(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(f"file not found: {path}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"invalid UTF-8 JSON in {path}: {exc}") from exc
    fail(isinstance(value, dict), f"{path} must contain a JSON object")
    return value


def atomic_create(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as exc:
        raise EvidenceError(f"refusing to overwrite immutable artifact: {path}") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            os.chmod(temp_path, stat.S_IMODE(path.stat().st_mode))
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def exact_keys(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    fail(isinstance(value, dict), f"{label} must be an object")
    fail(set(value) == keys, f"{label} keys must be {sorted(keys)}")
    return value


def non_empty_text(value: Any, label: str, *, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    fail(isinstance(value, str) and bool(value.strip()), f"{label} must be non-empty text")


def text_list(value: Any, label: str) -> None:
    fail(isinstance(value, list), f"{label} must be an array")
    fail(all(isinstance(item, str) and item.strip() for item in value), f"{label} must contain text")
    fail(len(value) == len(set(value)), f"{label} must not contain duplicates")


def timestamp(value: Any, label: str, *, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    non_empty_text(value, label)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError(f"{label} must be an ISO-8601 timestamp") from exc
    fail(parsed.tzinfo is not None, f"{label} must include a timezone")


def uuid_value(value: Any, label: str) -> None:
    try:
        uuid.UUID(value)
    except (ValueError, TypeError, AttributeError) as exc:
        raise EvidenceError(f"{label} must be a UUID") from exc


def digest_bytes(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def digest_file(path: Path) -> str:
    try:
        return digest_bytes(path.read_bytes())
    except FileNotFoundError as exc:
        raise EvidenceError(f"artifact not found: {path}") from exc


def payload(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    integrity = result.get("integrity")
    if isinstance(integrity, dict):
        if "record_fingerprint" in integrity:
            integrity["record_fingerprint"] = None
        if "bundle_fingerprint" in integrity:
            integrity["bundle_fingerprint"] = None
    return result


def canonical_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(payload(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fingerprint(value: dict[str, Any]) -> str:
    return digest_bytes(canonical_bytes(value))


def validate_producer(value: Any, label: str) -> None:
    item = exact_keys(value, {"name", "version", "identity", "invocation_id"}, label)
    non_empty_text(item["name"], f"{label}.name")
    non_empty_text(item["version"], f"{label}.version")
    non_empty_text(item["identity"], f"{label}.identity")
    non_empty_text(item["invocation_id"], f"{label}.invocation_id", nullable=True)


def validate_subject(value: Any, label: str) -> None:
    item = exact_keys(value, {"name", "uri", "digest"}, label)
    non_empty_text(item["name"], f"{label}.name")
    non_empty_text(item["uri"], f"{label}.uri", nullable=True)
    digest = item["digest"]
    fail(digest is None or (isinstance(digest, str) and SHA256.fullmatch(digest)), f"{label}.digest is invalid")


def validate_binding(value: Any, label: str) -> None:
    item = exact_keys(
        value,
        {"decision_id", "record_id", "record_version", "record_fingerprint"},
        label,
    )
    fail(isinstance(item["decision_id"], str) and DECISION_ID.fullmatch(item["decision_id"]), f"{label}.decision_id is invalid")
    uuid_value(item["record_id"], f"{label}.record_id")
    fail(isinstance(item["record_version"], int) and item["record_version"] >= 1, f"{label}.record_version is invalid")
    fail(isinstance(item["record_fingerprint"], str) and SHA256.fullmatch(item["record_fingerprint"]), f"{label}.record_fingerprint is invalid")


def validate_structure_binding(value: Any, label: str) -> None:
    item = exact_keys(
        value,
        {"structure_id", "record_id", "record_version", "record_fingerprint"},
        label,
    )
    fail(
        isinstance(item["structure_id"], str)
        and STRUCTURE_ID.fullmatch(item["structure_id"]),
        f"{label}.structure_id is invalid",
    )
    uuid_value(item["record_id"], f"{label}.record_id")
    fail(
        isinstance(item["record_version"], int) and item["record_version"] >= 1,
        f"{label}.record_version is invalid",
    )
    fail(
        isinstance(item["record_fingerprint"], str)
        and SHA256.fullmatch(item["record_fingerprint"]),
        f"{label}.record_fingerprint is invalid",
    )


def validate_artifact(value: Any, label: str) -> None:
    item = exact_keys(value, {"name", "path", "media_type", "digest", "role"}, label)
    non_empty_text(item["name"], f"{label}.name")
    non_empty_text(item["path"], f"{label}.path")
    artifact_path = Path(item["path"])
    fail(not artifact_path.is_absolute(), f"{label}.path must be relative")
    fail(".." not in artifact_path.parts, f"{label}.path must not escape the artifact root")
    non_empty_text(item["media_type"], f"{label}.media_type")
    fail(isinstance(item["digest"], str) and SHA256.fullmatch(item["digest"]), f"{label}.digest is invalid")
    fail(item["role"] in ARTIFACT_ROLES, f"{label}.role is invalid")


def validate_record(record: dict[str, Any], *, check_fingerprint: bool = True) -> None:
    exact_keys(record, RECORD_KEYS, "record")
    fail(record["schema_version"] == RECORD_SCHEMA_VERSION, f"schema_version must be {RECORD_SCHEMA_VERSION}")
    uuid_value(record["evidence_id"], "evidence_id")
    fail(record["evidence_type"] in EVIDENCE_TYPES, "evidence_type is invalid")
    validate_subject(record["subject"], "subject")

    claim = exact_keys(record["claim"], {"statement", "result", "summary", "criteria_refs"}, "claim")
    non_empty_text(claim["statement"], "claim.statement")
    fail(claim["result"] in RESULTS, "claim.result is invalid")
    non_empty_text(claim["summary"], "claim.summary")
    text_list(claim["criteria_refs"], "claim.criteria_refs")
    validate_producer(record["producer"], "producer")

    method = exact_keys(record["method"], {"name", "version", "parameters_digest"}, "method")
    non_empty_text(method["name"], "method.name")
    non_empty_text(method["version"], "method.version")
    fail(
        method["parameters_digest"] is None
        or (isinstance(method["parameters_digest"], str) and SHA256.fullmatch(method["parameters_digest"])),
        "method.parameters_digest is invalid",
    )

    timing = exact_keys(record["timing"], {"observed_at", "valid_from", "valid_until"}, "timing")
    timestamp(timing["observed_at"], "timing.observed_at")
    timestamp(timing["valid_from"], "timing.valid_from", nullable=True)
    timestamp(timing["valid_until"], "timing.valid_until", nullable=True)
    if timing["valid_from"] and timing["valid_until"]:
        start = datetime.fromisoformat(timing["valid_from"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(timing["valid_until"].replace("Z", "+00:00"))
        fail(start <= end, "timing.valid_until must not precede valid_from")

    environment = exact_keys(record["environment"], {"name", "target", "correlation_ids"}, "environment")
    non_empty_text(environment["name"], "environment.name")
    non_empty_text(environment["target"], "environment.target")
    fail(isinstance(environment["correlation_ids"], dict), "environment.correlation_ids must be an object")
    for key, value in environment["correlation_ids"].items():
        non_empty_text(key, "environment.correlation_ids key")
        non_empty_text(value, f"environment.correlation_ids.{key}")

    fail(isinstance(record["decision_bindings"], list), "decision_bindings must be an array")
    for index, binding in enumerate(record["decision_bindings"]):
        validate_binding(binding, f"decision_bindings[{index}]")
    binding_ids = [
        (item["decision_id"], item["record_id"], item["record_version"])
        for item in record["decision_bindings"]
    ]
    fail(len(binding_ids) == len(set(binding_ids)), "decision_bindings must not contain duplicates")
    fail(isinstance(record["structure_bindings"], list), "structure_bindings must be an array")
    for index, binding in enumerate(record["structure_bindings"]):
        validate_structure_binding(binding, f"structure_bindings[{index}]")
    structure_ids = [
        (item["structure_id"], item["record_id"], item["record_version"])
        for item in record["structure_bindings"]
    ]
    fail(
        len(structure_ids) == len(set(structure_ids)),
        "structure_bindings must not contain duplicates",
    )
    text_list(record["policy_refs"], "policy_refs")
    text_list(record["control_refs"], "control_refs")

    fail(isinstance(record["artifacts"], list), "artifacts must be an array")
    for index, artifact in enumerate(record["artifacts"]):
        validate_artifact(artifact, f"artifacts[{index}]")
    artifact_paths = [item["path"] for item in record["artifacts"]]
    fail(len(artifact_paths) == len(set(artifact_paths)), "artifacts must not contain duplicate paths")

    relationships = exact_keys(record["relationships"], {"derived_from", "supersedes", "revokes"}, "relationships")
    for key in relationships:
        text_list(relationships[key], f"relationships.{key}")

    integrity = exact_keys(record["integrity"], {"record_fingerprint"}, "integrity")
    stored = integrity["record_fingerprint"]
    fail(stored is None or (isinstance(stored, str) and SHA256.fullmatch(stored)), "integrity.record_fingerprint is invalid")
    if check_fingerprint and stored is not None:
        fail(stored == fingerprint(record), "record fingerprint mismatch")


def validate_bundle(bundle: dict[str, Any], *, check_fingerprint: bool = True) -> None:
    exact_keys(bundle, BUNDLE_KEYS, "bundle")
    fail(bundle["schema_version"] == BUNDLE_SCHEMA_VERSION, f"schema_version must be {BUNDLE_SCHEMA_VERSION}")
    uuid_value(bundle["bundle_id"], "bundle_id")
    timestamp(bundle["created_at"], "created_at")
    validate_producer(bundle["producer"], "producer")
    validate_subject(bundle["subject"], "subject")
    fail(isinstance(bundle["records"], list) and bundle["records"], "records must be a non-empty array")
    for index, record in enumerate(bundle["records"]):
        validate_record(record)
    evidence_ids = [item["evidence_id"] for item in bundle["records"]]
    fail(len(evidence_ids) == len(set(evidence_ids)), "bundle records must have unique evidence_id values")
    integrity = exact_keys(bundle["integrity"], {"bundle_fingerprint"}, "integrity")
    stored = integrity["bundle_fingerprint"]
    fail(stored is None or (isinstance(stored, str) and SHA256.fullmatch(stored)), "integrity.bundle_fingerprint is invalid")
    if check_fingerprint and stored is not None:
        fail(stored == fingerprint(bundle), "bundle fingerprint mismatch")


def detect_and_validate(value: dict[str, Any]) -> str:
    schema_version = value.get("schema_version")
    if schema_version == RECORD_SCHEMA_VERSION:
        validate_record(value)
        return "record"
    if schema_version == BUNDLE_SCHEMA_VERSION:
        validate_bundle(value)
        return "bundle"
    raise EvidenceError(f"unsupported schema_version: {schema_version!r}")


def media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".json": "application/json",
        ".jsonl": "application/x-ndjson",
        ".md": "text/markdown",
        ".log": "text/plain",
        ".txt": "text/plain",
        ".yaml": "application/yaml",
        ".yml": "application/yaml",
    }.get(suffix, "application/octet-stream")


def adrp_payload(record: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(record)
    result.pop("ratification", None)
    return result


def adrp_fingerprint(record: dict[str, Any]) -> str:
    content = json.dumps(adrp_payload(record), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return digest_bytes(content)


def decision_binding(path: Path) -> dict[str, Any]:
    record = read_json(path)
    fail(record.get("schema_version") == ADRP_SCHEMA_VERSION, f"{path} is not an ADRP v1 record")
    missing = ADRP_REQUIRED_KEYS - set(record)
    fail(not missing, f"{path} is missing ADRP fields: {sorted(missing)}")
    decision_id = record.get("decision_id")
    fail(isinstance(decision_id, str) and DECISION_ID.fullmatch(decision_id), f"{path} has invalid decision_id")
    uuid_value(record.get("record_id"), f"{path}.record_id")
    version = record.get("record_version")
    fail(isinstance(version, int) and version >= 1, f"{path}.record_version is invalid")
    calculated = adrp_fingerprint(record)
    ratification = record.get("ratification")
    if isinstance(ratification, dict) and ratification.get("record_fingerprint"):
        fail(ratification["record_fingerprint"] == calculated, f"{path} ADRP fingerprint mismatch")
    return {
        "decision_id": decision_id,
        "record_id": record["record_id"],
        "record_version": version,
        "record_fingerprint": calculated,
    }


def structure_binding(path: Path) -> dict[str, Any]:
    record = read_json(path)
    fail(record.get("schema_version") == ASRP_SCHEMA_VERSION, f"{path} is not an ASRP v1 record")
    missing = ASRP_REQUIRED_KEYS - set(record)
    fail(not missing, f"{path} is missing ASRP fields: {sorted(missing)}")
    binding = {
        "structure_id": record["structure_id"],
        "record_id": record["record_id"],
        "record_version": record["record_version"],
        "record_fingerprint": fingerprint(record),
    }
    validate_structure_binding(binding, str(path))
    stored = record.get("integrity", {}).get("record_fingerprint")
    if stored is not None:
        fail(stored == binding["record_fingerprint"], f"{path} ASRP fingerprint mismatch")
    return binding


def producer(name: str, version: str, identity: str, invocation_id: str | None) -> dict[str, Any]:
    return {
        "name": name,
        "version": version,
        "identity": identity,
        "invocation_id": invocation_id,
    }


def artifact(path: Path, root: Path, role: str) -> dict[str, Any]:
    relative = path.relative_to(root).as_posix()
    return {
        "name": path.name,
        "path": relative,
        "media_type": media_type(path),
        "digest": digest_file(path),
        "role": role,
    }


def make_record(
    *,
    evidence_type: str,
    subject_name: str,
    subject_uri: str | None,
    subject_digest: str | None,
    statement: str,
    result: str,
    summary: str,
    producer_value: dict[str, Any],
    method_name: str,
    method_version: str,
    observed_at: str,
    valid_from: str | None,
    valid_until: str | None,
    environment_name: str,
    target: str,
    bindings: list[dict[str, Any]],
    structure_bindings: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
    criteria_refs: list[str] | None = None,
    policy_refs: list[str] | None = None,
    control_refs: list[str] | None = None,
    relationships: dict[str, list[str]] | None = None,
    correlation_ids: dict[str, str] | None = None,
) -> dict[str, Any]:
    record = {
        "schema_version": RECORD_SCHEMA_VERSION,
        "evidence_id": str(uuid.uuid4()),
        "evidence_type": evidence_type,
        "subject": {"name": subject_name, "uri": subject_uri, "digest": subject_digest},
        "claim": {
            "statement": statement,
            "result": result,
            "summary": summary,
            "criteria_refs": criteria_refs or [],
        },
        "producer": producer_value,
        "method": {"name": method_name, "version": method_version, "parameters_digest": None},
        "timing": {
            "observed_at": observed_at,
            "valid_from": valid_from,
            "valid_until": valid_until,
        },
        "environment": {
            "name": environment_name,
            "target": target,
            "correlation_ids": correlation_ids or {},
        },
        "decision_bindings": bindings,
        "structure_bindings": structure_bindings,
        "policy_refs": policy_refs or [],
        "control_refs": control_refs or [],
        "artifacts": artifacts,
        "relationships": relationships
        or {"derived_from": [], "supersedes": [], "revokes": []},
        "integrity": {"record_fingerprint": None},
    }
    record["integrity"]["record_fingerprint"] = fingerprint(record)
    validate_record(record)
    return record


def parse_pairs(values: list[str], label: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        key, separator, item = value.partition("=")
        fail(bool(separator) and bool(key.strip()) and bool(item.strip()), f"{label} must use KEY=VALUE")
        fail(key not in result, f"{label} contains duplicate key: {key}")
        result[key] = item
    return result


def command_new(args: argparse.Namespace) -> dict[str, Any]:
    bindings = [decision_binding(Path(item)) for item in args.decision]
    structures = [structure_binding(Path(item)) for item in args.structure]
    observed_at = args.observed_at or utc_now()
    artifacts: list[dict[str, Any]] = []
    root = Path(args.artifact_root).resolve()
    for item in args.artifact:
        path = Path(item).resolve()
        fail(path.is_file(), f"artifact not found: {path}")
        try:
            artifacts.append(artifact(path, root, args.artifact_role))
        except ValueError as exc:
            raise EvidenceError(f"artifact {path} is outside artifact root {root}") from exc
    record = make_record(
        evidence_type=args.type,
        subject_name=args.subject,
        subject_uri=args.subject_uri,
        subject_digest=args.subject_digest,
        statement=args.claim,
        result=args.result,
        summary=args.summary,
        producer_value=producer(args.producer, args.producer_version, args.identity, args.invocation_id),
        method_name=args.method,
        method_version=args.method_version,
        observed_at=observed_at,
        valid_from=args.valid_from,
        valid_until=args.valid_until,
        environment_name=args.environment,
        target=args.target,
        bindings=bindings,
        structure_bindings=structures,
        artifacts=artifacts,
        criteria_refs=args.criteria_ref,
        policy_refs=args.policy_ref,
        control_refs=args.control_ref,
        relationships={
            "derived_from": args.derived_from,
            "supersedes": args.supersedes,
            "revokes": args.revokes,
        },
        correlation_ids=parse_pairs(args.correlation, "correlation"),
    )
    atomic_create(Path(args.output), record)
    return {"created": args.output, "evidence_id": record["evidence_id"], "fingerprint": fingerprint(record)}


def command_bind(args: argparse.Namespace) -> dict[str, Any]:
    record = read_json(Path(args.record))
    validate_record(record)
    binding = decision_binding(Path(args.decision))
    key = (binding["decision_id"], binding["record_id"], binding["record_version"])
    existing = {
        (item["decision_id"], item["record_id"], item["record_version"])
        for item in record["decision_bindings"]
    }
    fail(key not in existing, "record already contains this decision binding")
    record["decision_bindings"].append(binding)
    record["decision_bindings"].sort(key=lambda item: (item["decision_id"], item["record_version"], item["record_id"]))
    record["integrity"]["record_fingerprint"] = fingerprint(record)
    validate_record(record)
    atomic_create(Path(args.output), record)
    return {"created": args.output, "binding": binding, "fingerprint": fingerprint(record)}


def command_bind_structure(args: argparse.Namespace) -> dict[str, Any]:
    record = read_json(Path(args.record))
    validate_record(record)
    binding = structure_binding(Path(args.structure))
    key = (binding["structure_id"], binding["record_id"], binding["record_version"])
    existing = {
        (item["structure_id"], item["record_id"], item["record_version"])
        for item in record["structure_bindings"]
    }
    fail(key not in existing, "record already contains this structure binding")
    record["structure_bindings"].append(binding)
    record["structure_bindings"].sort(
        key=lambda item: (item["structure_id"], item["record_version"], item["record_id"])
    )
    record["integrity"]["record_fingerprint"] = fingerprint(record)
    validate_record(record)
    atomic_create(Path(args.output), record)
    return {"created": args.output, "binding": binding, "fingerprint": fingerprint(record)}


def infer_git_ape_result(path: Path, evidence_type: str) -> str:
    name = path.name
    if name == "error.log":
        return "failed"
    if name in {"security-gate.json", "tests.json", "metadata.json"}:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return "observed"
        candidates = [
            value.get("result"),
            value.get("status"),
            value.get("overallStatus"),
            value.get("overall_status"),
            value.get("summary", {}).get("status") if isinstance(value.get("summary"), dict) else None,
        ]
        normalized = " ".join(str(item).lower() for item in candidates if item is not None)
        if any(word in normalized for word in ("fail", "block", "error", "unhealthy")):
            return "failed"
        if any(word in normalized for word in ("pass", "succeed", "healthy", "complete")):
            return "passed" if evidence_type == "assessment" else "succeeded"
    if evidence_type == "execution":
        return "observed"
    if evidence_type == "outcome":
        return "observed"
    return "observed"


def command_bundle_git_ape(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.deployment).resolve()
    fail(root.is_dir(), f"deployment directory not found: {root}")
    deployment_id = root.name
    observed_at = args.observed_at or utc_now()
    bindings = [decision_binding(Path(item)) for item in args.decision]
    structures = [structure_binding(Path(item)) for item in args.structure]
    producer_value = producer(
        args.producer,
        args.producer_version,
        args.identity,
        args.invocation_id or deployment_id,
    )
    records: list[dict[str, Any]] = []
    candidates: list[tuple[Path, str, str]] = []
    for name, (evidence_type, role) in GIT_APE_ARTIFACTS.items():
        path = root / name
        if path.is_file():
            candidates.append((path, evidence_type, role))
    drift_root = root / "drift-analysis"
    for name, (evidence_type, role) in GIT_APE_DRIFT_ARTIFACTS.items():
        path = drift_root / name
        if path.is_file():
            candidates.append((path, evidence_type, role))
    fail(candidates, f"no recognised Git-Ape artifacts found in {root}")

    for path, evidence_type, role in sorted(candidates, key=lambda item: item[0].as_posix()):
        item = artifact(path, root, role)
        result = infer_git_ape_result(path, evidence_type)
        records.append(
            make_record(
                evidence_type=evidence_type,
                subject_name=path.stem,
                subject_uri=f"git-ape:deployment:{deployment_id}#{item['path']}",
                subject_digest=None,
                statement=f"Git-Ape produced {item['path']} during deployment {deployment_id}",
                result=result,
                summary=f"Captured and fingerprinted Git-Ape artifact {item['path']}.",
                producer_value=producer_value,
                method_name="aerp-git-ape-adapter",
                method_version=VERSION,
                observed_at=observed_at,
                valid_from=None,
                valid_until=None,
                environment_name=args.environment,
                target=args.target,
                bindings=bindings,
                structure_bindings=structures,
                artifacts=[item],
                correlation_ids={"git_ape_deployment_id": deployment_id},
            )
        )

    bundle = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "bundle_id": str(uuid.uuid4()),
        "created_at": observed_at,
        "producer": producer_value,
        "subject": {
            "name": deployment_id,
            "uri": f"git-ape:deployment:{deployment_id}",
            "digest": None,
        },
        "records": records,
        "integrity": {"bundle_fingerprint": None},
    }
    bundle["integrity"]["bundle_fingerprint"] = fingerprint(bundle)
    validate_bundle(bundle)
    atomic_create(Path(args.output), bundle)
    return {
        "created": args.output,
        "bundle_id": bundle["bundle_id"],
        "records": len(records),
        "fingerprint": fingerprint(bundle),
    }


def verify_artifacts(record: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in record["artifacts"]:
        path = root / item["path"]
        resolved = path.resolve(strict=False)
        within_root = resolved.is_relative_to(root)
        exists = within_root and resolved.is_file()
        actual = digest_file(path) if exists else None
        results.append(
            {
                "path": item["path"],
                "within_artifact_root": within_root,
                "exists": exists,
                "expected_digest": item["digest"],
                "actual_digest": actual,
                "valid": exists and actual == item["digest"],
            }
        )
    return results


def command_verify(args: argparse.Namespace) -> dict[str, Any]:
    value = read_json(Path(args.path))
    kind = detect_and_validate(value)
    root = Path(args.artifact_root).resolve()
    records = [value] if kind == "record" else value["records"]
    artifact_results = [
        result
        for record in records
        for result in verify_artifacts(record, root)
    ]
    valid = all(item["valid"] for item in artifact_results)
    fail(valid or args.allow_missing_artifacts, "artifact verification failed")
    return {
        "kind": kind,
        "valid": valid,
        "records": len(records),
        "artifacts": artifact_results,
    }


def command_inspect(args: argparse.Namespace) -> dict[str, Any]:
    value = read_json(Path(args.path))
    kind = detect_and_validate(value)
    if kind == "record":
        return {
            "kind": kind,
            "evidence_id": value["evidence_id"],
            "evidence_type": value["evidence_type"],
            "subject": value["subject"],
            "result": value["claim"]["result"],
            "decision_bindings": value["decision_bindings"],
            "structure_bindings": value["structure_bindings"],
            "artifacts": value["artifacts"],
            "fingerprint": fingerprint(value),
        }
    results: dict[str, int] = {}
    evidence_types: dict[str, int] = {}
    decisions: set[tuple[str, str, int, str]] = set()
    structures: set[tuple[str, str, int, str]] = set()
    for record in value["records"]:
        results[record["claim"]["result"]] = results.get(record["claim"]["result"], 0) + 1
        evidence_types[record["evidence_type"]] = evidence_types.get(record["evidence_type"], 0) + 1
        for item in record["decision_bindings"]:
            decisions.add(
                (
                    item["decision_id"],
                    item["record_id"],
                    item["record_version"],
                    item["record_fingerprint"],
                )
            )
        for item in record["structure_bindings"]:
            structures.add(
                (
                    item["structure_id"],
                    item["record_id"],
                    item["record_version"],
                    item["record_fingerprint"],
                )
            )
    return {
        "kind": kind,
        "bundle_id": value["bundle_id"],
        "subject": value["subject"],
        "records": len(value["records"]),
        "evidence_types": evidence_types,
        "results": results,
        "decision_bindings": [
            {
                "decision_id": item[0],
                "record_id": item[1],
                "record_version": item[2],
                "record_fingerprint": item[3],
            }
            for item in sorted(decisions)
        ],
        "structure_bindings": [
            {
                "structure_id": item[0],
                "record_id": item[1],
                "record_version": item[2],
                "record_fingerprint": item[3],
            }
            for item in sorted(structures)
        ],
        "fingerprint": fingerprint(value),
    }


def command_export_intoto(args: argparse.Namespace) -> dict[str, Any]:
    bundle = read_json(Path(args.bundle))
    validate_bundle(bundle)
    subjects: dict[tuple[str, str], dict[str, Any]] = {}
    for record in bundle["records"]:
        for item in record["artifacts"]:
            algorithm, digest = item["digest"].split(":", 1)
            subjects[(item["path"], digest)] = {
                "name": item["path"],
                "digest": {algorithm: digest},
            }
    statement = {
        "_type": IN_TOTO_STATEMENT,
        "subject": [subjects[key] for key in sorted(subjects)],
        "predicateType": IN_TOTO_PREDICATE,
        "predicate": bundle,
    }
    atomic_create(Path(args.output), statement)
    return {"created": args.output, "subjects": len(statement["subject"]), "predicateType": IN_TOTO_PREDICATE}


def command_export_oscal(args: argparse.Namespace) -> dict[str, Any]:
    bundle = read_json(Path(args.bundle))
    validate_bundle(bundle)
    findings = []
    observations = []
    for record in bundle["records"]:
        observation_uuid = record["evidence_id"]
        observations.append(
            {
                "uuid": observation_uuid,
                "title": record["claim"]["statement"],
                "description": record["claim"]["summary"],
                "methods": [record["method"]["name"]],
                "collected": record["timing"]["observed_at"],
                "props": [
                    {"name": "aerp-evidence-type", "value": record["evidence_type"]},
                    {"name": "aerp-result", "value": record["claim"]["result"]},
                    {"name": "aerp-fingerprint", "value": record["integrity"]["record_fingerprint"]},
                ],
                "relevant-evidence": [
                    {
                        "description": item["name"],
                        "href": item["path"],
                        "props": [{"name": "sha256", "value": item["digest"].split(":", 1)[1]}],
                    }
                    for item in record["artifacts"]
                ],
            }
        )
        if (
            record["evidence_type"] == "assessment"
            and record["claim"]["result"] in {"passed", "failed"}
        ):
            for control_ref in record["control_refs"]:
                findings.append(
                    {
                        "uuid": str(
                            uuid.uuid5(
                                uuid.UUID(bundle["bundle_id"]),
                                f"{record['evidence_id']}:{control_ref}",
                            )
                        ),
                        "title": record["claim"]["statement"],
                        "description": record["claim"]["summary"],
                        "target": {
                            "type": "statement-id",
                            "target-id": control_ref,
                            "description": (
                                "Mechanical projection from an AERP assessment. "
                                "Applicability requires independent confirmation."
                            ),
                            "status": {
                                "state": (
                                    "satisfied"
                                    if record["claim"]["result"] == "passed"
                                    else "not-satisfied"
                                ),
                                "reason": (
                                    "pass"
                                    if record["claim"]["result"] == "passed"
                                    else "fail"
                                ),
                            },
                        },
                        "related-observations": [{"observation-uuid": observation_uuid}],
                    }
                )
    exported = {
        "assessment-results": {
            "uuid": bundle["bundle_id"],
            "metadata": {
                "title": f"AERP evidence for {bundle['subject']['name']}",
                "last-modified": bundle["created_at"],
                "version": VERSION,
                "oscal-version": "1.1.2",
            },
            "import-ap": {"href": "urn:aerp:no-assessment-plan"},
            "results": [
                {
                    "uuid": str(uuid.uuid5(uuid.UUID(bundle["bundle_id"]), "result")),
                    "title": f"AERP bundle {bundle['bundle_id']}",
                    "description": "Mechanical projection from AERP. Applicability and compliance standing require separate assessment.",
                    "start": bundle["created_at"],
                    "reviewed-controls": {
                        "description": (
                            "AERP does not determine control applicability. "
                            "The receiving assessment process must replace this selection."
                        ),
                        "control-selections": [{"include-all": {}}],
                    },
                    "observations": observations,
                    "findings": findings,
                    "risks": [],
                }
            ],
        },
    }
    atomic_create(Path(args.output), exported)
    return {"created": args.output, "observations": len(observations), "findings": len(findings)}


def emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="aerp", description=__doc__)
    root.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    sub = root.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="Validate an AERP record or bundle")
    validate.add_argument("path")

    fingerprint_command = sub.add_parser("fingerprint", help="Print the canonical fingerprint")
    fingerprint_command.add_argument("path")

    inspect = sub.add_parser("inspect", help="Summarise an AERP record or bundle")
    inspect.add_argument("path")

    new = sub.add_parser("new", help="Create an immutable evidence record")
    new.add_argument("--type", required=True, choices=sorted(EVIDENCE_TYPES))
    new.add_argument("--subject", required=True)
    new.add_argument("--subject-uri")
    new.add_argument("--subject-digest")
    new.add_argument("--claim", required=True)
    new.add_argument("--result", required=True, choices=sorted(RESULTS))
    new.add_argument("--summary", required=True)
    new.add_argument("--producer", required=True)
    new.add_argument("--producer-version", required=True)
    new.add_argument("--identity", required=True)
    new.add_argument("--invocation-id")
    new.add_argument("--method", required=True)
    new.add_argument("--method-version", required=True)
    new.add_argument("--observed-at")
    new.add_argument("--valid-from")
    new.add_argument("--valid-until")
    new.add_argument("--environment", required=True)
    new.add_argument("--target", required=True)
    new.add_argument("--correlation", action="append", default=[], metavar="KEY=VALUE")
    new.add_argument("--decision", action="append", default=[])
    new.add_argument("--structure", action="append", default=[])
    new.add_argument("--criteria-ref", action="append", default=[])
    new.add_argument("--policy-ref", action="append", default=[])
    new.add_argument("--control-ref", action="append", default=[])
    new.add_argument("--derived-from", action="append", default=[])
    new.add_argument("--supersedes", action="append", default=[])
    new.add_argument("--revokes", action="append", default=[])
    new.add_argument("--artifact", action="append", default=[])
    new.add_argument("--artifact-root", default=".")
    new.add_argument("--artifact-role", choices=sorted(ARTIFACT_ROLES), default="supporting")
    new.add_argument("--output", required=True)

    bind = sub.add_parser("bind", help="Create a new record bound to an ADRP decision")
    bind.add_argument("record")
    bind.add_argument("decision")
    bind.add_argument("--output", required=True)

    bind_structure = sub.add_parser("bind-structure", help="Create a new record bound to an ASRP Structure record")
    bind_structure.add_argument("record")
    bind_structure.add_argument("structure")
    bind_structure.add_argument("--output", required=True)

    bundle = sub.add_parser("bundle-git-ape", help="Bundle a Git-Ape deployment trace")
    bundle.add_argument("deployment")
    bundle.add_argument("--decision", action="append", default=[])
    bundle.add_argument("--structure", action="append", default=[])
    bundle.add_argument("--producer", default="git-ape")
    bundle.add_argument("--producer-version", default="unknown")
    bundle.add_argument("--identity", required=True)
    bundle.add_argument("--invocation-id")
    bundle.add_argument("--observed-at")
    bundle.add_argument("--environment", default="azure")
    bundle.add_argument("--target", required=True)
    bundle.add_argument("--output", required=True)

    verify = sub.add_parser("verify", help="Verify fingerprints and referenced artifacts")
    verify.add_argument("path")
    verify.add_argument("--artifact-root", default=".")
    verify.add_argument("--allow-missing-artifacts", action="store_true")

    export_intoto = sub.add_parser("export-intoto", help="Export a bundle as an in-toto Statement")
    export_intoto.add_argument("bundle")
    export_intoto.add_argument("--output", required=True)

    export_oscal = sub.add_parser("export-oscal", help="Project evidence into OSCAL Assessment Results")
    export_oscal.add_argument("bundle")
    export_oscal.add_argument("--output", required=True)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "validate":
            value = read_json(Path(args.path))
            emit({"kind": detect_and_validate(value), "valid": True, "fingerprint": fingerprint(value)})
        elif args.command == "fingerprint":
            value = read_json(Path(args.path))
            detect_and_validate(value)
            print(fingerprint(value))
        elif args.command == "inspect":
            emit(command_inspect(args))
        elif args.command == "new":
            emit(command_new(args))
        elif args.command == "bind":
            emit(command_bind(args))
        elif args.command == "bind-structure":
            emit(command_bind_structure(args))
        elif args.command == "bundle-git-ape":
            emit(command_bundle_git_ape(args))
        elif args.command == "verify":
            emit(command_verify(args))
        elif args.command == "export-intoto":
            emit(command_export_intoto(args))
        elif args.command == "export-oscal":
            emit(command_export_oscal(args))
        else:
            raise EvidenceError(f"unsupported command: {args.command}")
    except EvidenceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
