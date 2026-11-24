#!/usr/bin/env python3
"""
Compile AgentPulseGate.sol using local solc 0.8.24 and export:
- artifacts/AgentPulseGate.abi.json
- artifacts/AgentPulseGate.bin
- artifacts/AgentPulseGate.standard_input.json (for 1-click BscScan open-source verification)
- artifacts/AgentPulseGate.json (combined metadata + ABI + bytecode + selectors)
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
CONTRACT_PATH = ROOT_DIR / "contracts" / "AgentPulseGate.sol"
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
NODE_BIN = shutil.which("node") or "node"


def compile_contract() -> dict:
    source_code = CONTRACT_PATH.read_text(encoding="utf-8")
    standard_input = {
        "language": "Solidity",
        "sources": {
            "contracts/AgentPulseGate.sol": {
                "content": source_code,
            }
        },
        "settings": {
            "optimizer": {
                "enabled": True,
                "runs": 200,
            },
            "evmVersion": "paris",
            "outputSelection": {
                "*": {
                    "*": [
                        "abi",
                        "evm.bytecode.object",
                        "evm.deployedBytecode.object",
                        "evm.methodIdentifiers",
                        "metadata",
                    ]
                }
            },
        },
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    std_in_path = ARTIFACTS_DIR / "AgentPulseGate.standard_input.json"
    std_in_path.write_text(json.dumps(standard_input, indent=2), encoding="utf-8")

    js_runner = (
        "const fs = require('fs');"
        f"const solc = require('{ROOT_DIR.as_posix()}/node_modules/solc');"
        f"const input = fs.readFileSync('{std_in_path.as_posix()}', 'utf8');"
        "const output = JSON.parse(solc.compile(input));"
        "process.stdout.write(JSON.stringify({version: solc.version(), output}));"
    )
    proc = subprocess.run(
        [NODE_BIN, "-e", js_runner],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(proc.stdout)
    solc_version = payload["version"]
    output = payload["output"]

    errors = output.get("errors", [])
    fatal = [e for e in errors if e.get("severity") == "error"]
    if fatal:
        for err in fatal:
            sys.stderr.write(err.get("formattedMessage", str(err)) + "\n")
        raise RuntimeError("Solidity compilation failed")

    contract_data = output["contracts"]["contracts/AgentPulseGate.sol"]["AgentPulseGate"]
    abi = contract_data["abi"]
    bytecode = "0x" + contract_data["evm"]["bytecode"]["object"]
    deployed_bytecode = "0x" + contract_data["evm"]["deployedBytecode"]["object"]
    method_identifiers = contract_data["evm"]["methodIdentifiers"]

    (ARTIFACTS_DIR / "AgentPulseGate.abi.json").write_text(
        json.dumps(abi, indent=2), encoding="utf-8"
    )
    (ARTIFACTS_DIR / "AgentPulseGate.bin").write_text(bytecode, encoding="utf-8")

    bundle = {
        "contractName": "AgentPulseGate",
        "sourceName": "contracts/AgentPulseGate.sol",
        "compilerVersion": f"v{solc_version.split('+commit.')[0]}+commit.{solc_version.split('+commit.')[1].split('.')[0]}",
        "rawSolcVersion": solc_version,
        "evmVersion": "paris",
        "optimizer": {"enabled": True, "runs": 200},
        "abi": abi,
        "bytecode": bytecode,
        "deployedBytecode": deployed_bytecode,
        "bytecodeSizeBytes": (len(bytecode) - 2) // 2,
        "deployedSizeBytes": (len(deployed_bytecode) - 2) // 2,
        "methodIdentifiers": method_identifiers,
    }
    (ARTIFACTS_DIR / "AgentPulseGate.json").write_text(
        json.dumps(bundle, indent=2), encoding="utf-8"
    )
    return bundle


if __name__ == "__main__":
    info = compile_contract()
    print(f"Compiled {info['contractName']} successfully with {info['compilerVersion']} (evm={info['evmVersion']})")
    print(f"Bytecode size: {info['bytecodeSizeBytes']} bytes | Deployed: {info['deployedSizeBytes']} bytes")
