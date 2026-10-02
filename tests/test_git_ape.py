import contextlib
import io
import json
import tempfile
import unittest
import uuid
from pathlib import Path

from aerp import cli


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


class GitApeAdapterTest(unittest.TestCase):
    def invoke(self, arguments: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = cli.main(arguments)
        return result, stdout.getvalue(), stderr.getvalue()

    def test_bundle_verify_and_exports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            deployment = Path(directory) / "deploy-20261002-103000"
            deployment.mkdir()
            (deployment / "requirements.json").write_text(
                '{"application":"api"}\n', encoding="utf-8"
            )
            (deployment / "security-gate.json").write_text(
                '{"status":"passed"}\n', encoding="utf-8"
            )
            (deployment / "tests.json").write_text(
                '{"overallStatus":"healthy"}\n', encoding="utf-8"
            )
            drift = deployment / "drift-analysis"
            drift.mkdir()
            (drift / "drift-details.json").write_text(
                '{"differences":[]}\n', encoding="utf-8"
            )
            structure = Path(directory) / "structure.json"
            structure.write_text(json.dumps(asrp_record()), encoding="utf-8")
            bundle = deployment / "evidence/bundle.json"
            result, stdout, stderr = self.invoke(
                [
                    "bundle-git-ape",
                    str(deployment),
                    "--identity",
                    "ci:deploy",
                    "--producer-version",
                    "0.8.0",
                    "--target",
                    "/subscriptions/test/resourceGroups/rg-api",
                    "--structure",
                    str(structure),
                    "--observed-at",
                    "2026-10-02T10:00:00Z",
                    "--output",
                    str(bundle),
                ]
            )
            self.assertEqual(result, 0, stderr)
            self.assertEqual(json.loads(stdout)["records"], 4)
            bundle_value = json.loads(bundle.read_text(encoding="utf-8"))
            self.assertEqual(
                bundle_value["records"][0]["structure_bindings"][0]["structure_id"],
                "STR-PRODUCTION-DEPLOYMENT",
            )

            result, stdout, stderr = self.invoke(
                ["verify", str(bundle), "--artifact-root", str(deployment)]
            )
            self.assertEqual(result, 0, stderr)
            self.assertTrue(json.loads(stdout)["valid"])

            assessment = next(
                record
                for record in bundle_value["records"]
                if record["evidence_type"] == "assessment"
            )
            assessment["control_refs"] = ["ac-6.1_smt"]
            assessment["integrity"]["record_fingerprint"] = cli.fingerprint(assessment)
            bundle_value["integrity"]["bundle_fingerprint"] = cli.fingerprint(bundle_value)
            bundle.write_text(json.dumps(bundle_value), encoding="utf-8")

            statement = deployment / "evidence/statement.json"
            result, _, stderr = self.invoke(
                ["export-intoto", str(bundle), "--output", str(statement)]
            )
            self.assertEqual(result, 0, stderr)
            statement_value = json.loads(statement.read_text(encoding="utf-8"))
            self.assertEqual(statement_value["_type"], cli.IN_TOTO_STATEMENT)
            self.assertEqual(len(statement_value["subject"]), 4)

            oscal = deployment / "evidence/assessment-results.json"
            result, stdout, stderr = self.invoke(
                ["export-oscal", str(bundle), "--output", str(oscal)]
            )
            self.assertEqual(result, 0, stderr)
            exported = json.loads(stdout)
            self.assertEqual(exported["findings"], 1)
            self.assertEqual(exported["observations"], 4)
            oscal_value = json.loads(oscal.read_text(encoding="utf-8"))
            finding = oscal_value["assessment-results"]["results"][0]["findings"][0]
            self.assertEqual(finding["target"]["status"]["state"], "satisfied")

    def test_unknown_artifacts_do_not_create_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            deployment = Path(directory) / "deploy-empty"
            deployment.mkdir()
            (deployment / "unknown.txt").write_text("unknown\n", encoding="utf-8")
            result, _, stderr = self.invoke(
                [
                    "bundle-git-ape",
                    str(deployment),
                    "--identity",
                    "ci:deploy",
                    "--target",
                    "test",
                    "--output",
                    str(deployment / "bundle.json"),
                ]
            )
            self.assertEqual(result, 2)
            self.assertIn("no recognised Git-Ape artifacts", stderr)


if __name__ == "__main__":
    unittest.main()
