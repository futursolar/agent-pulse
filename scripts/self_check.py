#!/usr/bin/env python3
"""
scripts/self_check.py
=====================
Hard Pre-Publish Sanitization, Privacy & Compliance Gate for the public `agent-pulse` repository.

Checks enforced across EVERY tracked/working file in the repository:
1. Zero internal host paths, vault directories, private domains, or node hostnames.
2. Zero plaintext private keys, GitHub PATs, API tokens, or Bearer credentials.
3. Rule 193 Anti-Doxxing & EOA Isolation Guarantee:
   - `calibration_benchmark_12.json` and `docs/calibration_benchmark_12.json` contain ZERO unmasked 42-char `0x`
     wallet or funder addresses and carry `addressSha256` digests for owner-verified unlocking.
   - Scans EVERY 42-char `0x[0-9a-fA-F]{40}` token across ALL repository files (including `.py`, `.js`, `.md`, `.html`)
     against SHA-256 digests of calibrated `.ai` owner / personal cold wallets so zero personal EOAs leak in plaintext.
4. Static GitHub Pages Parity: `docs/{index.html,app.js,styles.css,calibration_benchmark_12.json}`
   match `web/static/` and root benchmark snapshot.
5. Deployment Receipt & Rule 183 / Rule 166 Disclosures:
   - `deployments/bsc_mainnet.json` preserves non-null `txHash`, `blockNumber`, and Sourcify `exact_match` (`matchId=59824360`).
   - `README.md` and `docs/index.html` disclose owner permissions (`setVerifierSigner`, `transferOwnership`,
     `ZeroValueOnly`) and official hashtags (`#BinanceWalletHackathon`, `#AgenticWallet`), authored by `RedKoi Research`.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Assembled dynamically so even `grep -rn` across the repo never hits literal internal tokens in this script
FORBIDDEN_SUBSTRINGS: tuple[str, ...] = (
    "/" + "home/" + "ubuntu",
    "/" + "root",
    "pi-" + "vault",
    "vault_" + "cipher",
    "redkoi." + "online",
    "host" + "sailor",
    "oracle-" + "arm",
    "oracle-" + "amd",
    "ghp" + "_",
    "github_" + "pat_",
    "sk-" + "proj-",
    "xoxb" + "-",
)

SECRET_REGEXES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "hex_private_key_assignment",
        re.compile(
            r"(?i)(?:priv(?:ate)?_?key|secret_?key|deployer_private_key|signer_key)\s*[:=]\s*['\"]?(?:0x)?[0-9a-f]{64}['\"]?"
        ),
    ),
    (
        "inline_url_basic_auth_token",
        re.compile(r"https?://[^\s/@]+:[^\s/@]{12,}@github\.com"),
    ),
)

FULL_EVM_ADDR_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
ANY_EVM_ADDR_WORD_RE = re.compile(r"\b0x[0-9a-fA-F]{40}\b")
PERSONAL_COLD_WALLET_SHA256 = "36657128fb10fcc13915b9688f4abeae0731ca2d4ac52095368fecb59d352cdf"
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache", ".ruff_cache"}


def iter_repo_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for p in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.is_file():
            out.append(p)
    return out


def check_files_for_leaks(files: list[Path], protected_addr_sha256: set[str]) -> list[str]:
    errors: list[str] = []
    for fpath in files:
        rel = fpath.relative_to(REPO_ROOT).as_posix()
        raw = fpath.read_bytes()
        text = raw.decode("utf-8", errors="ignore")
        lowered = text.lower()
        for bad in FORBIDDEN_SUBSTRINGS:
            if bad.lower() in lowered:
                errors.append(f"[FORBIDDEN_SUBSTRING] {rel} contains banned internal marker `{bad}`")
        for label, rx in SECRET_REGEXES:
            if rx.search(text):
                errors.append(f"[SECRET_PATTERN:{label}] {rel} matched sensitive credential pattern")
        for addr_match in ANY_EVM_ADDR_WORD_RE.findall(text):
            digest = hashlib.sha256(addr_match.lower().encode("ascii")).hexdigest()
            if digest in protected_addr_sha256:
                errors.append(
                    f"[RULE_193_PLAINTEXT_EOA_LEAK] {rel} exposes a privacy-protected .ai owner / personal EOA (`{addr_match[:6]}...{addr_match[-4:]}`)"
                )
    return errors


def check_git_remotes_clean() -> list[str]:
    errors: list[str] = []
    git_cfg = REPO_ROOT / ".git" / "config"
    if git_cfg.is_file():
        cfg_txt = git_cfg.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"https?://[^\s/@]+@github\.com", cfg_txt) or "extraheader" in cfg_txt.lower():
            errors.append("[GIT_CONFIG_CREDENTIAL_LEAK] .git/config contains embedded credentials or extraheader")
    return errors


def check_benchmark_privacy_masked(json_path: Path) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    sha_digests: set[str] = {PERSONAL_COLD_WALLET_SHA256}
    rel = json_path.relative_to(REPO_ROOT).as_posix()
    if not json_path.is_file():
        return [f"[MISSING_BENCHMARK] {rel} does not exist"], sha_digests
    records = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(records, list) or len(records) != 12:
        return [f"[INVALID_BENCHMARK] {rel} must contain 12 calibrated records"], sha_digests
    for idx, rec in enumerate(records):
        rec_sha = str(rec.get("addressSha256") or "").strip().lower()
        if len(rec_sha) != 64:
            errors.append(f"[MISSING_ADDRESS_SHA256] {rel}[{idx}] missing 64-hex addressSha256")
        else:
            sha_digests.add(rec_sha)
        for field_name in ("address", "addressLower"):
            val = str(rec.get(field_name) or "")
            if FULL_EVM_ADDR_RE.match(val):
                errors.append(f"[RULE_193_UNMASKED_WALLET] {rel}[{idx}].{field_name} exposes full 0x address")
        funder_val = str(rec.get("dimensions", {}).get("d1Funding", {}).get("funder") or "")
        if FULL_EVM_ADDR_RE.match(funder_val):
            errors.append(f"[RULE_193_UNMASKED_FUNDER] {rel}[{idx}].d1Funding.funder exposes full 0x address")
        payload_wallet = str(rec.get("eip712", {}).get("payload", {}).get("wallet") or "")
        if FULL_EVM_ADDR_RE.match(payload_wallet):
            errors.append(f"[RULE_193_UNMASKED_PAYLOAD] {rel}[{idx}].eip712.payload.wallet exposes full 0x address")
    return errors, sha_digests


def check_static_pages_parity() -> list[str]:
    errors: list[str] = []
    for asset in ("index.html", "app.js", "styles.css"):
        src = REPO_ROOT / "web" / "static" / asset
        dst = REPO_ROOT / "docs" / asset
        if not src.is_file() or not dst.is_file():
            errors.append(f"[MISSING_STATIC_ASSET] Missing {asset} in web/static or docs")
        elif src.read_bytes() != dst.read_bytes():
            errors.append(f"[STATIC_ASSET_DRIFT] docs/{asset} differs from web/static/{asset}")
    root_bench = REPO_ROOT / "calibration_benchmark_12.json"
    docs_bench = REPO_ROOT / "docs" / "calibration_benchmark_12.json"
    if not root_bench.is_file() or not docs_bench.is_file():
        errors.append("[MISSING_BENCHMARK_COPY] Missing calibration_benchmark_12.json in root or docs/")
    elif root_bench.read_bytes() != docs_bench.read_bytes():
        errors.append("[BENCHMARK_DRIFT] docs/calibration_benchmark_12.json differs from root copy")
    return errors


def check_deployment_and_compliance_disclosures() -> list[str]:
    errors: list[str] = []
    required_markers = (
        "setVerifierSigner",
        "transferOwnership",
        "ZeroValueOnly",
        "Privacy-Masked",
        "#BinanceWalletHackathon",
        "#AgenticWallet",
        "RedKoi Research",
    )
    readme_txt = (REPO_ROOT / "README.md").read_text(encoding="utf-8") if (REPO_ROOT / "README.md").is_file() else ""
    subkit_txt = (REPO_ROOT / "SUBMISSION_KIT.md").read_text(encoding="utf-8") if (REPO_ROOT / "SUBMISSION_KIT.md").is_file() else ""
    html_txt = (REPO_ROOT / "docs" / "index.html").read_text(encoding="utf-8") if (REPO_ROOT / "docs" / "index.html").is_file() else ""
    js_txt = (REPO_ROOT / "docs" / "app.js").read_text(encoding="utf-8") if (REPO_ROOT / "docs" / "app.js").is_file() else ""
    combined = readme_txt + "\n" + html_txt + "\n" + js_txt
    for marker in required_markers:
        if marker not in combined:
            errors.append(f"[MISSING_DISCLOSURE] Required compliance marker `{marker}` missing")
    for marker in ("setVerifierSigner", "transferOwnership", "ZeroValueOnly", "RedKoi Research", "59824360"):
        if marker not in readme_txt:
            errors.append(f"[README_DISCLOSURE] README.md missing `{marker}`")
    if "59824360" not in subkit_txt:
        errors.append("[SUBMISSION_KIT_DISCLOSURE] SUBMISSION_KIT.md missing Sourcify matchId `59824360`")

    dep_path = REPO_ROOT / "deployments" / "bsc_mainnet.json"
    if not dep_path.is_file():
        errors.append("[MISSING_DEPLOYMENT_MANIFEST] deployments/bsc_mainnet.json missing")
    else:
        dep = json.loads(dep_path.read_text(encoding="utf-8"))
        if dep.get("status") == "DEPLOYED_ON_BSC_MAINNET":
            if not dep.get("txHash") or not dep.get("blockNumber"):
                errors.append("[NULL_DEPLOYMENT_RECEIPT] deployments/bsc_mainnet.json has null txHash or blockNumber")
            sc = dep.get("sourcifyVerification") or {}
            if sc.get("match") != "exact_match" or str(sc.get("matchId")) != "59824360":
                errors.append("[MISSING_SOURCIFY_MANIFEST] deployments/bsc_mainnet.json missing Sourcify exact_match 59824360")
    return errors


def main() -> int:
    files = iter_repo_files(REPO_ROOT)
    errors: list[str] = []
    bench_errs_root, protected_sha_root = check_benchmark_privacy_masked(REPO_ROOT / "calibration_benchmark_12.json")
    bench_errs_docs, protected_sha_docs = check_benchmark_privacy_masked(REPO_ROOT / "docs" / "calibration_benchmark_12.json")
    protected_sha = protected_sha_root | protected_sha_docs

    errors.extend(bench_errs_root)
    errors.extend(bench_errs_docs)
    errors.extend(check_files_for_leaks(files, protected_sha))
    errors.extend(check_git_remotes_clean())
    errors.extend(check_static_pages_parity())
    errors.extend(check_deployment_and_compliance_disclosures())

    if errors:
        sys.stderr.write(f"SELF_CHECK FAILED ({len(errors)} violation(s)):\n")
        for err in errors:
            sys.stderr.write(f"  - {err}\n")
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "scannedFiles": len(files),
                "privacyMaskedBenchmarkRecords": 12,
                "protectedWalletDigestsChecked": len(protected_sha),
                "staticPagesParity": True,
                "gitConfigClean": True,
                "author": "RedKoi Research",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
