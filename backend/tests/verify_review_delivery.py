"""Apply the delivered patch to a clean baseline and verify every code digest."""
from __future__ import annotations

import hashlib
import io
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/review/evidence"


def main():
    manifest = json.loads((OUT / "source-manifest.json").read_text())
    patch = OUT / "code-changes.patch"
    assert hashlib.sha256(patch.read_bytes()).hexdigest() == manifest["patch_sha256"]
    current = []
    for entry in manifest["files"]:
        path = ROOT / entry["path"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        assert digest == entry["sha256"], entry["path"]
        current.append({"path": entry["path"], "sha256": digest})
    assert hashlib.sha256(json.dumps(current, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == manifest["code_sha256"]
    archive = subprocess.check_output(["git", "archive", "--format=tar", manifest["base_commit"]], cwd=ROOT)
    with tempfile.TemporaryDirectory(prefix="ontology-delivery-check-") as directory:
        dest = Path(directory)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            for member in tar.getmembers():
                assert (dest / member.name).resolve().is_relative_to(dest.resolve())
                assert not member.issym() and not member.islnk()
            tar.extractall(dest)
        commands = []
        for args in (["git", "apply", "--check", str(patch)], ["git", "apply", str(patch)]):
            result = subprocess.run(args, cwd=dest, capture_output=True, text=True)
            commands.append({"command": args[:3], "exit_code": result.returncode})
            assert result.returncode == 0, result.stderr
        for entry in current:
            path = dest / entry["path"]
            digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
            assert digest == entry["sha256"], entry["path"]
    evidence = {"status": "passed", "base_commit": manifest["base_commit"],
                "code_sha256": manifest["code_sha256"], "checked_files": len(current),
                "checks": ["worktree hashes equal manifest", "patch checksum matches", "patch applies to clean original commit", "patched code hashes equal actual worktree"],
                "commands": commands}
    (OUT / "delivery-verification.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(evidence, ensure_ascii=False))


if __name__ == "__main__":
    main()
