#!/usr/bin/env python3
"""
One-Click Isolated Burner Deployment & BscScan Open-Source Verification Script for AgentPulseGate.sol
=====================================================================================================
Safety & Key-Isolation Architecture:
1. Defaults to DRY-RUN mode (zero gas spent, zero mainnet broadcast unless `--broadcast` is explicitly passed).
2. Strict 3-Tier Cold/Hot Key Separation:
   - Cold/Main Personal Wallet (e.g. `redkoi.ai` `0x9556...6A7f`) is STRICTLY FORBIDDEN as `--verifier-signer` or deployer.
   - Burner Deployer Key (`DEPLOYER_PRIVATE_KEY` env var): ephemeral key funded with ~0.002 BNB solely for deployment.
   - Isolated Verifier Signer (`--verifier-signer` or `AGENT_PULSE_SIGNER_ADDRESS`): dedicated backend EIP-712 hot oracle address.
3. True One-Click Deploy + BscScan Verification:
   - Uses official Etherscan API V2 (`https://api.etherscan.io/v2/api?chainid=56&module=contract&action=verifysourcecode&apikey=...`)
     with canonical `constructorArguments` (no `0x` prefix) + async GUID status polling (`checkverifystatus`).
   - Automatically triggers verification after `--broadcast` when `BSCSCAN_API_KEY` or `ETHERSCAN_API_KEY` is provided.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from eth_abi.abi import encode
from eth_account import Account
from eth_utils.address import to_checksum_address
from eth_utils.crypto import keccak

ROOT_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
CONTRACT_SRC_PATH = ROOT_DIR / "contracts" / "AgentPulseGate.sol"
DEFAULT_RPC_URL = os.environ.get("BSC_RPC_URL", "https://bsc-dataseed.binance.org")
ETHERSCAN_V2_ENDPOINT = "https://api.etherscan.io/v2/api"
SPACE_ID_AI_REGISTRY = "0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F"

# Public demo signer address used ONLY for read-only dry-run gas estimation when no signer is configured
DRY_RUN_ESTIMATE_SIGNER = Account.from_key(
    "0x" + keccak(b"AgentPulse:ephemeral-local-preview-test-vector-v1").hex()
).address

# Explicitly blocked personal/cold vault addresses & public test keys that MUST NEVER be set as live verifierSigner
FORBIDDEN_LIVE_SIGNERS = {
    "0x95562a6e632c2b48d4788063e0e960afaee76a7f",  # Cold/hot wallet separation guard (never reuse personal EOA)
    "0x2c7536e3605d9c16a7a3d7b1898e529396a65c23",  # Legacy public test vector
    DRY_RUN_ESTIMATE_SIGNER.lower(),               # Ephemeral local preview vector
    "0x0000000000000000000000000000000000000000",
}


def rpc_call(rpc_url: str, method: str, params: list) -> dict:
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    req = urllib.request.Request(
        rpc_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "AgentPulseDeployer/1.1"},
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if "error" in data:
        raise RuntimeError(f"RPC {method} error: {data['error']}")
    return data


def resolve_verifier_signer(cli_signer: str, is_broadcast: bool) -> str:
    candidate = (cli_signer or os.environ.get("AGENT_PULSE_SIGNER_ADDRESS") or "").strip()
    if not candidate and os.environ.get("AGENT_PULSE_SIGNER_KEY"):
        candidate = Account.from_key(os.environ["AGENT_PULSE_SIGNER_KEY"].strip()).address

    if not candidate:
        if is_broadcast:
            raise ValueError(
                "Refusing --broadcast without an isolated --verifier-signer (or AGENT_PULSE_SIGNER_ADDRESS). "
                "Generate a dedicated hot oracle signer keypair first."
            )
        return DRY_RUN_ESTIMATE_SIGNER

    if not (candidate.startswith("0x") and len(candidate) == 42):
        raise ValueError(f"Invalid --verifier-signer address: {candidate}")

    if is_broadcast and candidate.lower() in FORBIDDEN_LIVE_SIGNERS:
        raise ValueError(
            f"Cold/Hot Isolation Guard: {candidate} is forbidden as live verifierSigner "
            "(never use personal main wallet 0x9556...6A7f or public demo key on production)."
        )

    return to_checksum_address(candidate)


def build_deploy_payload(
    verifier_signer: str,
    registry_override: str = "0x0000000000000000000000000000000000000000",
) -> tuple[str, str, dict]:
    bundle_path = ARTIFACTS_DIR / "AgentPulseGate.json"
    if not bundle_path.exists():
        raise FileNotFoundError(f"Missing compiled artifact {bundle_path}. Run compile_and_export.py first.")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    ctor_args_hex = encode(
        ["address", "address"],
        [to_checksum_address(verifier_signer), to_checksum_address(registry_override)],
    ).hex()
    full_deploy_data = bundle["bytecode"] + ctor_args_hex
    return full_deploy_data, ctor_args_hex, bundle


def submit_bscscan_verification(
    contract_address: str,
    ctor_args_hex: str,
    compiler_version: str,
    api_key: str,
) -> dict:
    """
    Submits Standard-JSON verification to Etherscan API V2 (BSC chainid=56).
    Query params: chainid, module, action, apikey.
    Body params : contractaddress, sourceCode, codeformat, contractname, compilerversion, constructorArguments, licenseType.
    """
    std_input_path = ARTIFACTS_DIR / "AgentPulseGate.standard_input.json"
    std_input_raw = std_input_path.read_text(encoding="utf-8")
    clean_ctor_hex = ctor_args_hex[2:] if ctor_args_hex.startswith("0x") else ctor_args_hex

    query_str = urllib.parse.urlencode(
        {
            "chainid": "56",
            "module": "contract",
            "action": "verifysourcecode",
            "apikey": api_key,
        }
    )
    url = f"{ETHERSCAN_V2_ENDPOINT}?{query_str}"

    form_data = urllib.parse.urlencode(
        {
            "contractaddress": to_checksum_address(contract_address),
            "sourceCode": std_input_raw,
            "codeformat": "solidity-standard-json-input",
            "contractname": "contracts/AgentPulseGate.sol:AgentPulseGate",
            "compilerversion": compiler_version,
            "constructorArguments": clean_ctor_hex,
            "licenseType": "3",  # MIT License
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=form_data,
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "AgentPulseDeployer/1.1"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def check_bscscan_verification_status(guid: str, api_key: str) -> dict:
    query_str = urllib.parse.urlencode(
        {
            "chainid": "56",
            "module": "contract",
            "action": "checkverifystatus",
            "guid": guid,
            "apikey": api_key,
        }
    )
    req = urllib.request.Request(
        f"{ETHERSCAN_V2_ENDPOINT}?{query_str}",
        headers={"User-Agent": "AgentPulseDeployer/1.1"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_verification_workflow(
    contract_address: str,
    ctor_args_hex: str,
    compiler_version: str,
    api_key: str,
    poll_attempts: int = 6,
    poll_interval_sec: float = 4.0,
) -> dict:
    submit_res = submit_bscscan_verification(
        contract_address=contract_address,
        ctor_args_hex=ctor_args_hex,
        compiler_version=compiler_version,
        api_key=api_key,
    )
    result_info: dict = {"submit": submit_res}
    if str(submit_res.get("status")) != "1":
        return result_info

    guid = str(submit_res.get("result") or "").strip()
    result_info["guid"] = guid
    for _ in range(poll_attempts):
        time.sleep(poll_interval_sec)
        status_res = check_bscscan_verification_status(guid=guid, api_key=api_key)
        result_info["statusCheck"] = status_res
        msg = str(status_res.get("result") or "").lower()
        if "pending" not in msg:
            break
    return result_info


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deploy & Verify AgentPulseGate on BNB Smart Chain (ChainID 56)")
    parser.add_argument(
        "--verifier-signer",
        type=str,
        default="",
        help="Dedicated isolated EIP-712 verifier signer address (must NOT be personal cold/main wallet)",
    )
    parser.add_argument("--rpc-url", type=str, default=DEFAULT_RPC_URL, help="BSC JSON-RPC endpoint")
    parser.add_argument(
        "--broadcast",
        action="store_true",
        help="Broadcast signed deployment tx to BSC Mainnet (omitted = safe dry-run estimation only)",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip automatic BscScan open-source verification after --broadcast",
    )
    parser.add_argument("--verify-address", type=str, default="", help="Verify an already deployed contract on BscScan")
    args = parser.parse_args(argv)

    is_live_mode = bool(args.broadcast or args.verify_address)
    try:
        verifier_signer = resolve_verifier_signer(args.verifier_signer, is_broadcast=is_live_mode)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    deploy_data, ctor_args_hex, bundle = build_deploy_payload(verifier_signer)
    api_key = (os.environ.get("BSCSCAN_API_KEY") or os.environ.get("ETHERSCAN_API_KEY") or "").strip()

    if args.verify_address:
        if not api_key:
            print("ERROR: Set BSCSCAN_API_KEY or ETHERSCAN_API_KEY before running --verify-address", file=sys.stderr)
            return 1
        ver_out = run_verification_workflow(
            contract_address=args.verify_address,
            ctor_args_hex=ctor_args_hex,
            compiler_version=bundle["compilerVersion"],
            api_key=api_key,
        )
        print(json.dumps(ver_out, indent=2))
        return 0 if str(ver_out.get("submit", {}).get("status")) == "1" else 1

    if args.broadcast:
        priv_key = os.environ.get("DEPLOYER_PRIVATE_KEY", "").strip()
        if not priv_key:
            print("ERROR: --broadcast requires isolated burner DEPLOYER_PRIVATE_KEY env variable.", file=sys.stderr)
            return 1
        deployer_acct = Account.from_key(priv_key)
        if deployer_acct.address.lower() in FORBIDDEN_LIVE_SIGNERS:
            print("ERROR: DEPLOYER_PRIVATE_KEY must be an isolated burner wallet, not a personal main wallet.", file=sys.stderr)
            return 1
        if deployer_acct.address.lower() == verifier_signer.lower():
            print("ERROR: DEPLOYER_PRIVATE_KEY and --verifier-signer must be separate isolated keys.", file=sys.stderr)
            return 1
    else:
        deployer_acct = None

    # Read-only gas estimation on live BSC RPC
    chain_id = int(rpc_call(args.rpc_url, "eth_chainId", [])["result"], 16)
    gas_price = int(rpc_call(args.rpc_url, "eth_gasPrice", [])["result"], 16)
    est_from = deployer_acct.address if deployer_acct else verifier_signer
    est_gas = int(
        rpc_call(
            args.rpc_url,
            "eth_estimateGas",
            [{"from": est_from, "data": deploy_data}],
        )["result"],
        16,
    )
    est_cost_bnb = (est_gas * gas_price) / 1e18

    summary: dict = {
        "mode": "LIVE_BROADCAST" if args.broadcast else "DRY_RUN_READONLY",
        "chainId": chain_id,
        "compilerVersion": bundle["compilerVersion"],
        "evmVersion": bundle["evmVersion"],
        "verifierSigner": verifier_signer,
        "isDryRunPlaceholderSigner": (not args.broadcast and verifier_signer == DRY_RUN_ESTIMATE_SIGNER),
        "spaceIdRegistry": SPACE_ID_AI_REGISTRY,
        "constructorArgsHex": ctor_args_hex,
        "estimatedGas": est_gas,
        "gasPriceGwei": round(gas_price / 1e9, 4),
        "estimatedDeployCostBNB": round(est_cost_bnb, 8),
    }

    if not args.broadcast or deployer_acct is None:
        print(json.dumps(summary, indent=2))
        return 0

    nonce = int(rpc_call(args.rpc_url, "eth_getTransactionCount", [deployer_acct.address, "pending"])["result"], 16)
    tx = {
        "chainId": chain_id,
        "nonce": nonce,
        "gas": int(est_gas * 1.15),
        "gasPrice": gas_price,
        "data": deploy_data,
        "value": 0,
    }
    signed = deployer_acct.sign_transaction(tx)
    raw_hex = "0x" + signed.raw_transaction.hex()
    tx_hash = rpc_call(args.rpc_url, "eth_sendRawTransaction", [raw_hex])["result"]
    summary["deployer"] = deployer_acct.address
    summary["txHash"] = tx_hash

    contract_addr = ""
    tx_status = 0
    for _ in range(30):
        time.sleep(2)
        receipt = rpc_call(args.rpc_url, "eth_getTransactionReceipt", [tx_hash]).get("result")
        if receipt:
            contract_addr = receipt.get("contractAddress") or ""
            tx_status = int(receipt.get("status", "0x0"), 16)
            summary["contractAddress"] = contract_addr
            summary["status"] = tx_status
            break

    if contract_addr and tx_status == 1 and api_key and not args.skip_verify:
        # Wait briefly for BscScan indexer to index newly mined contract bytecode before verification
        time.sleep(8)
        summary["verification"] = run_verification_workflow(
            contract_address=contract_addr,
            ctor_args_hex=ctor_args_hex,
            compiler_version=bundle["compilerVersion"],
            api_key=api_key,
        )
    elif contract_addr and tx_status == 1 and not api_key and not args.skip_verify:
        summary["verification"] = {
            "skipped": True,
            "reason": "BSCSCAN_API_KEY / ETHERSCAN_API_KEY not set; re-run with --verify-address once set.",
        }

    out_file = ARTIFACTS_DIR / "deployment_mainnet.json"
    out_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if tx_status == 1 else 1


if __name__ == "__main__":
    sys.exit(main())
