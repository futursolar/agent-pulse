#!/usr/bin/env python3
"""
AgentPulse Lightweight Read-Only API & Static SPA Server
========================================================
- Zero external web framework dependencies (uses standard library ThreadingHTTPServer).
- Does NOT touch production reverse proxies or any running tunnels.
- Endpoints:
  * GET /                                -> Serves SPA (index.html)
  * GET /api/health                      -> Service & contract status
  * GET /api/check?target=...            -> Live 4D deterministic liveness audit + EIP-712 signed payload
  * GET /api/samples                     -> Pre-calibrated live BSC .ai benchmark leaderboard
  * GET /calibration_benchmark_12.json   -> Static benchmark JSON (shared with GitHub Pages serverless mode)
  * GET /api/contract                    -> AgentPulseGate ABI, selectors & contract metadata
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"
HACKATHON_ROOT = WEB_DIR.parent

for _cand_dir in (HACKATHON_ROOT / "src", HACKATHON_ROOT.parent.parent / "scripts"):
    if _cand_dir.is_dir() and str(_cand_dir) not in sys.path:
        sys.path.insert(0, str(_cand_dir))

from agent_liveness_scorer import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    DEFAULT_VERIFYING_CONTRACT,
    SPACE_ID_AI_REGISTRY,
    AgentLivenessScorer,
)

SCORER = AgentLivenessScorer()


def _load_json_safe(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


class AgentPulseHandler(BaseHTTPRequestHandler):
    server_version = "AgentPulseHTTP/1.1"

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        sys.stderr.write(f"[AgentPulseWeb] {self.address_string()} - {format % args}\n")

    def _send_json(self, payload: dict | list, status: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _serve_static(self, rel_path: str) -> None:
        clean = rel_path.lstrip("/") or "index.html"
        static_root = STATIC_DIR.resolve()
        try:
            target_file = (static_root / clean).resolve()
        except Exception:
            self._send_json({"ok": False, "error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return
        if not target_file.is_relative_to(static_root) or not target_file.is_file():
            self._send_json({"ok": False, "error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return
        ctype, _ = mimetypes.guess_type(str(target_file))
        data = target_file.read_bytes()
        is_text = (ctype or "").startswith(("text/", "application/javascript", "application/json", "image/svg"))
        self.send_response(HTTPStatus.OK)
        self.send_header(
            "Content-Type",
            f"{ctype or 'application/octet-stream'}; charset=utf-8" if is_text else (ctype or "application/octet-stream"),
        )
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        route = parsed.path

        if route == "/api/health":
            artifact = _load_json_safe(HACKATHON_ROOT / "artifacts" / "AgentPulseGate.json", {})
            self._send_json(
                {
                    "ok": True,
                    "service": "AgentPulse (Proof-of-Live-Agent)",
                    "chainId": 56,
                    "spaceIdRegistry": SPACE_ID_AI_REGISTRY,
                    "verifyingContract": os.environ.get("AGENT_PULSE_CONTRACT", DEFAULT_VERIFYING_CONTRACT),
                    "compilerVersion": artifact.get("compilerVersion", "v0.8.24+commit.e11b9ed9"),
                }
            )
            return

        if route == "/api/check":
            qs = urllib.parse.parse_qs(parsed.query)
            target = (qs.get("target") or [""])[0].strip()
            refresh_raw = (qs.get("refresh") or [""])[0].strip().lower()
            force_refresh = refresh_raw in ("1", "true", "yes")
            if not target:
                self._send_json(
                    {"ok": False, "error": "Missing `target` query parameter (e.g. redkoi.ai or 0x...)"},
                    status=400,
                )
                return
            try:
                res = SCORER.evaluate(target, use_cache=not force_refresh)
                self._send_json(res, status=200)
            except ValueError as ve:
                self._send_json({"ok": False, "error": str(ve)}, status=404)
            except Exception as exc:
                self._send_json({"ok": False, "error": f"Upstream RPC/Indexer error: {exc}"}, status=502)
            return

        if route == "/api/samples":
            bench = _load_json_safe(HACKATHON_ROOT / "calibration_benchmark_12.json", [])
            self._send_json({"ok": True, "count": len(bench), "samples": bench})
            return

        if route == "/calibration_benchmark_12.json":
            bench = _load_json_safe(HACKATHON_ROOT / "calibration_benchmark_12.json", [])
            self._send_json(bench)
            return

        if route == "/api/contract":
            artifact = _load_json_safe(HACKATHON_ROOT / "artifacts" / "AgentPulseGate.json", {})
            self._send_json(
                {
                    "ok": True,
                    "contractName": "AgentPulseGate",
                    "chainId": 56,
                    "verifyingContract": os.environ.get("AGENT_PULSE_CONTRACT", DEFAULT_VERIFYING_CONTRACT),
                    "spaceIdRegistry": SPACE_ID_AI_REGISTRY,
                    "compilerVersion": artifact.get("compilerVersion", ""),
                    "methodIdentifiers": artifact.get("methodIdentifiers", {}),
                    "abi": artifact.get("abi", []),
                }
            )
            return

        self._serve_static(route)


def create_server(host: str = "127.0.0.1", port: int = 18890) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), AgentPulseHandler)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AgentPulse Web SPA & Read-Only Liveness API")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Bind host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=18890, help="Bind port (default 18890)")
    args = parser.parse_args()

    srv = create_server(args.host, args.port)
    print(f"AgentPulse SPA & API listening on http://{args.host}:{args.port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
