"""The adoption of core 0.4.1: the files a render copies whole from sdk-core, at its tag
v0.4.1, the secret scan's rule for the line on which core's recorder writes a cut body's
sha256, and the reference refresh on core's default class name (#42, #167, #190).

Each test reads the renders of ``conftest.py`` and asserts mechanics: a digest equal, what
the render's own detect-secrets hook does with a file, the arguments of a call.
``scripts/prove.sh`` runs the rendered refresh script itself, on the core release.
"""

import ast
import base64
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from helpers import CORE_DEFAULT

# SHA-256 of sdk-core's files that a render copies byte for byte, at v0.4.1, the core
# release the template adopts: git -C <workspace root>/sdk-core show v0.4.1:<path> |
# sha256sum (digests, not secrets). ci.yml and publish.yml, which the template extends by
# its own lines, are pinned by test_template.py once those lines are taken out.
CORE_VERBATIM = {
    # pragma: allowlist nextline secret
    ".pre-commit-config.yaml": "214aa7ed6b8bd72a40f1fe3a7e7060e90e6e0e47d3f06415e6804fb16189cd7e",
    # pragma: allowlist nextline secret
    ".secrets.baseline": "db68bd50b639c34059bb4f8d4f4ca75f41888afa61e19a7bd1be60a54aede51d",
    # pragma: allowlist nextline secret
    ".python-version": "7b55f8e67b5623c4bef3fa691288da9437d79d3aba156de48d481db32ac7d16d",
    # pragma: allowlist nextline secret
    "LICENSE": "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4",
}


def test_the_copies_are_cores_bytes_at_its_tag(keyed_nested: Path) -> None:
    """#190: the files a render copies whole from sdk-core are core's at v0.4.1, the release
    ``core_version`` defaults to."""
    assert CORE_DEFAULT == "0.4.1", "the core release the template adopts, its copies'"
    for rel, digest in CORE_VERBATIM.items():
        assert hashlib.sha256((keyed_nested / rel).read_bytes()).hexdigest() == digest, rel


def secret_scan(render: Path, scan: Path, *files: str) -> subprocess.CompletedProcess[str]:
    """The render's detect-secrets hook on ``files`` in ``scan``, with the arguments that the
    render's ``.pre-commit-config.yaml`` passes it, against a copy of its baseline."""
    config = yaml.safe_load((render / ".pre-commit-config.yaml").read_text())
    (hook,) = [h for repo in config["repos"] for h in repo["hooks"] if h["id"] == "detect-secrets"]
    shutil.copy(render / ".secrets.baseline", scan / ".secrets.baseline")
    return subprocess.run(
        [sys.executable, "-m", "detect_secrets.pre_commit_hook", *hook["args"], *files],
        cwd=scan,
        capture_output=True,
        text=True,
        check=False,
    )


def fixture(**response: object) -> str:
    """A recorded exchange with a cut body, laid out as core's ``fixture_text`` writes one:
    indented JSON, keys sorted, a newline; ``response`` adds to or replaces its fields."""
    whole = b"an answer over the cap"
    cut = {
        "status": 200,
        "headers": [["content-type", "application/json"]],
        "body": "[]",
        "truncated": True,
        "original_bytes": len(whole),
        "sha256": hashlib.sha256(whole).hexdigest(),
        **response,
    }
    request = {"method": "GET", "url": "https://api.example.org/v1/items"}
    return json.dumps({"request": request, "response": cut}, indent=2, sort_keys=True) + "\n"


def test_the_secret_scan_skips_a_fixtures_sha256_line_alone(
    keyed_nested: Path, tmp_path: Path
) -> None:
    """#42: the render's hook passes a cut fixture, whose ``sha256`` line holds 64 hex
    digits, against its unchanged baseline, as sdk-core's rule skips that line. The same
    digits under another key are flagged, and so is a body stored base64, which no line
    rule tells from a text body of the same characters."""
    scan = tmp_path / "scan"
    scan.mkdir()
    digest = json.loads(fixture())["response"]["sha256"]
    binary = base64.b64encode(hashlib.sha512(b"a binary body").digest()).decode("ascii")
    (scan / "cut.json").write_text(fixture())
    (scan / "other_key.json").write_text(fixture(sha256=None, etag=digest))
    (scan / "binary.json").write_text(fixture(body=binary, body_base64=True))
    hook = secret_scan(keyed_nested, scan, "cut.json")
    assert hook.returncode == 0, hook.stdout + hook.stderr
    baseline = (keyed_nested / ".secrets.baseline").read_bytes()
    assert (scan / ".secrets.baseline").read_bytes() == baseline, "the baseline unchanged"
    other_key = secret_scan(keyed_nested, scan, "other_key.json")
    assert other_key.returncode == 1, "the sha256 key's line alone is skipped"
    assert "Hex High Entropy String" in other_key.stdout, other_key.stdout
    stored_base64 = secret_scan(keyed_nested, scan, "binary.json")
    assert stored_base64.returncode == 1, "a body stored base64 is scanned"
    assert "Base64 High Entropy String" in stored_base64.stdout, stored_base64.stdout


def test_the_reference_refresh_takes_cores_default_class_name(keyless_flat: Path) -> None:
    """#167: core's ``render_enums`` names an id list's class after its id field, a
    camelCase hump kept, ``unitId`` making ``UnitId``, so the rendered script, whose
    enums core's frame renders (sdk-core ADR-0051), keeps no class names of its own and
    passes none, ``Enumeration(class_name=...)`` among them."""
    script = ast.parse((keyless_flat / "scripts/refresh_reference.py").read_text())
    keywords = {
        keyword.arg
        for node in ast.walk(script)
        if isinstance(node, ast.Call)
        for keyword in node.keywords
    }
    assert not {"class_name", "class_names"} & keywords
    names = {node.id for node in ast.walk(script) if isinstance(node, ast.Name)}
    assert "class_names" not in names
