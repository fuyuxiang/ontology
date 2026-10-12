"""Remove credentials from recorded evidence while retaining business IDs/results."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/review/evidence"
SENSITIVE = {"password", "client_secret", "secret_key", "access_key", "api_key", "apikey", "access_token", "refresh_token", "id_token", "authorization", "x-agent-key"}
JWT = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
AUTH_QUERY = re.compile(r"([?&](?:code|state|ticket|token|access_token|refresh_token|code_verifier)=)[^\s\"&]+", re.IGNORECASE)
AUTH_URL = re.compile(r"[^\s\"]*(?:/auth/|/sso/|/authorize|/callback)[^\s\"]*", re.IGNORECASE)


def clean_string(value):
    # Ontology scenario code and business ticket are legitimate result data.
    # Only authorization URLs carry the one-time values removed here.
    value = JWT.sub("[REDACTED_JWT]", value)
    return AUTH_URL.sub(lambda match: AUTH_QUERY.sub(r"\1[REDACTED]", match.group()), value)


def clean_json(value):
    if isinstance(value, dict):
        return {key: "[REDACTED]" if key.lower().split(".")[-1] in SENSITIVE and isinstance(item, str) and item and "****" not in item and "••••" not in item
                else clean_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean_json(item) for item in value]
    return clean_string(value) if isinstance(value, str) else value


def main():
    changed, checked = [], 0
    # Source manifests and portable code are immutable code artifacts, not
    # recorded requests. Synthetic protocol credentials in test source are
    # intentional fixtures and must not make the patch cease to match source.
    excluded = {"source-manifest.json", "code-changes.patch", "core-findings-code.json"}
    for path in sorted(OUT.rglob("*")):
        if not path.is_file() or path.suffix not in {".json", ".txt", ".log", ".md"} or path.name in excluded:
            continue
        before = path.read_text()
        checked += 1
        if path.suffix == ".json":
            original = json.loads(before)
            cleaned = clean_json(original)
            after = json.dumps(cleaned, ensure_ascii=False, indent=2) + "\n" if cleaned != original else before
        else:
            after = clean_string(before)
        if after != before:
            path.write_text(after)
            changed.append(str(path.relative_to(OUT)))
    (OUT / "evidence-redaction.json").write_text(json.dumps({"status": "passed", "checked_text_files": checked,
        "redacted_files": changed, "policy": "recorded credential fields, JWTs and one-time authorization query values removed; business IDs and results retained"}, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"checked": checked, "redacted_files": len(changed)}))


if __name__ == "__main__":
    main()
