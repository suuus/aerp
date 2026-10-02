import contextlib
import io
import json
import tempfile
import unittest
import uuid
from pathlib import Path

from aerp import cli


def adrp_record() -> dict:
    return {
        "schema_version": "ape-decision-record/v1",
        "decision_id": "ADR-SECURITY-GATE",
        "record_id": str(uuid.uuid4()),
        "record_version": 1,
        "status": "effective",
        "title": "Require security gate",
        "decision_statement": "Deployments must pass a security gate.",
        "context": {},
        "drivers": [],
        "alternatives": [],
        "selected_alternative": "security-gate",
        "rationale": "Prevent unsafe deployment.",
        "tradeoffs": {},
        "authority": {},
        "provenance": {},
        "lifecycle": {},
        "consequences": {},
        "implementation": {},
        "relationships": {},
        "autonomy": {},
        "gaps": [],
        "ratification": None,
    }


def asrp_record() -> dict:
    return {
        "schema_version": "ape-structure-record/v1",
        "structure_id": "STR-PRODUCTION-DEPLOYMENT",
        "record_id": str(uuid.uuid4()),
        "record_version": 1,
        "status": "effective",
        "title": "Production deployment",
        "description": "Test Structure",
        "scope": ["production deployments"],
        "intent_bindings": [],
        "actors": [],
        "elements": [],
        "gates": [],
        "entry_points": [],
        "evidence_requirements": [],
        "artifacts": [],
        "relationships": {"depends_on": [], "supersedes": []},
        "lifecycle": {
            "effective_from": None,
            "review_by": None,
            "expires_at": None,
            "drift_triggers": [],
        },
        "integrity": {"record_fingerprint": None},
    }


class CliTest(unittest.TestCase):
    def invoke(self, arguments: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = cli.main(arguments)
        return result, stdout.getvalue(), stderr.getvalue()

    def test_example_validates(self) -> None:
        example = Path(__file__).parents[1] / "docs/examples/observation.v1.json"
        result, stdout, stderr = self.invoke(["validate", str(example)])
        self.assertEqual(result, 0, stderr)
        self.assertTrue(json.loads(stdout)["valid"])

    def test_new_record_hashes_artifact_and_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "reports/result.json"
            report.parent.mkdir()
            report.write_text('{"status":"passed"}\n', encoding="utf-8")
            output = root / "evidence.json"
            result, stdout, stderr = self.invoke(
                [
                    "new",
                    "--type",
                    "assessment",
                    "--subject",
                    "api",
                    "--claim",
                    "The API passed the test",
                    "--result",
                    "passed",
                    "--summary",
                    "Test returned passed.",
                    "--producer",
                    "test-runner",
                    "--producer-version",
                    "1",
                    "--identity",
                    "ci:test",
                    "--method",
                    "api-test",
                    "--method-version",
                    "1",
                    "--observed-at",
                    "2026-10-02T10:00:00Z",
                    "--environment",
                    "test",
                    "--target",
                    "api",
                    "--control-ref",
                    "ac-6.1_smt",
                    "--correlation",
                    "workflow_run_id=1234",
                    "--artifact",
                    str(report),
                    "--artifact-root",
                    str(root),
                    "--artifact-role",
                    "report",
                    "--output",
                    str(output),
                ]
            )
            self.assertEqual(result, 0, stderr)
            created = json.loads(stdout)
            self.assertEqual(created["created"], str(output))
            record = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(record["control_refs"], ["ac-6.1_smt"])
            self.assertEqual(
                record["environment"]["correlation_ids"]["workflow_run_id"],
                "1234",
            )

            result, stdout, stderr = self.invoke(
                ["verify", str(output), "--artifact-root", str(root)]
            )
            self.assertEqual(result, 0, stderr)
            self.assertTrue(json.loads(stdout)["valid"])

            report.write_text('{"status":"failed"}\n', encoding="utf-8")
            result, _, stderr = self.invoke(
                ["verify", str(output), "--artifact-root", str(root)]
            )
            self.assertEqual(result, 2)
            self.assertIn("artifact verification failed", stderr)

    def test_bind_creates_new_immutable_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = json.loads(
                (Path(__file__).parents[1] / "docs/examples/observation.v1.json").read_text(
                    encoding="utf-8"
                )
            )
            source_path = root / "source.json"
            source_path.write_text(json.dumps(source), encoding="utf-8")
            decision_path = root / "decision.json"
            decision_path.write_text(json.dumps(adrp_record()), encoding="utf-8")
            output = root / "bound.json"
            result, _, stderr = self.invoke(
                ["bind", str(source_path), str(decision_path), "--output", str(output)]
            )
            self.assertEqual(result, 0, stderr)
            bound = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(bound["decision_bindings"][0]["decision_id"], "ADR-SECURITY-GATE")
            self.assertIsNotNone(bound["integrity"]["record_fingerprint"])
            self.assertEqual(source["decision_bindings"], [])

            result, _, stderr = self.invoke(
                ["bind", str(source_path), str(decision_path), "--output", str(output)]
            )
            self.assertEqual(result, 2)
            self.assertIn("refusing to overwrite", stderr)

    def test_bind_structure_uses_exact_asrp_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.json"
            source.write_text(
                (Path(__file__).parents[1] / "docs/examples/observation.v1.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            structure = root / "structure.json"
            structure.write_text(json.dumps(asrp_record()), encoding="utf-8")
            output = root / "bound.json"
            result, stdout, stderr = self.invoke(
                [
                    "bind-structure",
                    str(source),
                    str(structure),
                    "--output",
                    str(output),
                ]
            )
            self.assertEqual(result, 0, stderr)
            payload = json.loads(stdout)
            self.assertEqual(payload["binding"]["structure_id"], "STR-PRODUCTION-DEPLOYMENT")
            bound = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(bound["structure_bindings"]), 1)

    def test_fingerprint_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            record = json.loads(
                (Path(__file__).parents[1] / "docs/examples/observation.v1.json").read_text(
                    encoding="utf-8"
                )
            )
            record["integrity"]["record_fingerprint"] = cli.fingerprint(record)
            path.write_text(json.dumps(record), encoding="utf-8")
            result, _, stderr = self.invoke(["validate", str(path)])
            self.assertEqual(result, 0, stderr)
            record["claim"]["summary"] = "Changed"
            path.write_text(json.dumps(record), encoding="utf-8")
            result, _, stderr = self.invoke(["validate", str(path)])
            self.assertEqual(result, 2)
            self.assertIn("fingerprint mismatch", stderr)

    def test_artifact_path_cannot_escape_root(self) -> None:
        record = json.loads(
            (Path(__file__).parents[1] / "docs/examples/observation.v1.json").read_text(
                encoding="utf-8"
            )
        )
        record["artifacts"] = [
            {
                "name": "secret.txt",
                "path": "../secret.txt",
                "media_type": "text/plain",
                "digest": "sha256:" + ("0" * 64),
                "role": "supporting",
            }
        ]
        with self.assertRaisesRegex(cli.EvidenceError, "must not escape"):
            cli.validate_record(record)


if __name__ == "__main__":
    unittest.main()
