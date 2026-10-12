"""Export the actual code diff and reproducible file digests without touching git."""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/review/evidence"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def main():
    paths = {p.decode() for p in git("diff", "HEAD", "--name-only", "-z").split(b"\0") if p}
    paths.update(p.decode() for p in git("ls-files", "--others", "--exclude-standard", "-z").split(b"\0") if p)
    # Evidence/reports change as validation finishes; code identity excludes them.
    paths = sorted(p for p in paths if not p.startswith("docs/review/"))
    entries = []
    for relative in paths:
        path = ROOT / relative
        entries.append({"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None})
    digest = hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    OUT.mkdir(parents=True, exist_ok=True)
    tracked_paths = set(git("ls-files", "-z").split(b"\0"))
    tracked = [p for p in paths if p.encode() in tracked_paths]
    patch = git("diff", "--binary", "HEAD", "--", *tracked)
    for relative in sorted(set(paths) - set(tracked)):
        result = subprocess.run(["git", "diff", "--no-index", "--binary", "--", "/dev/null", relative],
                                cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if result.returncode not in (0, 1):
            raise RuntimeError(result.stderr.decode())
        patch += result.stdout
    (OUT / "code-changes.patch").write_bytes(patch)
    manifest = {"base_commit": git("rev-parse", "HEAD").decode().strip(),
                "branch": git("branch", "--show-current").decode().strip(),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "delivery": "actual uncommitted worktree and portable code patch; no remote push",
                "code_sha256": digest, "code_file_count": len(entries), "files": entries,
                "patch_sha256": hashlib.sha256(patch).hexdigest(),
                "excluded": "docs/review reports/evidence, ignored runtime data and credentials"}
    (OUT / "source-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"code_sha256": digest, "code_file_count": len(entries), "evidence": str(OUT.relative_to(ROOT))}))


if __name__ == "__main__":
    main()
