import json
import re
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RepositoryContractTest(unittest.TestCase):
    def test_versions_match(self) -> None:
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        plugin = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        marketplace = json.loads(
            (ROOT / ".github/plugin/marketplace.json").read_text(encoding="utf-8")
        )
        cli_text = (ROOT / "src/aerp/cli.py").read_text(encoding="utf-8")
        cli_version = re.search(r'^VERSION = "([^"]+)"$', cli_text, re.MULTILINE)
        self.assertIsNotNone(cli_version)
        expected = pyproject["project"]["version"]
        self.assertEqual(plugin["version"], expected)
        self.assertEqual(marketplace["metadata"]["version"], expected)
        self.assertEqual(marketplace["plugins"][0]["version"], expected)
        self.assertEqual(cli_version.group(1), expected)

    def test_agent_and_skills_exist(self) -> None:
        self.assertTrue((ROOT / ".github/agents/aerp.agent.md").is_file())
        expected = {
            "aerp-capture",
            "aerp-bind",
            "aerp-git-ape",
            "aerp-verify",
            "aerp-export",
        }
        actual = {
            path.parent.name
            for path in (ROOT / ".github/skills").glob("*/SKILL.md")
        }
        self.assertEqual(actual, expected)

    def test_relative_markdown_links_resolve(self) -> None:
        markdown_files = [
            ROOT / "README.md",
            ROOT / "CONTRIBUTING.md",
            ROOT / "SECURITY.md",
            *ROOT.joinpath("docs").rglob("*.md"),
        ]
        missing: list[str] = []
        for path in markdown_files:
            text = path.read_text(encoding="utf-8")
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
                if (
                    "://" in target
                    or target.startswith("#")
                    or target.startswith("mailto:")
                ):
                    continue
                file_target = target.split("#", 1)[0]
                if file_target and not (path.parent / file_target).resolve().exists():
                    missing.append(f"{path.relative_to(ROOT)}: {target}")
        self.assertEqual(missing, [])

    def test_json_files_parse(self) -> None:
        paths = [
            ROOT / "schemas/aerp-evidence-record-v1.schema.json",
            ROOT / "schemas/aerp-evidence-bundle-v1.schema.json",
            ROOT / "docs/examples/observation.v1.json",
            ROOT / "plugin.json",
            ROOT / ".github/plugin/marketplace.json",
        ]
        for path in paths:
            with self.subTest(path=path):
                value = json.loads(path.read_text(encoding="utf-8"))
                self.assertIsInstance(value, dict)


if __name__ == "__main__":
    unittest.main()
