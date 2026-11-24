#!/usr/bin/env python3
"""
scripts/agent_liveness_scorer.py
================================
AgentPulse (Proof-of-Live-Agent) — 100% Deterministic, Zero-LLM 4D Anti-Sybil Liveness Engine for BSC .ai Agents.

Core Capabilities:
1. Dual-Source SPACE ID .ai Resolution:
   - Official BSC HandleRegistry `0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F`
     (`handleOf(address)` selector `0xc50a1514`, `ownerOfHandle(string)` selector `0x1da94fb4`)
   - Official SPACE ID Web3 Name API (`https://nameapi.space.id/getAddress?domain=<handle>.ai`)
2. 0..100 Deterministic 4-Dimensional Physical Anti-Sybil Model (Fail-Closed):
   - D1 Funding Provenance, 72h Capital Seasoning & Anti-Cluster/Relay Tree (0..30 pts)
   - D2 Multi-Day Temporal Maturity & Inter-Arrival Entropy (0..25 pts)
   - D3 Whitelisted Cross-Protocol Economic Friction & Seasoned Retention (0..30 pts)
   - D4 EIP-712 On-Chain Attestation Digest & .ai Identity Binding (0..15 pts)
3. Exact EIP-712 & Live Nonce (`0x7ecebe00`) Parity with `AgentPulseGate.sol`.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from eth_abi.abi import decode as abi_decode
from eth_abi.abi import encode as abi_encode
from eth_account import Account
from eth_utils.address import to_checksum_address
from eth_utils.crypto import keccak

# =============================================================================
# Constants & On-Chain Registry Addresses (BNB Smart Chain - ChainID 56)
# =============================================================================

BSC_CHAIN_ID = 56
SPACE_ID_AI_REGISTRY = "0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F"
SELECTOR_HANDLE_OF = "0xc50a1514"        # handleOf(address) -> string
SELECTOR_OWNER_OF_HANDLE = "0x1da94fb4"  # ownerOfHandle(string) -> address
SELECTOR_BALANCE_OF = "0x70a08231"       # balanceOf(address) -> uint256
SELECTOR_GET_RESERVES = "0x0902f1ac"     # PancakeSwap Pair getReserves()
SELECTOR_NONCES = "0x7ecebe00"           # nonces(address) -> uint256

SPACE_ID_NAMEAPI_BASE = "https://nameapi.space.id"
ETHERSCAN_V2_API_BASE = "https://api.etherscan.io/v2/api"

# Un-deployed deterministic placeholder prior to mainnet contract deployment
PLACEHOLDER_VERIFYING_CONTRACT = "0x00000000000000000000000000000000000056A1"
# Deterministic nonce=0 BSC Mainnet AgentPulseGate address (deployer 0x46C4732D496b4f4d10aA41BA4164d89fF1d3b54D)
MAINNET_VERIFYING_CONTRACT = "0x6cC807d492D8a10A16E5A7309d408801aaD025B5"
DEFAULT_VERIFYING_CONTRACT = os.environ.get(
    "AGENT_PULSE_CONTRACT",
    MAINNET_VERIFYING_CONTRACT,
)

# Deterministic ephemeral demo test vector ONLY used when AGENT_PULSE_SIGNER_KEY is not injected (local preview/tests)
_DEMO_SIGNER_PRIVKEY = "0x" + keccak(b"AgentPulse:ephemeral-local-preview-test-vector-v1").hex()

# Minimum seasoning window (72 hours) to defeat 15s flash-rotated capital pools & hot-money balls
CAPITAL_SEASONING_WINDOW_SEC = 72 * 3600

BSC_RPC_POOL: Tuple[str, ...] = (
    "https://bsc-dataseed.binance.org",
    "https://bsc-dataseed1.defibit.io",
    "https://bsc-dataseed1.ninicoin.io",
    "https://bsc-rpc.publicnode.com",
    "https://1rpc.io/bnb",
)

NODEREAL_INDEXER_POOL: Tuple[str, ...] = (
    "https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3",
    "https://bsc-mainnet.nodereal.io/v1/e9a36765eb8a40b9bd12e680a1fd2bc5",
)

# Core BSC Token Contracts (ALL verified 18 decimals on BSC) & Canonical PancakeSwap V2 WBNB/USDT Pair
BSC_USDT = "0x55d398326f99059ff775485246999027b3197955"
BSC_USDC = "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d"
BSC_FDUSD = "0xc5f0f7b66764f6ec8c8dff7ba683102295e16409"
BSC_USD1 = "0x8d0d000ee44948fc98c9b98a4fa4921476f08b0d"
BSC_DAI = "0x1af3f329e8be154074d8769d1ffa4ee058b1dbc3"
BSC_BUSD = "0xe9e7cea3dedca5984780bafc599bd69add087d56"
BSC_WBNB = "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"
PANCAKE_WBNB_USDT_PAIR = "0x16b9a82891338f9ba80e2d6970fdda79d1eb0dae"
FALLBACK_BNB_PRICE_USD = 565.0

for _addr_const in (
    SPACE_ID_AI_REGISTRY,
    PLACEHOLDER_VERIFYING_CONTRACT,
    BSC_USDT,
    BSC_USDC,
    BSC_FDUSD,
    BSC_USD1,
    BSC_DAI,
    BSC_BUSD,
    BSC_WBNB,
    PANCAKE_WBNB_USDT_PAIR,
):
    if not (_addr_const.startswith("0x") and len(_addr_const) == 42):
        raise ValueError(f"Invalid constant EVM address length: {_addr_const}")

# Strictly 1:1 with the 6 BSC 18-decimal stablecoins queried in `collect_raw_snapshot_bundle` / `WalletSnapshot`
STABLECOIN_SET: Set[str] = {
    BSC_USDT,
    BSC_USDC,
    BSC_FDUSD,
    BSC_USD1,
    BSC_DAI,
    BSC_BUSD,
}
HARD_LIQUID_TOKENS: Set[str] = STABLECOIN_SET | {BSC_WBNB}

# Minimum economic friction & 72h continuous capital lockup floors
MIN_NATIVE_BNB_FRICTION = 0.002
MIN_HARD_TOKEN_FRICTION_USD = 1.0
MIN_SEASONED_COMMITMENT_USD = 10.0
MIN_CANDIDATE_SEC_BNB = 0.0085
MIN_CANDIDATE_TOKEN_USD = 0.50
MAX_CANDIDATE_FUNDERS_PER_TYPE = 8

# Lending pools where instant supply+redeem roundtrips carry 0% protocol fee (Venus / Kinza)
LENDING_POOL_CONTRACTS: Set[str] = {
    "0xfd36e2c2a6789db23113685031d7f16329158384",  # Venus Comptroller
    "0xa07c5b74c9b40447a954e1466938b865b6bbea36",  # Venus vBNB
    "0xfd5840cd36d94d7229439859c0112a4185bc0255",  # Venus vUSDT
    "0xcb0620b181140e57d1c0d8b724cde623ca963c8c",  # Kinza Finance Pool
}
LENDING_REDEEM_SELECTORS: Set[str] = {
    "0xdb006a75",  # Compound/Venus redeem(uint256)
    "0x852a12e3",  # Compound/Venus redeemUnderlying(uint256)
    "0xc5ebeaec",  # Compound/Venus borrow(uint256)
    "0x69328dec",  # Aave/Kinza withdraw(address,uint256,address)
    "0xa415bcad",  # Aave/Kinza borrow(address,uint256,uint256,uint16,address)
    "0x2dad97d4",  # Aave/Kinza repayWithATokens(address,uint256,uint256)
    "0xede4edd0",  # Comptroller exitMarket(address)
    "0x2e1a7d4d",  # withdraw(uint256)
}
LENDING_BEHALF_SELECTORS: Set[str] = {
    "0x23323e03",  # Venus vToken.mintBehalf(address,uint256)
    "0xc2eae838",  # Venus vBNB.mintBehalf(address)
    "0x2608f818",  # Venus vToken.repayBorrowBehalf(address,uint256)
    "0xe5974619",  # Venus vBNB.repayBorrowBehalf(address)
}
VENUS_COMPTROLLER = "0xfd36e2c2a6789db23113685031d7f16329158384"

# Cross-chain bridge method allowlist & 0%-fee local LP deposit/redeem selectors (Stargate V1 + UniswapV2/PancakeV2 LP)
RELAY_DEPOSITORY_BSC = "0x4cd00e387622c35bddb9b4c962c136462338bc31"
STARGATE_ROUTER_BSC = "0x4a364f8c717caad9a442737eb7b8a55cc6cf18d8"
STARGATE_BRIDGE_SWAP_SELECTORS: Set[str] = {
    "0x9fbf10fc",  # Stargate V1 Router.swap(..., (uint256,uint256,bytes), bytes, bytes) [Verified BSC Bytecode]
    "0x46abb447",  # IStargateRouter.swap ABI variant
    "0x1114cd2a",  # Stargate RouterETH.swapETH
}
# ApolloX / Aster V2 Trading Diamond (`0x1b6f2d3844c6ae7d56ceb3c3643b9060ba28feb0`) method isolation:
# ONLY executed market-order entries (`openMarketTrade` / `openMarketTradeBNB` on `TradingPortalFacet`) charge an
# immediate opening fee; `LimitOrderFacet` (`openLimitOrder` / `openLimitOrderBNB` / `cancelLimitOrder`) and ALP/Stake
# facets carry 0% cancellation fee and 100% refundable local margin!
APX_V2_TRADING_DIAMOND = "0x1b6f2d3844c6ae7d56ceb3c3643b9060ba28feb0"
APX_V2_MARKET_TRADE_SELECTORS: Set[str] = {
    "0x703085c7",  # TradingPortalFacet.openMarketTrade((address,bool,address,uint96,uint80,uint64,uint64,uint64,uint24)) [Verified BSC Facet]
    "0xb7aeae66",  # TradingPortalFacet.openMarketTradeBNB((address,bool,address,uint96,uint80,uint64,uint64,uint64,uint24)) [Verified BSC Facet]
    "0x90a8e114",  # openMarketTrade uint256 tuple ABI alias
    "0x9c1da3c6",  # openMarketTradeBNB uint256 tuple ABI alias
}
APX_V2_ZERO_FEE_ESCROW_ADD_SELECTORS: Set[str] = {
    "0x0390a929",  # LimitOrderFacet.openLimitOrder(...) — 0% cancel fee [Verified BSC Facet]
    "0x02725c1c",  # LimitOrderFacet.openLimitOrderBNB(...) — 0% cancel fee [Verified BSC Facet]
    "0x29d9ddce",  # TradingPortalFacet.addMargin(bytes32,uint96) [Verified BSC Facet]
    "0x184cf4ee",  # addMarginBNB(bytes32)
    "0xc375f765",  # AlpManagerFacet.mintAlp(address,uint256,uint256,bool) [Verified BSC Facet]
    "0x08cdd3a3",  # AlpManagerFacet.mintAlpBNB(uint256,bool) [Verified BSC Facet]
    "0xa694fc3a",  # StakeFacet.stake(uint256) [Verified BSC Facet]
}
APX_V2_EXIT_OR_ADMIN_SELECTORS: Set[str] = {
    "0x4584eff6",  # LimitOrderFacet.cancelLimitOrder(bytes32) — 0% fee 100% refund [Verified BSC Facet]
    "0x5177fd3b",  # TradingPortalFacet.closeTrade(bytes32) [Verified BSC Facet]
    "0x48276b6f",  # AlpManagerFacet.burnAlp(...) [Verified BSC Facet]
    "0x63810c0d",  # AlpManagerFacet.burnAlpBNB(...) [Verified BSC Facet]
    "0x2e17de78",  # unstake(uint256)
    "0x1bf31c47",  # updateTradeTpAndSl
    "0xc7bf7464",  # updateTradeSl
    "0xe016f83f",  # updateTradeTp
    "0x9420c452",  # LimitOrderFacet update
    "0x96289683",  # LimitOrderFacet update
    "0x0638d9c4",  # LimitOrderFacet update
}
ZERO_FEE_LP_ADD_SELECTORS: Set[str] = {
    "0x87b21efc",  # Stargate Router.addLiquidity(uint256,uint256,address) [Verified BSC Bytecode]
    "0x6d40be95",  # Stargate addLiquidity doc alias
    "0xe8e33700",  # UniswapV2/PancakeV2 addLiquidity
    "0xf305d719",  # UniswapV2/PancakeV2 addLiquidityETH
}
ZERO_FEE_LP_REDEEM_SELECTORS: Set[str] = {
    "0xc4de93a5",  # Stargate Router.instantRedeemLocal(uint16,uint256,address) [Verified BSC Bytecode]
    "0x2b814df3",  # Stargate instantRedeemLocal doc alias
    "0x8f2e1d18",  # Stargate Router.redeemLocal(...) [Verified BSC Bytecode]
    "0xbe97303f",  # Stargate redeemLocal doc alias
    "0x84d0dba3",  # Stargate Router.redeemRemote(...) [Live BSC Bytecode]
    "0x6273abdd",  # Stargate redeemRemote doc alias
    "0x9ba3aa74",  # Stargate Router.sendCredits(...) [Live BSC Bytecode]
    "0xbaa2abde",  # UniswapV2/PancakeV2 removeLiquidity
    "0x02751cec",  # UniswapV2/PancakeV2 removeLiquidityETH
    "0x2195995c",  # UniswapV2/PancakeV2 removeLiquidityWithPermit
    "0xded9382a",  # UniswapV2/PancakeV2 removeLiquidityETHWithPermit
    "0xaf2979eb",  # UniswapV2/PancakeV2 removeLiquidityETHSupportingFeeOnTransferTokens
    "0x5b0d5984",  # UniswapV2/PancakeV2 removeLiquidityETHWithPermitSupportingFeeOnTransferTokens
}

# Router batch / command-VM selectors & contracts capable of bundling a third-party `recipient` / `PAY_PORTION`
# drain alongside a 1-wei self-beneficiary non-hard token swap in the same `tx_hash`.
DEX_BATCH_SPLIT_SELECTORS: Set[str] = {
    "0xac9650d8",  # SmartRouter / SwapRouter02 multicall(bytes[])
    "0x5ae401dc",  # SmartRouter multicall(uint256,bytes[])
    "0x1f0464d1",  # SwapRouter02 multicall(bytes32,bytes[])
    "0x3593564c",  # UniversalRouter execute(bytes,bytes[],uint256)
    "0x24856bc3",  # UniversalRouter execute(bytes,bytes[])
}
DEX_COMMAND_VM_ROUTERS: Set[str] = {
    "0x1a0a18ac4becddbd6389559687d1a73d8927e416",  # PancakeSwap Universal Router
    "0xd9c500dff816a1da21a48a732d3498bf09dc9aeb",  # PancakeSwap Universal Router V2
    "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad",  # Uniswap Universal Router
}
# Official Predict.fun & Cross-Chain Bridge Contracts on BNB Smart Chain (Verified via BscScan & Official Docs)
PREDICT_FUN_EXCHANGES: Set[str] = {
    "0x8bc070bedab741406f4b1eb65a72bee27894b689",  # Predict.fun CTFExchange (Standard)
    "0x6beb5a40c032afc305961162d8204cda16decfa5",  # Predict.fun YieldBearing CTFExchange
    "0x8a289d458f5a134ba40015085a8f50ffb681b41d",  # Predict.fun NegRisk CTFExchange
}

# Known Batch Disperse / Multisender Contracts & Selectors on BSC
BATCH_DISPERSE_CONTRACTS: Set[str] = {
    "0xd152f549545093347a162dce210e7293f1452150",  # Disperse.app
    "0x2c95d751da37a5c1d9c5a7fd465c1d50f3d96160",  # CoinTool Multisender
    "0xa5025faba6e70b84f74e9b1113e5f7f4e7f4859f",  # Multisend.org
}
BATCH_DISPERSE_SELECTORS: Set[str] = {
    "0xc73a2d60",  # disperseEther(address[],uint256[])
    "0xd73dd623",  # disperseToken / batch variants
    "0xe6930a22",  # multisendEther
    "0xc37bc3a8",  # batch airdrop disperse
    "0x5be6950f",  # multiTransfer
}

# Verified Mainstream BSC CEX Withdrawal Hot Wallets & Dynamic High-Nonce Threshold
# Note: At 2026 BSC 0.05 gwei floor, 5,000 self-txs costs only ~2.94 USD; raising unlisted floor to 50,000
# (~29.4 USD + >10h continuous sequential block inclusion) AND enforcing zero bidirectional spoke overlap,
# zero self-tx stuffing, >=12 unique recipients, and >=10x multi-magnitude dispersion crushes fake-CEX hubs.
CEX_HOT_WALLET_MIN_NONCE = 50_000
KNOWN_BSC_CEX_HOT_WALLETS: Set[str] = {
    "0xf977814e90da44bfa03b6295a0616a897441acec",  # Binance: Hot Wallet 20
    "0xbe0eb53f46cd790cd13851d5eff43d12404d33e8",  # Binance 7
    "0x8894e0a0c962cb723c1976a4421c95949be2d4e3",  # Binance: Hot Wallet 6
    "0xeb2d2f1b8c558a40207669291fda468e50c8a0bb",  # Binance: Hot Wallet 10
    "0x28c6c06298d514db089934071355e5743bf21d60",  # Binance: Hot Wallet 14
    "0xa180fe01b906a1be37be6c534a3300785b20d947",  # Binance: Hot Wallet 16
    "0x29bdfbf7d27462a2d115748ace2bd71a2646946c",  # Binance: Hot Wallet 17
    "0x73f5ebe90f27b46ea12e5795d16c4b408b19cc6f",  # Binance: Hot Wallet 18
    "0x1fbe2acee135d991592f167ac371f3dd893a508b",  # Binance: Hot Wallet 19
    "0x01c952174c24e1210d26961d456a77a39e1f0bb0",  # Binance: Hot Wallet 23
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d",  # Binance 16
    "0x5a52e96bacdabb82fd05763e25335261b270efcb",  # Binance 28
    "0x835678a611b28684005a5e2233695fb6cbbb0007",  # Binance 70
    "0xd3a22590f8243f8e83ac230d1842c9af0404c4a1",  # Ceffu Custody Hot Wallet
    "0xf89d7b9c864f589bbf53a82105107622b35eaa40",  # Bybit: Hot Wallet
    "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b",  # OKX Hot Wallet
    "0x0d0707963952f2fba59dd06f2b425ace40b492fe",  # Gate.io 1
    "0x1c4b70a3968436b9a0a9cf5205c787eb81bb558c",  # Gate.io 3
}
for _cex_addr in KNOWN_BSC_CEX_HOT_WALLETS:
    if not (_cex_addr.startswith("0x") and len(_cex_addr) == 42):
        raise ValueError(f"Invalid CEX hot wallet address length: {_cex_addr}")

# Selectors that NEVER represent real DeFi protocol economic friction (approvals, 1:1 WBNB wrap/unwrap, raw transfers, check-ins)
ZERO_FRICTION_SELECTORS: Set[str] = {
    "0x095ea7b3",  # approve(address,uint256)
    "0xa22cb465",  # setApprovalForAll(address,bool)
    "0xd505accf",  # permit(...)
    "0x39509351",  # increaseAllowance
    "0xa457c2d7",  # decreaseAllowance
    "0xd0e30db0",  # WBNB.deposit() — 1:1 self-wrap, zero protocol fee
    "0x2e1a7d4d",  # WBNB.withdraw(uint256) — 1:1 self-unwrap, zero protocol fee
    "0xa9059cbb",  # ERC20.transfer(address,uint256) — peer transfer, not protocol friction
    "0x23b872dd",  # ERC20.transferFrom(address,address,uint256)
    "0x183ff085",  # daily checkIn()
    "0x912d97fc",  # gm() / sign-in
    "0x8cb5772c",  # zero-value daily mint / check-in
    "0x8580974c",  # SPACE ID .ai registration mint itself (identity mint != DeFi economic friction)
    "0x72ce4275",  # Gnosis ConditionalTokens.splitPosition — 1:1 collateral split, zero protocol fee
    "0x9e7212ad",  # Gnosis ConditionalTokens.mergePositions — 1:1 collateral merge, zero protocol fee
    "0xf242432a",  # ERC1155.safeTransferFrom — peer transfer, not protocol friction
    "0x2eb2c2d6",  # ERC1155.safeBatchTransferFrom — peer transfer, not protocol friction
}

# Strictly Curated BSC Real-Economy Protocol Directory (Address lowercase -> Category)
# Security Invariant: Unverified / custom user-deployed contracts CANNOT spoof 4-byte selectors to farm D3 friction!
KNOWN_BSC_PROTOCOLS: Dict[str, str] = {
    # DEX & Aggregators & Launchpads (Verified non-zero BSC Mainnet bytecode)
    "0x10ed43c718714eb63d5aa57b78b54704e256024e": "DEX_SWAP",  # PancakeSwap V2 Router
    "0x13f4ea83d0bd40e75c8222255bc855a974568dd4": "DEX_SWAP",  # PancakeSwap V3 SmartRouter
    "0x1a0a18ac4becddbd6389559687d1a73d8927e416": "DEX_SWAP",  # PancakeSwap Universal Router
    "0xd9c500dff816a1da21a48a732d3498bf09dc9aeb": "DEX_SWAP",  # PancakeSwap Universal Router V2
    "0xb300000b72deaeb607a12d5f54773d1c19c7028d": "DEX_SWAP",  # KyberSwap MetaAggregationRouterV2
    "0x6131b5fae19ea4f9d964eac0408e4408b66337b5": "DEX_SWAP",  # KyberSwap Router
    "0x1111111254eeb25477b68fb85ed929f73a960582": "DEX_SWAP",  # 1inch V5 Router
    "0x111111125421ca6dc452d289314280a0f8842a65": "DEX_SWAP",  # 1inch V6 Router
    "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad": "DEX_SWAP",  # Uniswap Universal Router
    "0xb971ef87ede563556b2ed4b1c0b0019111dd85d2": "DEX_SWAP",  # Uniswap V3 SwapRouter02
    "0xd4ae6eca985340dd434d38f470accce4dc78d109": "DEX_SWAP",  # THENA V1 Router
    "0x6352a56caadc4f1e25cd6c75970fa768a3304e64": "DEX_SWAP",  # OpenOcean Exchange V2
    "0x6a000f20005980200259b80c5102003040001068": "DEX_SWAP",  # ParaSwap Augustus v6.2
    "0x5994814f2c4040b863a0125a45de152a8c2a4dec": "DEX_SWAP",  # OKX DEX AggregationRouter
    "0xdef1c0ded9bec7f1a1670819833240f027b25eff": "DEX_SWAP",  # 0x ExchangeProxy
    "0x1a1ec25dc08e98e5e93f1104b5e5cdd298707d31": "DEX_SWAP",  # MetaMask Swap Router
    "0x89b8aa89fdd0507a99d334cbe3c808fafc7d850e": "DEX_SWAP",  # Odos Router V2
    "0x5c952063c7fc8610ffdb798152d69f0b9550762b": "DEX_SWAP",  # Four.meme Bonding Curve
    # Prediction Markets & Perps (Verified Predict.fun CTF / Exchange + PancakeSwap Prediction + Aster/ApolloX)
    "0x8bc070bedab741406f4b1eb65a72bee27894b689": "PREDICTION_PERP",  # Predict.fun CTFExchange
    "0x6beb5a40c032afc305961162d8204cda16decfa5": "PREDICTION_PERP",  # Predict.fun YieldBearing CTFExchange
    "0x8a289d458f5a134ba40015085a8f50ffb681b41d": "PREDICTION_PERP",  # Predict.fun NegRisk CTFExchange
    "0x22da1810b194ca018378464a58f6ac2b10c9d244": "PREDICTION_PERP",  # Predict.fun ConditionalTokens
    "0x9400f8ad57e9e0f352345935d6d3175975eb1d9f": "PREDICTION_PERP",  # Predict.fun YieldBearingConditionalTokens
    "0xf64b0b318aaf83bd9071110af24d24445719a07f": "PREDICTION_PERP",  # Predict.fun NegRisk ConditionalTokens
    "0x18b2a687610328590bc8f2e5fedde3b582a49cda": "PREDICTION_PERP",  # PancakeSwap Prediction V2
    "0x1b6f2d3844c6ae7d56ceb3c3643b9060ba28feb0": "PREDICTION_PERP",  # ApolloX / Aster Perp Router
    # Lending, Staking & Cross-Chain Bridges (Relay Depository + Stargate + Venus + Kinza)
    "0xfd36e2c2a6789db23113685031d7f16329158384": "LENDING_YIELD_BRIDGE",  # Venus Comptroller
    "0xa07c5b74c9b40447a954e1466938b865b6bbea36": "LENDING_YIELD_BRIDGE",  # Venus vBNB
    "0xfd5840cd36d94d7229439859c0112a4185bc0255": "LENDING_YIELD_BRIDGE",  # Venus vUSDT
    "0xcb0620b181140e57d1c0d8b724cde623ca963c8c": "LENDING_YIELD_BRIDGE",  # Kinza Finance Pool
    "0x4cd00e387622c35bddb9b4c962c136462338bc31": "LENDING_YIELD_BRIDGE",  # Relay: Depository (Cross-Chain Bridge)
    "0x4a364f8c717caad9a442737eb7b8a55cc6cf18d8": "LENDING_YIELD_BRIDGE",  # Stargate Router BSC (swap-only)
}
KNOWN_BSC_PROTOCOLS = {k.lower(): v for k, v in KNOWN_BSC_PROTOCOLS.items()}

# EIP-712 Typehashes (Byte-for-byte identical to AgentPulseGate.sol)
EIP712_DOMAIN_TYPEHASH = keccak(
    b"EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
)
ATTESTATION_TYPEHASH = keccak(
    b"LivenessAttestation(address wallet,bytes32 handleHash,uint8 totalScore,uint8 d1Funding,uint8 d2Temporal,uint8 d3Economic,uint8 d4Proof,uint64 issuedAt,uint64 expiresAt,uint256 nonce)"
)
NAME_HASH = keccak(b"AgentPulse")
VERSION_HASH = keccak(b"1")

# Machine-generated gibberish handle regex (e.g. m6n3b7v1.ai, qwer1160115362.ai)
_BOT_HANDLE_RE = re.compile(r"^(?:[a-z]{1,4}\d{6,}|(?:[a-z]\d){3,}[a-z\d]*)$")


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class TransferEvent:
    tx_hash: str
    category: str          # 'external' | 'internal' | '20' | '721'
    from_addr: str
    to_addr: str
    value_float: float     # Normalized float (BNB for external/internal, token units for 20)
    asset: str             # 'BNB', 'USDT', 'USDC', etc.
    contract_addr: str     # Token CA for '20', else 0x0
    timestamp: int
    selector: str = "0x"   # 4-byte method selector (first 10 chars of input)
    status: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tx_hash": self.tx_hash,
            "category": self.category,
            "from_addr": self.from_addr,
            "to_addr": self.to_addr,
            "value_float": self.value_float,
            "asset": self.asset,
            "contract_addr": self.contract_addr,
            "timestamp": self.timestamp,
            "selector": self.selector,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TransferEvent:
        return cls(
            tx_hash=str(data.get("tx_hash") or ""),
            category=str(data.get("category") or "external"),
            from_addr=str(data.get("from_addr") or "").lower(),
            to_addr=str(data.get("to_addr") or "").lower(),
            value_float=float(data.get("value_float") or 0.0),
            asset=str(data.get("asset") or ""),
            contract_addr=str(data.get("contract_addr") or "").lower(),
            timestamp=int(data.get("timestamp") or 0),
            selector=str(data.get("selector") or "0x"),
            status=int(data["status"]) if "status" in data and data["status"] is not None else 1,
        )


@dataclass
class WalletSnapshot:
    address: str
    onchain_handle: str              # From 0x60B9...022F.handleOf(address), e.g. "redkoi.ai" or ""
    nameapi_address: Optional[str]   # Forward check from nameapi.space.id/getAddress?domain=...
    tx_count: int                    # eth_getTransactionCount (outgoing EOA nonces)
    bnb_balance: float
    wbnb_balance: float
    usdt_balance: float
    usdc_balance: float
    fdusd_balance: float
    bnb_price_usd: float = FALLBACK_BNB_PRICE_USD
    bnb_price_source: str = "fallback_default"
    transfers: List[TransferEvent] = field(default_factory=list)
    funder_address: str = ""
    first_funding_bnb: float = 0.0
    first_funding_category: str = ""  # 'external' | 'internal'
    first_funding_selector: str = "0x"
    first_funding_timestamp: int = 0
    funder_fanout_50: int = 0         # Unique recipients in funder's recent outgoing transfers
    funder_same_dust_50: int = 0      # Equal-sized (<0.005 BNB) dust transfers in funder's recent txs
    funder_same_amount_50: int = 0    # Equal-sized batch transfers (ANY BNB size > 0) in funder's recent txs
    funder_is_relay_pass_through: bool = False  # True if funder is a rotating pass-through / ping-pong hub
    contract_nonce: int = 0           # Live nonces(address) (0x7ecebe00) from deployed AgentPulseGate
    indexer_degraded: bool = False
    funder_eoa_out_50: int = 0        # Plain EOA outgoing count in funder's recent window
    stable_funder_tainted: bool = False  # True if external hard-token funder is a batch mother / relay hub
    secondary_funder_tainted: bool = False  # True if any secondary BNB funder is a batch mother / relay hub
    recent_window_truncated: bool = False  # True if unindexed gap remains inside the recent 72h window
    funder_tx_count: int = 0          # eth_getTransactionCount of primary funder
    funder_is_cex_hot_wallet: bool = False  # True if primary funder is a verified/high-nonce CEX hot wallet
    usd1_balance: float = 0.0         # World Liberty Financial USD1 balance (18 dec)
    dai_balance: float = 0.0          # Binance-Peg DAI balance (18 dec)
    busd_balance: float = 0.0         # Binance-Peg BUSD balance (18 dec)


# =============================================================================
# Pure EIP-712 Signing & Verification (100% Parity with AgentPulseGate.sol)
# =============================================================================

def normalize_handle(handle: str) -> str:
    h = (handle or "").strip().lower()
    if not h:
        return ""
    return h if h.endswith(".ai") else f"{h}.ai"


def strip_ai_suffix(handle: str) -> str:
    h = (handle or "").strip().lower()
    return h[:-3] if h.endswith(".ai") else h


def parse_tx_status(item: Mapping[str, Any]) -> int:
    """
    Safely parses transaction execution status across NodeReal (`receiptsStatus`) and
    Etherscan V2 (`isError` / `txreceipt_status`) WITHOUT truthiness short-circuiting on 0!
    Returns 1 ONLY for confirmed successful execution, 0 for reverted/failed execution.
    """
    is_err = item.get("isError")
    if is_err is not None and str(is_err).strip() != "":
        s_err = str(is_err).strip().lower()
        err_int = int(s_err, 16) if s_err.startswith("0x") else int(s_err)
        if err_int != 0:
            return 0

    for key in ("receiptsStatus", "txreceipt_status", "status"):
        if key in item:
            raw = item.get(key)
            if raw is None or raw == "":
                continue
            if isinstance(raw, bool):
                return 1 if raw else 0
            if isinstance(raw, int):
                return 1 if raw == 1 else 0
            s_val = str(raw).strip().lower()
            if not s_val:
                continue
            parsed_int = int(s_val, 16) if s_val.startswith("0x") else int(s_val)
            return 1 if parsed_int == 1 else 0

    return 1


def compute_domain_separator(chain_id: int = BSC_CHAIN_ID, verifying_contract: str = DEFAULT_VERIFYING_CONTRACT) -> bytes:
    vc = to_checksum_address(verifying_contract)
    return keccak(
        abi_encode(
            ["bytes32", "bytes32", "bytes32", "uint256", "address"],
            [EIP712_DOMAIN_TYPEHASH, NAME_HASH, VERSION_HASH, int(chain_id), vc],
        )
    )


def compute_attestation_digest(
    wallet: str,
    handle: str,
    total_score: int,
    d1_funding: int,
    d2_temporal: int,
    d3_economic: int,
    d4_proof: int,
    issued_at: int,
    expires_at: int,
    nonce: int = 0,
    chain_id: int = BSC_CHAIN_ID,
    verifying_contract: str = DEFAULT_VERIFYING_CONTRACT,
) -> Tuple[bytes, bytes, bytes]:
    """
    Returns (digest_32b, domain_separator_32b, struct_hash_32b) matching AgentPulseGate.sol.
    """
    norm_h = normalize_handle(handle)
    handle_hash = keccak(norm_h.encode("utf-8"))
    checksum_wallet = to_checksum_address(wallet)
    struct_hash = keccak(
        abi_encode(
            [
                "bytes32",
                "address",
                "bytes32",
                "uint8",
                "uint8",
                "uint8",
                "uint8",
                "uint8",
                "uint64",
                "uint64",
                "uint256",
            ],
            [
                ATTESTATION_TYPEHASH,
                checksum_wallet,
                handle_hash,
                int(total_score),
                int(d1_funding),
                int(d2_temporal),
                int(d3_economic),
                int(d4_proof),
                int(issued_at),
                int(expires_at),
                int(nonce),
            ],
        )
    )
    domain_sep = compute_domain_separator(chain_id=chain_id, verifying_contract=verifying_contract)
    digest = keccak(b"\x19\x01" + domain_sep + struct_hash)
    return digest, domain_sep, struct_hash


def sign_attestation_digest(digest: bytes, private_key_hex: Optional[str] = None) -> Dict[str, Any]:
    """Signs raw 32-byte EIP-712 digest using eth_account PrivateKey.sign_msg_hash (standard EIP-712 r||s||v)."""
    pk = (private_key_hex or os.environ.get("AGENT_PULSE_SIGNER_KEY") or _DEMO_SIGNER_PRIVKEY).strip()
    acct = Account.from_key(pk)
    signed = Account._keys.PrivateKey(bytes.fromhex(pk[2:] if pk.startswith("0x") else pk)).sign_msg_hash(digest)
    v = signed.v + 27 if signed.v < 27 else signed.v
    r_bytes = int(signed.r).to_bytes(32, "big")
    s_bytes = int(signed.s).to_bytes(32, "big")
    sig_bytes = r_bytes + s_bytes + bytes([v])
    return {
        "signer": acct.address,
        "isDemoSigner": not bool(private_key_hex or os.environ.get("AGENT_PULSE_SIGNER_KEY")),
        "digest": "0x" + digest.hex(),
        "signature": "0x" + sig_bytes.hex(),
        "v": v,
        "r": "0x" + r_bytes.hex(),
        "s": "0x" + s_bytes.hex(),
    }


def recover_attestation_signer(digest: bytes, signature_hex: str) -> str:
    """Pure Python ecrecover equivalent matching AgentPulseGate._recoverSigner."""
    raw = bytes.fromhex(signature_hex[2:] if signature_hex.startswith("0x") else signature_hex)
    if len(raw) != 65:
        raise ValueError("Invalid signature length (expected 65 bytes)")
    r = int.from_bytes(raw[0:32], "big")
    s = int.from_bytes(raw[32:64], "big")
    v = raw[64]
    v_norm = v - 27 if v >= 27 else v
    if v_norm not in (0, 1):
        raise ValueError("Invalid recovery id v")
    secp256k1n_half = 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0
    if s > secp256k1n_half:
        raise ValueError("EIP-2 signature malleability violation: s > secp256k1n/2")
    sig_obj = Account._keys.Signature(vrs=(v_norm, r, s))
    pub = sig_obj.recover_public_key_from_msg_hash(digest)
    return pub.to_checksum_address()


def refresh_report_attestation(
    report: Dict[str, Any],
    *,
    nonce: int,
    now_ts: Optional[int] = None,
    chain_id: int = BSC_CHAIN_ID,
    verifying_contract: str = DEFAULT_VERIFYING_CONTRACT,
    ttl_seconds: int = 86400 * 14,
    signer_private_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Re-signs a cached report with a freshly queried on-chain contract `nonce` (`0x7ecebe00`)."""
    updated = copy.deepcopy(report)
    issued_at = int(now_ts if now_ts is not None else time.time())
    expires_at = issued_at + int(ttl_seconds)
    payload = updated["eip712"]["payload"]
    handle = updated["handle"] or "unbound.ai"

    digest, domain_sep, struct_hash = compute_attestation_digest(
        wallet=updated["address"],
        handle=handle,
        total_score=int(payload["totalScore"]),
        d1_funding=int(payload["d1Funding"]),
        d2_temporal=int(payload["d2Temporal"]),
        d3_economic=int(payload["d3Economic"]),
        d4_proof=int(payload["d4Proof"]),
        issued_at=issued_at,
        expires_at=expires_at,
        nonce=int(nonce),
        chain_id=chain_id,
        verifying_contract=verifying_contract,
    )
    sig_bundle = sign_attestation_digest(digest, private_key_hex=signer_private_key)
    recovered = recover_attestation_signer(digest, sig_bundle["signature"])
    if recovered.lower() != sig_bundle["signer"].lower():
        raise RuntimeError("CRITICAL: EIP-712 local ecrecover self-check failed during nonce refresh")

    updated["dimensions"]["d4Proof"]["contractNonce"] = int(nonce)
    payload["issuedAt"] = issued_at
    payload["expiresAt"] = expires_at
    payload["nonce"] = int(nonce)
    updated["eip712"]["domain"]["verifyingContract"] = to_checksum_address(verifying_contract)
    updated["eip712"]["domainSeparator"] = "0x" + domain_sep.hex()
    updated["eip712"]["structHash"] = "0x" + struct_hash.hex()
    updated["eip712"]["signature"] = sig_bundle["signature"]
    updated["eip712"]["digest"] = sig_bundle["digest"]
    updated["eip712"]["verifierSigner"] = sig_bundle["signer"]
    updated["eip712"]["isDemoSigner"] = sig_bundle["isDemoSigner"]
    return updated


# =============================================================================
# Deterministic 4-Dimensional Scoring Engine (Fail-Closed & Sybil-Resistant)
# =============================================================================

def _extract_external_funding_envelope(
    addr_low: str,
    bnb_price_usd: float,
    transfers: Sequence[TransferEvent],
    explicit_primary_funder: str = "",
) -> Tuple[
    List[TransferEvent],
    List[TransferEvent],
    Optional[TransferEvent],
    List[Tuple[str, float, TransferEvent]],
    List[Tuple[str, float, TransferEvent]],
]:
    """
    Single Source of Truth for external hard-liquid funding extraction & audit-envelope selection,
    shared byte-for-byte between `AgentLivenessScorer._extract_candidate_funders` AND `score_wallet_snapshot`.
    Critically: does NOT exclude outgoing `external` calls to non-protocol contracts (such as `PullVault.claim()`
    with `1e12 wei` BNB), so self-pulled vaults are 100% audited AND reconciled identically!
    """
    zero_addr = "0x0000000000000000000000000000000000000000"
    a_low = addr_low.lower()
    proto_tx_hashes: Set[str] = set()
    tx_in_usd: Dict[str, float] = {}
    tx_out_usd: Dict[str, float] = {}

    for t in transfers:
        if t.status != 1:
            continue
        txh = (t.tx_hash or "").lower()
        frm_l = t.from_addr.lower()
        to_l = t.to_addr.lower()
        ca_l = t.contract_addr.lower()
        if t.category == "external" and frm_l == a_low and txh:
            if (
                to_l in KNOWN_BSC_PROTOCOLS
                and (t.selector or "0x")[:10].lower() not in ZERO_FRICTION_SELECTORS
            ):
                proto_tx_hashes.add(txh)
        if t.value_float <= 0 or (frm_l == a_low and to_l == a_low):
            continue
        if t.category in ("external", "internal") and (
            (frm_l == a_low and to_l == BSC_WBNB) or (frm_l == BSC_WBNB and to_l == a_low)
        ):
            continue
        if t.category == "20" and ca_l == BSC_WBNB and (frm_l == zero_addr or to_l == zero_addr):
            continue
        u_val = 0.0
        if t.category in ("external", "internal"):
            u_val = t.value_float * bnb_price_usd
        elif t.category == "20" and ca_l in HARD_LIQUID_TOKENS:
            u_val = t.value_float * (bnb_price_usd if ca_l == BSC_WBNB else 1.0)
        if u_val > 0 and txh:
            if (
                to_l == a_low
                and frm_l not in KNOWN_BSC_PROTOCOLS
                and not (t.category == "20" and frm_l == zero_addr)
            ):
                tx_in_usd[txh] = tx_in_usd.get(txh, 0.0) + u_val
            elif frm_l == a_low:
                tx_out_usd[txh] = tx_out_usd.get(txh, 0.0) + u_val

    def _net_ext_funding_scale(ev: TransferEvent) -> float:
        """
        Exact Balance-Sheet Inflow Conservation (immune to `BounceFundVault` partial-bounce smuggling!):
        1) Whitelisted protocol calls (`h_l in proto_tx_hashes`) are portfolio conversions/redemptions, NOT external funding (`0.0`).
        2) Non-protocol pure self-bounces (`gin <= gout`) inject ZERO net capital (`0.0`).
        3) ANY non-protocol transaction with `gin > gout` (`PullVault` 1-wei pull, `BounceFundVault` 38%..99% bounce, etc.)
           is external funding scaled by `(gin - gout) / gin` so `sum(scaled_inflows) == gin - gout` dollar-for-dollar!
        """
        h_l = (ev.tx_hash or "").lower()
        if not h_l:
            return 1.0
        if h_l in proto_tx_hashes:
            return 0.0
        gin = tx_in_usd.get(h_l, 0.0)
        gout = tx_out_usd.get(h_l, 0.0)
        net_u = gin - gout
        if gin <= 0.0 or net_u <= 1e-9:
            return 0.0
        return min(1.0, net_u / gin)

    ext_bnb_events: List[TransferEvent] = []
    raw_bnb_events_paired: List[Tuple[TransferEvent, TransferEvent]] = []
    for t in transfers:
        if (
            t.status == 1
            and t.value_float > 0
            and t.category in ("external", "internal")
            and t.to_addr.lower() == a_low
            and t.from_addr.lower() != a_low
            and t.from_addr.lower() != BSC_WBNB
            and t.from_addr.lower() not in KNOWN_BSC_PROTOCOLS
        ):
            sc_b = _net_ext_funding_scale(t)
            if sc_b > 0.0:
                ev_b_net = replace(t, value_float=t.value_float * sc_b) if sc_b < (1.0 - 1e-12) else t
                ext_bnb_events.append(ev_b_net)
                raw_bnb_events_paired.append((ev_b_net, t))

    ext_tok_events: List[TransferEvent] = []
    raw_tok_events_paired: List[Tuple[TransferEvent, TransferEvent]] = []
    for t in transfers:
        if (
            t.status == 1
            and t.value_float > 0
            and t.category == "20"
            and t.to_addr.lower() == a_low
            and t.from_addr.lower() != a_low
            and t.from_addr.lower() != zero_addr
            and t.from_addr.lower() not in KNOWN_BSC_PROTOCOLS
            and t.contract_addr.lower() in HARD_LIQUID_TOKENS
        ):
            sc_t = _net_ext_funding_scale(t)
            if sc_t > 0.0:
                ev_t_net = replace(t, value_float=t.value_float * sc_t) if sc_t < (1.0 - 1e-12) else t
                ext_tok_events.append(ev_t_net)
                raw_tok_events_paired.append((ev_t_net, t))

    first_in = raw_bnb_events_paired[0][1] if raw_bnb_events_paired else None
    primary_funder = explicit_primary_funder.lower() or (first_in.from_addr.lower() if first_in else "")

    sec_bnb_totals: Dict[str, float] = {}
    sec_bnb_max: Dict[str, TransferEvent] = {}
    for ev_b_net, ev_b_raw in raw_bnb_events_paired:
        sf_b = ev_b_net.from_addr.lower()
        if sf_b == primary_funder or sf_b in BATCH_DISPERSE_CONTRACTS:
            continue
        sec_bnb_totals[sf_b] = sec_bnb_totals.get(sf_b, 0.0) + ev_b_net.value_float
        prev_b = sec_bnb_max.get(sf_b)
        if prev_b is None or ev_b_raw.value_float > prev_b.value_float:
            sec_bnb_max[sf_b] = ev_b_raw

    sec_candidates = [
        (sec_addr, sec_tot, sec_bnb_max[sec_addr])
        for sec_addr, sec_tot in sorted(sec_bnb_totals.items(), key=lambda kv: kv[1], reverse=True)[:MAX_CANDIDATE_FUNDERS_PER_TYPE]
        if sec_tot >= MIN_CANDIDATE_SEC_BNB and sec_addr in sec_bnb_max
    ]

    tok_funder_totals: Dict[str, float] = {}
    tok_funder_max: Dict[str, Tuple[float, TransferEvent]] = {}
    for ev_t_net, ev_t_raw in raw_tok_events_paired:
        sf_t = ev_t_net.from_addr.lower()
        if sf_t in BATCH_DISPERSE_CONTRACTS:
            continue
        unit_m = bnb_price_usd if ev_t_net.contract_addr.lower() == BSC_WBNB else 1.0
        u_leg_net = ev_t_net.value_float * unit_m
        u_leg_raw = ev_t_raw.value_float * unit_m
        tok_funder_totals[sf_t] = tok_funder_totals.get(sf_t, 0.0) + u_leg_net
        prev_tok = tok_funder_max.get(sf_t)
        if prev_tok is None or u_leg_raw > prev_tok[0]:
            tok_funder_max[sf_t] = (u_leg_raw, ev_t_raw)

    tok_candidates = [
        (sf_addr, sf_tot_usd, tok_funder_max[sf_addr][1])
        for sf_addr, sf_tot_usd in sorted(tok_funder_totals.items(), key=lambda kv: kv[1], reverse=True)[:MAX_CANDIDATE_FUNDERS_PER_TYPE]
        if sf_tot_usd >= MIN_CANDIDATE_TOKEN_USD and sf_addr in tok_funder_max
    ]
    return ext_bnb_events, ext_tok_events, first_in, sec_candidates, tok_candidates


def _reconcile_alt_and_receipt_disposals(
    addr_low: str,
    token_transfers: Sequence[TransferEvent],
    all_seen_tx_hashes: Set[str],
    tx_hard_out_usd_pre: Mapping[str, float],
    tx_hard_in_usd_pre: Mapping[str, float],
    tx_non_hard_erc20_in: Mapping[str, bool],
    tx_batch_or_vm_dex_hashes: Set[str],
    unverified_dex_tx_hashes: Set[str],
    unreceipted_lending_tx_hashes: Set[str],
    unreceipted_lp_tx_hashes: Set[str],
    dex_settlement_tx_hashes: Set[str],
    lending_receipt_token_cas: Set[str],
    lp_receipt_token_cas: Set[str],
    lending_redeem_tx_hashes: Set[str],
    zero_fee_lp_redeem_tx_hashes: Set[str],
    apx_exit_tx_hashes: Set[str],
    is_verified_outflow_fn: Any,
) -> Tuple[float, float, Dict[str, float], int]:
    """
    Anti-Dilution & Receipt-Burn Cost-Basis Conservation on Non-Hard ERC-20s (`CAKE`, `kUSDT`, `vUSDT`, `S*USDT`, `Cake-LP`):
    1) Never divides `net_spent_tx` by `len(same_tx_alt_legs)` (immunizes against `1/N` junk-token dust dilution);
    2) Audits ALL outbound disposals INCLUDING `to_ev == zero_addr` receipt/LP burns (`Kinza.withdraw(COLLECTOR_EOA)`,
       `StargateRouter.instantRedeemLocal(COLLECTOR_EOA)`, `PancakeV2.removeLiquidity(COLLECTOR_EOA)`), requiring
       dollar-for-dollar hard-liquid return to `addr_low` in the same tx or charging unrecovered cost to `swept_acquired_alt_usd`;
    3) Reconciles ALL `Alt -> Hard` disposals across EVERY DEX/aggregator (`KyberSwap`, `1inch`, `Pancake`, `UniversalRouter`)
       and rolls cost basis across `Alt1 -> Alt2` hops, bounded by `total_hard_into_alt_pool_usd`.
    """
    zero_addr = "0x0000000000000000000000000000000000000000"
    alt_cost_basis_usd: Dict[str, float] = {}
    alt_rem_cost_usd: Dict[str, float] = {}
    alt_qty_acquired: Dict[str, float] = {}
    alt_from_dex_cas: Set[str] = set()
    swept_acquired_alt_usd = 0.0
    swept_dex_alt_usd = 0.0
    swept_acquired_alt_by_to: Dict[str, float] = {}
    total_hard_into_alt_pool_usd = 0.0
    counted_hard_alt_txs: Set[str] = set()
    revoked_dex_friction_cnt = 0
    tx_rem_net_hard_in: Dict[str, float] = {
        h_k: max(0.0, tx_hard_in_usd_pre.get(h_k, 0.0) - tx_hard_out_usd_pre.get(h_k, 0.0))
        for h_k in all_seen_tx_hashes
    }

    ordered_tok_events = sorted(
        enumerate(token_transfers),
        key=lambda pair: (pair[1].timestamp, pair[0]),
    )
    in_alt_qty_by_tx_ca: Dict[Tuple[str, str], float] = {}
    for _, t in ordered_tok_events:
        txh_a = (t.tx_hash or "").lower()
        ca_a = t.contract_addr.lower()
        if (
            txh_a
            and t.to_addr.lower() == addr_low
            and t.from_addr.lower() != addr_low
            and ca_a not in HARD_LIQUID_TOKENS
        ):
            in_alt_qty_by_tx_ca[(txh_a, ca_a)] = in_alt_qty_by_tx_ca.get((txh_a, ca_a), 0.0) + t.value_float

    processed_in_tx_ca: Set[Tuple[str, str]] = set()
    tx_rolled_alt_cost: Dict[str, float] = {}
    for _, t in ordered_tok_events:
        txh_ev = (t.tx_hash or "").lower()
        frm_ev = t.from_addr.lower()
        to_ev = t.to_addr.lower()
        ca_ev = t.contract_addr.lower()
        if ca_ev in HARD_LIQUID_TOKENS:
            continue
        if to_ev == addr_low and frm_ev != addr_low and txh_ev:
            if (txh_ev, ca_ev) in processed_in_tx_ca:
                continue
            processed_in_tx_ca.add((txh_ev, ca_ev))
            hard_spent = 0.0
            if (
                txh_ev not in unverified_dex_tx_hashes
                and txh_ev not in unreceipted_lending_tx_hashes
                and txh_ev not in unreceipted_lp_tx_hashes
            ):
                hard_spent = max(0.0, tx_hard_out_usd_pre.get(txh_ev, 0.0) - tx_hard_in_usd_pre.get(txh_ev, 0.0))
                if hard_spent > 0.0 and txh_ev not in counted_hard_alt_txs:
                    counted_hard_alt_txs.add(txh_ev)
                    total_hard_into_alt_pool_usd += hard_spent
                if hard_spent > 0.0 and txh_ev in dex_settlement_tx_hashes:
                    alt_from_dex_cas.add(ca_ev)
            tx_cost_full = hard_spent + tx_rolled_alt_cost.get(txh_ev, 0.0)
            if tx_cost_full > 0.0:
                alt_cost_basis_usd[ca_ev] = alt_cost_basis_usd.get(ca_ev, 0.0) + tx_cost_full
                alt_rem_cost_usd[ca_ev] = alt_rem_cost_usd.get(ca_ev, 0.0) + tx_cost_full
                alt_qty_acquired[ca_ev] = alt_qty_acquired.get(ca_ev, 0.0) + in_alt_qty_by_tx_ca.get((txh_ev, ca_ev), t.value_float)
        elif (
            frm_ev == addr_low
            and to_ev != addr_low
            and alt_rem_cost_usd.get(ca_ev, 0.0) > 0.0
            and alt_qty_acquired.get(ca_ev, 0.0) > 0.0
        ):
            prop_cost = alt_cost_basis_usd[ca_ev] * min(1.0, t.value_float / alt_qty_acquired[ca_ev])
            leg_cost = min(alt_rem_cost_usd[ca_ev], prop_cost)
            alt_rem_cost_usd[ca_ev] -= leg_cost

            is_burn_or_vault_redeem = (
                to_ev == zero_addr
                or ca_ev in lending_receipt_token_cas
                or ca_ev in lp_receipt_token_cas
                or to_ev in LENDING_POOL_CONTRACTS
                or bool(
                    txh_ev
                    and (
                        txh_ev in lending_redeem_tx_hashes
                        or txh_ev in zero_fee_lp_redeem_tx_hashes
                        or txh_ev in apx_exit_tx_hashes
                    )
                )
            )
            if is_burn_or_vault_redeem:
                avail_in = tx_rem_net_hard_in.get(txh_ev, 0.0) if txh_ev else 0.0
                recovered_c = min(leg_cost, avail_in / 0.98)
                if txh_ev:
                    tx_rem_net_hard_in[txh_ev] = max(0.0, avail_in - min(avail_in, recovered_c))
                unrec_c = max(0.0, leg_cost - recovered_c)
                if unrec_c > 1e-6:
                    rem_pool_cap = max(0.0, total_hard_into_alt_pool_usd - swept_acquired_alt_usd)
                    drained_c = min(unrec_c, rem_pool_cap)
                    if drained_c > 0.0:
                        swept_acquired_alt_usd += drained_c
                        if ca_ev in alt_from_dex_cas:
                            swept_dex_alt_usd += drained_c
                        if to_ev != zero_addr:
                            swept_acquired_alt_by_to[to_ev] = swept_acquired_alt_by_to.get(to_ev, 0.0) + drained_c
            elif is_verified_outflow_fn(to_ev, txh_ev, 0.0):
                avail_in_swap = tx_rem_net_hard_in.get(txh_ev, 0.0) if txh_ev else 0.0
                if (
                    txh_ev
                    and tx_non_hard_erc20_in.get(txh_ev, False)
                    and txh_ev not in tx_batch_or_vm_dex_hashes
                    and avail_in_swap < 0.80 * leg_cost
                ):
                    tx_rolled_alt_cost[txh_ev] = tx_rolled_alt_cost.get(txh_ev, 0.0) + leg_cost
                    for (h_chk, ca_chk) in list(processed_in_tx_ca):
                        if h_chk == txh_ev and ca_chk != ca_ev:
                            alt_cost_basis_usd[ca_chk] = alt_cost_basis_usd.get(ca_chk, 0.0) + leg_cost
                            alt_rem_cost_usd[ca_chk] = alt_rem_cost_usd.get(ca_chk, 0.0) + leg_cost
                            if ca_ev in alt_from_dex_cas:
                                alt_from_dex_cas.add(ca_chk)
                else:
                    if avail_in_swap >= 0.80 * leg_cost:
                        if txh_ev:
                            tx_rem_net_hard_in[txh_ev] = max(0.0, avail_in_swap - min(avail_in_swap, leg_cost))
                    else:
                        unrec_c = max(0.0, leg_cost - avail_in_swap)
                        if txh_ev:
                            tx_rem_net_hard_in[txh_ev] = 0.0
                        rem_pool_cap = max(0.0, total_hard_into_alt_pool_usd - swept_acquired_alt_usd)
                        drained_c = min(unrec_c, rem_pool_cap)
                        if drained_c > 0.0:
                            swept_acquired_alt_usd += drained_c
                            if ca_ev in alt_from_dex_cas:
                                swept_dex_alt_usd += drained_c
                        if txh_ev and avail_in_swap < 0.50 * leg_cost and txh_ev in dex_settlement_tx_hashes:
                            dex_settlement_tx_hashes.discard(txh_ev)
                            revoked_dex_friction_cnt += 1
            else:
                avail_in_unver = (
                    tx_rem_net_hard_in.get(txh_ev, 0.0)
                    if (txh_ev and KNOWN_BSC_PROTOCOLS.get(to_ev) == "DEX_SWAP")
                    else 0.0
                )
                if txh_ev and avail_in_unver > 0.0:
                    tx_rem_net_hard_in[txh_ev] = 0.0
                unrec_c_else = max(0.0, leg_cost - avail_in_unver)
                rem_pool_cap = max(0.0, total_hard_into_alt_pool_usd - swept_acquired_alt_usd)
                drained_c = min(unrec_c_else, rem_pool_cap)
                if drained_c > 0.0:
                    swept_acquired_alt_usd += drained_c
                    if ca_ev in alt_from_dex_cas:
                        swept_dex_alt_usd += drained_c
                    swept_acquired_alt_by_to[to_ev] = swept_acquired_alt_by_to.get(to_ev, 0.0) + drained_c

    return swept_acquired_alt_usd, swept_dex_alt_usd, swept_acquired_alt_by_to, revoked_dex_friction_cnt


def _compute_d2_temporal_dimension(
    ts_sorted: Sequence[int],
    span_days: float,
    active_days: int,
    effective_tx_count: int,
    snap_tx_count: int,
    history_unverified: bool,
    fee_bearing_tx_count: int,
    sybil_provenance_tainted: bool,
    track_b_eligible: bool,
    effective_seasoned_usd: float,
    risk_flags: List[str],
    reasons: List[str],
) -> Tuple[int, float, float]:
    """Computes D2 Multi-Day Temporal Maturity & Inter-Arrival Entropy (0..25 pts)."""
    if len(ts_sorted) >= 2:
        raw_deltas = [ts_sorted[i + 1] - ts_sorted[i] for i in range(len(ts_sorted) - 1)]
        pos_deltas = [d for d in raw_deltas if d > 0] or raw_deltas
        mean_dt = sum(pos_deltas) / len(pos_deltas) if pos_deltas else 0.0
        if mean_dt > 0 and len(pos_deltas) >= 2:
            var_dt = sum((d - mean_dt) ** 2 for d in pos_deltas) / len(pos_deltas)
            cv = math.sqrt(var_dt) / mean_dt
        else:
            cv = 0.0

        buckets = [0, 0, 0, 0, 0, 0]
        for d in raw_deltas:
            if d <= 30:
                buckets[0] += 1
            elif d <= 300:
                buckets[1] += 1
            elif d <= 3600:
                buckets[2] += 1
            elif d <= 21600:
                buckets[3] += 1
            elif d <= 86400:
                buckets[4] += 1
            else:
                buckets[5] += 1
        total_b = len(raw_deltas)
        entropy_bits = 0.0
        for count_b in buckets:
            if count_b > 0:
                p_b = count_b / total_b
                entropy_bits -= p_b * math.log2(p_b)
        norm_entropy = entropy_bits / math.log2(6.0)
    else:
        cv = 0.0
        entropy_bits = 0.0
        norm_entropy = 0.0

    if span_days < (1.0 / 24.0):
        span_pts = 0
        if effective_tx_count >= 1 and not history_unverified:
            risk_flags.append("SINGLE_HOUR_DORMANT_SHELL")
    elif span_days >= 21.0 or active_days >= 6:
        span_pts = 10
    elif span_days >= 14.0 or active_days >= 5:
        span_pts = 9
    elif span_days >= 7.0 or active_days >= 4:
        span_pts = 7
    elif span_days >= 3.0 or active_days >= 3:
        span_pts = 5
    elif span_days >= 1.0 or active_days >= 2:
        span_pts = 3
    else:
        span_pts = 1

    if effective_tx_count <= 1:
        tx_pts = 0
    elif effective_tx_count <= 4:
        tx_pts = 2
    elif effective_tx_count <= 14:
        tx_pts = 4
    elif effective_tx_count <= 39:
        tx_pts = 6
    else:
        tx_pts = 7

    if len(ts_sorted) < 3:
        entropy_pts = 0
    elif len(ts_sorted) >= 5 and cv < 0.22:
        entropy_pts = 1
        risk_flags.append("CRON_FIXED_INTERVAL_SCRIPT")
    else:
        raw_ent_pts = 4.8 * norm_entropy + min(3.2, cv * 1.6)
        entropy_pts = int(min(8, round(raw_ent_pts)))

    if history_unverified or len(ts_sorted) == 0:
        d2_score = 0
        reasons.append(f"D2(0/25): 缺乏已验证主动交易时间序列 (RPC nonce={snap_tx_count})")
    else:
        raw_d2 = min(25, span_pts + tx_pts + entropy_pts)
        if span_days < (1.0 / 24.0):
            d2_score = 0
        elif span_days < 1.0 or active_days < 2:
            d2_score = min(raw_d2, 2)
        elif span_days < 3.0:
            d2_score = min(raw_d2, 2 if fee_bearing_tx_count == 0 else 5)
        elif fee_bearing_tx_count == 0:
            d2_score = min(raw_d2, 7)
        else:
            d2_score = raw_d2

        if sybil_provenance_tainted:
            d2_score = min(d2_score, 10)
        elif (not track_b_eligible) and effective_seasoned_usd < MIN_SEASONED_COMMITMENT_USD and fee_bearing_tx_count >= 1:
            d2_score = min(d2_score, 12)

        reasons.append(
            f"D2({d2_score}/25): 跨度 {span_days:.2f}天 ({active_days}活跃日), 主动交易 {effective_tx_count}笔, 间隔熵 H={entropy_bits:.2f}bit / CV={cv:.2f}"
        )
    return d2_score, entropy_bits, cv


def score_wallet_snapshot(
    snap: WalletSnapshot,
    *,
    now_ts: Optional[int] = None,
    chain_id: int = BSC_CHAIN_ID,
    verifying_contract: str = DEFAULT_VERIFYING_CONTRACT,
    ttl_seconds: int = 86400 * 14,
    signer_private_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Computes the 0..100 4D Proof-of-Live-Agent score deterministically from a WalletSnapshot.

    Key Security Invariants (Aligned Numerically with On-Chain `totalScore >= 60`):
    1. Fail-Closed on Unverified History/Funder: If `indexer_degraded` is True or `tx_count > 0` with empty
       `transfers`, `INDEXER_HISTORY_UNVERIFIED_FAIL_CLOSED` caps `totalScore < 35` and `isLiveAgent60 = False`.
    2. Strict Whitelisted Protocol Friction: ONLY curated `KNOWN_BSC_PROTOCOLS` with net non-refunded value
       settlement earn economic friction (`real_economic_tx_count`). Custom user-deployed payable bounce contracts,
       1:1 `WBNB.deposit/withdraw`, `ERC20.transfer`, and `approve/checkIn` earn 0 economic friction!
    3. External Funding Purity & 72h Capital Seasoning: Self-triggered internal refunds (`tx_hash` in `outgoing_ext`),
       `WBNB`, and DeFi protocol payouts are excluded from external funding. Capital injected `< 72h` ago is treated
       as unseasoned hot money (`seasoned_retained_usd = max(0, retained_usd - unseasoned_inflow_usd)`).
    4. Multi-Day Maturity & Provenance Taint Ceilings: Wallets with `span_days < 3.0` or `active_days < 2`,
       zero-friction wallets, and confirmed Sybil provenance (Disperse / Homogeneous Mother / Pass-Through Relay /
       Sweep-Back) are numerically bounded `< 60` so neither off-chain nor on-chain `isLiveAgent(60)` can be bypassed.
    """
    addr_low = snap.address.lower()
    issued_at = int(now_ts if now_ts is not None else time.time())
    expires_at = issued_at + int(ttl_seconds)
    seasoning_cutoff = issued_at - CAPITAL_SEASONING_WINDOW_SEC

    reasons: List[str] = []
    risk_flags: List[str] = []

    # Strictly filter to status == 1 confirmed executions across ALL categories
    outgoing_ext = [
        t for t in snap.transfers
        if t.category == "external" and t.from_addr.lower() == addr_low and t.status == 1
    ]
    incoming_ext_int = [
        t for t in snap.transfers
        if t.category in ("external", "internal")
        and t.to_addr.lower() == addr_low
        and t.value_float > 0
        and t.status == 1
    ]
    token_transfers = [
        t for t in snap.transfers
        if t.category == "20"
        and (t.from_addr.lower() == addr_low or t.to_addr.lower() == addr_low)
        and t.value_float > 0
        and t.status == 1
    ]

    history_unverified = bool(snap.indexer_degraded) or (
        snap.tx_count > 0 and len(outgoing_ext) == 0 and len(incoming_ext_int) == 0 and len(token_transfers) == 0
    )
    if history_unverified:
        risk_flags.append("INDEXER_HISTORY_UNVERIFIED_FAIL_CLOSED")

    outgoing_tx_hashes: Set[str] = {(t.tx_hash or "").lower() for t in outgoing_ext if t.tx_hash}

    # -------------------------------------------------------------------------
    # Pre-Pass: Strictly Whitelisted Protocol Friction, Self-Beneficiary Swap Return Check & Wash Guard
    # -------------------------------------------------------------------------
    zero_addr = "0x0000000000000000000000000000000000000000"
    tx_hard_out_usd_pre: Dict[str, float] = {}
    tx_hard_in_usd_pre: Dict[str, float] = {}
    tx_non_hard_erc20_in: Dict[str, bool] = {}
    tx_non_hard_erc20_out: Dict[str, bool] = {}
    tx_batch_or_vm_dex_hashes: Set[str] = set()
    tx_ctf_split_hashes: Set[str] = set()
    lending_redeem_tx_hashes: Set[str] = set()
    lending_active_exit_tx_hashes: Set[str] = set()
    zero_fee_lp_redeem_tx_hashes: Set[str] = set()
    apx_exit_tx_hashes: Set[str] = set()

    for tx_ext in outgoing_ext:
        h_ext = (tx_ext.tx_hash or "").lower()
        if not h_ext:
            continue
        sel_ext = (tx_ext.selector or "0x")[:10].lower()
        to_ext = (tx_ext.to_addr or "").lower()
        if sel_ext in DEX_BATCH_SPLIT_SELECTORS or to_ext in DEX_COMMAND_VM_ROUTERS:
            tx_batch_or_vm_dex_hashes.add(h_ext)
        if sel_ext == "0x72ce4275":
            tx_ctf_split_hashes.add(h_ext)
        if to_ext in LENDING_POOL_CONTRACTS and sel_ext in LENDING_REDEEM_SELECTORS:
            lending_redeem_tx_hashes.add(h_ext)
            if sel_ext != "0xede4edd0":
                lending_active_exit_tx_hashes.add(h_ext)
        if to_ext in KNOWN_BSC_PROTOCOLS and sel_ext in ZERO_FEE_LP_REDEEM_SELECTORS:
            zero_fee_lp_redeem_tx_hashes.add(h_ext)
        if to_ext == APX_V2_TRADING_DIAMOND and sel_ext in APX_V2_EXIT_OR_ADMIN_SELECTORS:
            apx_exit_tx_hashes.add(h_ext)

    for t in snap.transfers:
        if t.status != 1 or t.value_float <= 0:
            continue
        txh_p = (t.tx_hash or "").lower()
        if not txh_p:
            continue
        frm_p = t.from_addr.lower()
        to_p = t.to_addr.lower()
        ca_p = t.contract_addr.lower()
        if frm_p == addr_low and to_p == addr_low:
            continue
        if t.category in ("external", "internal") and (
            (frm_p == addr_low and to_p == BSC_WBNB) or (frm_p == BSC_WBNB and to_p == addr_low)
        ):
            continue
        if t.category == "20" and ca_p == BSC_WBNB and (frm_p == zero_addr or to_p == zero_addr):
            continue

        if t.category in ("external", "internal"):
            u_p = t.value_float * snap.bnb_price_usd
            if frm_p == addr_low:
                tx_hard_out_usd_pre[txh_p] = tx_hard_out_usd_pre.get(txh_p, 0.0) + u_p
            elif to_p == addr_low:
                tx_hard_in_usd_pre[txh_p] = tx_hard_in_usd_pre.get(txh_p, 0.0) + u_p
        elif t.category == "20":
            if to_p == addr_low and ca_p not in HARD_LIQUID_TOKENS:
                tx_non_hard_erc20_in[txh_p] = True
            if frm_p == addr_low and to_p != zero_addr and ca_p not in HARD_LIQUID_TOKENS:
                tx_non_hard_erc20_out[txh_p] = True
            if ca_p in HARD_LIQUID_TOKENS:
                u_p = t.value_float * (snap.bnb_price_usd if ca_p == BSC_WBNB else 1.0)
                if frm_p == addr_low:
                    tx_hard_out_usd_pre[txh_p] = tx_hard_out_usd_pre.get(txh_p, 0.0) + u_p
                elif to_p == addr_low:
                    tx_hard_in_usd_pre[txh_p] = tx_hard_in_usd_pre.get(txh_p, 0.0) + u_p

    # Self-Beneficiary DEX Swap Invariant:
    # 1) Batch / Command-VM routers (`SmartRouter.multicall`, `UniversalRouter.execute`) can bundle a `99.95%`
    #    third-party `recipient = COLLECTOR_EOA` / `PAY_PORTION` leg alongside a `0.05%` micro-altcoin leg to `SELF`;
    #    therefore batch/VM DEX txs NEVER qualify via unpriced `tx_non_hard_erc20_in` when `h_out_c > 0` — they strictly
    #    require `>= 80%` hard-liquid USD return (`h_in_c >= 0.80 * h_out_c`, or `>= $1.00` when `h_out_c == 0`)!
    # 2) Single-swap methods (`exactInputSingle`, `swapExactETHForTokens`, `KyberSwap.swap`, `1inch.swap`) require
    #    either `>= 80%` hard-liquid return (or `>= $1.00` when selling an altcoin with `h_out_c == 0`) OR a non-hard
    #    ERC-20 return, AND ALL `Alt -> Hard` disposals across EVERY router are reconciled dollar-for-dollar below!
    all_seen_tx_hashes: Set[str] = (
        set(tx_hard_out_usd_pre.keys())
        | set(tx_hard_in_usd_pre.keys())
        | set(tx_non_hard_erc20_in.keys())
        | set(tx_non_hard_erc20_out.keys())
    )
    verified_dex_self_swap_hashes: Set[str] = set()
    for txh_cand in all_seen_tx_hashes:
        h_out_c = tx_hard_out_usd_pre.get(txh_cand, 0.0)
        h_in_c = tx_hard_in_usd_pre.get(txh_cand, 0.0)
        hard_self_ok = (h_in_c >= 0.80 * h_out_c) if h_out_c > 0.0 else (h_in_c >= MIN_HARD_TOKEN_FRICTION_USD)
        if txh_cand in tx_batch_or_vm_dex_hashes:
            if hard_self_ok:
                verified_dex_self_swap_hashes.add(txh_cand)
        else:
            if hard_self_ok or tx_non_hard_erc20_in.get(txh_cand, False):
                verified_dex_self_swap_hashes.add(txh_cand)

    internal_bnb_in_by_hash: Dict[str, float] = {}
    internal_bnb_from_lending_usd = 0.0
    seasoned_vault_self_redeemed_usd = 0.0
    apx_returned_usd = 0.0
    for t in incoming_ext_int:
        if t.category == "internal":
            h_low = (t.tx_hash or "").lower()
            if h_low:
                internal_bnb_in_by_hash[h_low] = internal_bnb_in_by_hash.get(h_low, 0.0) + t.value_float
            u_int = t.value_float * snap.bnb_price_usd
            if t.from_addr.lower() in LENDING_POOL_CONTRACTS or (h_low and h_low in lending_redeem_tx_hashes):
                internal_bnb_from_lending_usd += u_int
                if t.timestamp <= seasoning_cutoff:
                    seasoned_vault_self_redeemed_usd += u_int
            elif t.from_addr.lower() == APX_V2_TRADING_DIAMOND or (h_low and h_low in apx_exit_tx_hashes):
                apx_returned_usd += u_int
                if t.timestamp <= seasoning_cutoff:
                    seasoned_vault_self_redeemed_usd += u_int
            elif h_low and h_low in zero_fee_lp_redeem_tx_hashes and t.timestamp <= seasoning_cutoff:
                seasoned_vault_self_redeemed_usd += u_int

    hard_token_out_usd_by_hash: Dict[str, float] = {}
    hard_token_in_usd_by_hash: Dict[str, float] = {}
    lending_token_redeemed_usd = 0.0
    for t in token_transfers:
        txh = (t.tx_hash or "").lower()
        frm_low = t.from_addr.lower()
        to_t_low = t.to_addr.lower()
        ca_low = t.contract_addr.lower()
        if frm_low == addr_low and to_t_low == addr_low:
            continue
        if ca_low in HARD_LIQUID_TOKENS:
            unit_usd = snap.bnb_price_usd if ca_low == BSC_WBNB else 1.0
            usd_leg = t.value_float * unit_usd
            if txh:
                if frm_low == addr_low and to_t_low != BSC_WBNB:
                    hard_token_out_usd_by_hash[txh] = hard_token_out_usd_by_hash.get(txh, 0.0) + usd_leg
                elif to_t_low == addr_low and frm_low != BSC_WBNB:
                    hard_token_in_usd_by_hash[txh] = hard_token_in_usd_by_hash.get(txh, 0.0) + usd_leg
            if to_t_low == addr_low:
                if frm_low in LENDING_POOL_CONTRACTS or (txh and txh in lending_redeem_tx_hashes):
                    lending_token_redeemed_usd += usd_leg
                    if t.timestamp <= seasoning_cutoff:
                        seasoned_vault_self_redeemed_usd += usd_leg
                elif frm_low == APX_V2_TRADING_DIAMOND or (txh and txh in apx_exit_tx_hashes):
                    apx_returned_usd += usd_leg
                    if t.timestamp <= seasoning_cutoff:
                        seasoned_vault_self_redeemed_usd += usd_leg
                elif txh and txh in zero_fee_lp_redeem_tx_hashes and t.timestamp <= seasoning_cutoff:
                    seasoned_vault_self_redeemed_usd += usd_leg

    fee_bearing_tx_count = 0
    fee_bearing_categories: Set[str] = set()
    fee_bearing_contracts: Set[str] = set()
    fee_bearing_timestamps: List[int] = []

    lending_supply_tx_count = 0
    lending_supply_contracts: Set[str] = set()
    lending_supply_timestamps: List[int] = []
    lending_supplied_usd = 0.0
    lending_receipted_supplied_usd = 0.0
    lending_unreceipted_supply_usd = 0.0
    lending_behalf_drain_usd = 0.0
    lending_tx_hashes: Set[str] = set()
    unreceipted_lending_tx_hashes: Set[str] = set()
    zero_fee_lp_supply_tx_hashes: Set[str] = set()
    unreceipted_lp_tx_hashes: Set[str] = set()
    lp_supplied_usd = 0.0
    apx_escrow_tx_hashes: Set[str] = set()
    apx_limit_or_lp_in_usd = 0.0
    apx_market_in_usd = 0.0
    last_apx_market_open_ts = 0
    last_apx_close_ts = 0
    verified_bridge_out_usd = 0.0
    dex_settlement_tx_hashes: Set[str] = set()

    zero_friction_tx_count = 0
    plain_bnb_out_total = 0.0
    protocol_settlement_tx_hashes: Set[str] = set()

    for tx in outgoing_ext:
        to_low = (tx.to_addr or "").lower()
        sel = (tx.selector or "0x")[:10].lower()
        txh = (tx.tx_hash or "").lower()

        same_tx_refund = internal_bnb_in_by_hash.get(txh, 0.0)
        net_bnb_out = max(0.0, tx.value_float - same_tx_refund)
        has_net_bnb_out = net_bnb_out >= MIN_NATIVE_BNB_FRICTION
        has_net_bnb_payout = (tx.value_float < 0.0005 and same_tx_refund >= MIN_NATIVE_BNB_FRICTION)
        hard_tok_out_usd = hard_token_out_usd_by_hash.get(txh, 0.0)
        hard_tok_in_usd = hard_token_in_usd_by_hash.get(txh, 0.0)
        has_hard_token_out_settlement = (hard_tok_out_usd >= MIN_HARD_TOKEN_FRICTION_USD) and (to_low != BSC_WBNB)

        # 1) Self-transfers, .ai minting, WBNB 1:1 wrap/unwrap, ERC20/1155 peer transfer, CTF split/merge, lending/LP redeem, APX close/cancel, or approve/checkIn -> 0 friction
        if (
            to_low == addr_low
            or to_low == SPACE_ID_AI_REGISTRY.lower()
            or to_low == BSC_WBNB
            or sel in ZERO_FRICTION_SELECTORS
            or sel in LENDING_REDEEM_SELECTORS
            or sel in ZERO_FEE_LP_REDEEM_SELECTORS
            or (to_low == APX_V2_TRADING_DIAMOND and sel in APX_V2_EXIT_OR_ADMIN_SELECTORS)
        ):
            if to_low == APX_V2_TRADING_DIAMOND and sel == "0x5177fd3b" and tx.timestamp > last_apx_close_ts:
                last_apx_close_ts = tx.timestamp
            zero_friction_tx_count += 1
            continue

        # 2) Plain native EOA transfer (selector == "0x") to non-protocol address -> NOT protocol friction!
        if sel == "0x" and to_low not in KNOWN_BSC_PROTOCOLS:
            plain_bnb_out_total += tx.value_float
            continue

        # 3) 0%-fee local LP / LimitOrder / ALP / Stake deposits (`StargateRouter.addLiquidity`, `PancakeV2.addLiquidity*`,
        #    `APX V2.openLimitOrder*` / `mintAlp*` / `stake` / `addMargin*`) NEVER earn protocol friction!
        proto_cat = KNOWN_BSC_PROTOCOLS.get(to_low)
        if proto_cat and (
            sel in ZERO_FEE_LP_ADD_SELECTORS
            or (to_low == APX_V2_TRADING_DIAMOND and sel in APX_V2_ZERO_FEE_ESCROW_ADD_SELECTORS)
        ):
            lp_leg_usd = max(
                0.0,
                tx_hard_out_usd_pre.get(txh, 0.0) - tx_hard_in_usd_pre.get(txh, 0.0),
            ) if txh else (net_bnb_out * snap.bnb_price_usd)
            if lp_leg_usd > 0.0 and txh:
                if to_low == APX_V2_TRADING_DIAMOND:
                    apx_escrow_tx_hashes.add(txh)
                    apx_limit_or_lp_in_usd += lp_leg_usd
                    if tx_non_hard_erc20_in.get(txh, False):
                        zero_fee_lp_supply_tx_hashes.add(txh)
                elif tx_non_hard_erc20_in.get(txh, False):
                    zero_fee_lp_supply_tx_hashes.add(txh)
                    lp_supplied_usd += lp_leg_usd
                else:
                    unreceipted_lp_tx_hashes.add(txh)
            zero_friction_tx_count += 1
            continue

        # 4) ONLY curated `KNOWN_BSC_PROTOCOLS` with verified method & direction-checked canonical hard-value settlement:
        #    - Non-DEX protocols (`PREDICTION_PERP`, `LENDING_YIELD_BRIDGE`) strictly require NET OUTBOUND hard value
        #      (`has_net_bnb_out` or `has_hard_token_out_settlement`), so claims/cancels/redemptions NEVER farm +1 friction!
        #    - DEX swaps additionally allow selling a real outbound non-hard ERC-20 (`tx_non_hard_erc20_out`) for >=0.002 BNB or >=$1 hard token.
        stargate_method_ok = (to_low != STARGATE_ROUTER_BSC) or (sel in STARGATE_BRIDGE_SWAP_SELECTORS)
        apx_method_ok = (to_low != APX_V2_TRADING_DIAMOND) or (sel in APX_V2_MARKET_TRADE_SELECTORS)
        dex_return_ok = (proto_cat != "DEX_SWAP") or bool(txh and txh in verified_dex_self_swap_hashes)
        has_dex_alt_sale_payout = (
            proto_cat == "DEX_SWAP"
            and bool(txh and tx_non_hard_erc20_out.get(txh, False))
            and (has_net_bnb_payout or hard_tok_in_usd >= MIN_HARD_TOKEN_FRICTION_USD)
        )
        has_canonical_settlement = has_net_bnb_out or has_hard_token_out_settlement or has_dex_alt_sale_payout
        if to_low in LENDING_POOL_CONTRACTS:
            # Reconcile ALL positive hard-liquid lending outflows (`supply_leg_usd > 0`) without any `$1.0` or
            # `0.002 BNB` floor so split sub-threshold `Venus.mintBehalf(COLLECTOR_EOA)` / `Kinza.supply(..., EOA)`
            # calls NEVER evade `lending_tx_hashes`, `lending_behalf_drain_usd`, or `unredeemed_zero_fee_vault_usd`!
            supply_leg_usd = max(
                0.0,
                tx_hard_out_usd_pre.get(txh, 0.0) - tx_hard_in_usd_pre.get(txh, 0.0),
            ) if txh else 0.0
            if supply_leg_usd > 0.0 and txh:
                is_canonical_lending_supply = (
                    supply_leg_usd >= MIN_HARD_TOKEN_FRICTION_USD and has_canonical_settlement
                )
                lending_tx_hashes.add(txh)
                if is_canonical_lending_supply:
                    protocol_settlement_tx_hashes.add(txh)
                if sel in LENDING_BEHALF_SELECTORS:
                    lending_behalf_drain_usd += supply_leg_usd
                    unreceipted_lending_tx_hashes.add(txh)
                    zero_friction_tx_count += 1
                else:
                    lending_supplied_usd += supply_leg_usd
                    has_self_receipt = (
                        to_low == VENUS_COMPTROLLER
                        and sel != "0x"
                        and sel not in ZERO_FRICTION_SELECTORS
                    ) or bool(tx_non_hard_erc20_in.get(txh, False))
                    if has_self_receipt:
                        lending_receipted_supplied_usd += supply_leg_usd
                    else:
                        lending_unreceipted_supply_usd += supply_leg_usd
                        unreceipted_lending_tx_hashes.add(txh)
                    if is_canonical_lending_supply:
                        lending_supply_tx_count += 1
                        lending_supply_contracts.add(to_low)
                        if tx.timestamp > 0:
                            lending_supply_timestamps.append(tx.timestamp)
                    else:
                        zero_friction_tx_count += 1
            else:
                zero_friction_tx_count += 1
            continue
        if (
            proto_cat
            and stargate_method_ok
            and apx_method_ok
            and dex_return_ok
            and has_canonical_settlement
        ):
            if txh:
                protocol_settlement_tx_hashes.add(txh)
            settled_out_usd = max(
                0.0,
                tx_hard_out_usd_pre.get(txh, 0.0) - tx_hard_in_usd_pre.get(txh, 0.0),
            ) if txh else (net_bnb_out * snap.bnb_price_usd + hard_tok_out_usd)
            if proto_cat == "DEX_SWAP" and txh:
                dex_settlement_tx_hashes.add(txh)
            if to_low == APX_V2_TRADING_DIAMOND and settled_out_usd > 0.0:
                apx_market_in_usd += settled_out_usd
                if tx.timestamp > last_apx_market_open_ts:
                    last_apx_market_open_ts = tx.timestamp
            if to_low in (STARGATE_ROUTER_BSC, RELAY_DEPOSITORY_BSC) and settled_out_usd > 0.0:
                verified_bridge_out_usd += settled_out_usd
            fee_bearing_categories.add(proto_cat)
            fee_bearing_tx_count += 1
            fee_bearing_contracts.add(to_low)
            if tx.timestamp > 0:
                fee_bearing_timestamps.append(tx.timestamp)
        else:
            if to_low not in KNOWN_BSC_PROTOCOLS and net_bnb_out > 0:
                plain_bnb_out_total += net_bnb_out
            zero_friction_tx_count += 1

    # Also recognize EIP-712 signed CLOB order fills on Predict.fun CTFExchange where >= $1 stablecoin
    # moves directly from wallet -> PREDICT_FUN_EXCHANGES via operator `matchOrders` (`txh not in outgoing_tx_hashes`),
    # as well as direct hard-token bridge deposits into curated cross-chain bridge depositories (`Relay: Depository`).
    seen_clob_hashes: Set[str] = set()
    direct_bridge_depositories: Set[str] = {"0x4cd00e387622c35bddb9b4c962c136462338bc31"}
    for t in token_transfers:
        txh = (t.tx_hash or "").lower()
        to_t_low = t.to_addr.lower()
        t_sel = (t.selector or "0x")[:10].lower()
        ca_low = t.contract_addr.lower()
        if (
            t.from_addr.lower() == addr_low
            and to_t_low in PREDICT_FUN_EXCHANGES
            and ca_low in STABLECOIN_SET
            and t.value_float >= MIN_HARD_TOKEN_FRICTION_USD
            and t_sel not in ZERO_FRICTION_SELECTORS
            and t_sel != "0x"
            and txh not in outgoing_tx_hashes
            and txh not in seen_clob_hashes
        ):
            if txh:
                seen_clob_hashes.add(txh)
                protocol_settlement_tx_hashes.add(txh)
            fee_bearing_categories.add("PREDICTION_PERP")
            fee_bearing_tx_count += 1
            fee_bearing_contracts.add(to_t_low)
            if t.timestamp > 0:
                fee_bearing_timestamps.append(t.timestamp)
        elif (
            t.from_addr.lower() == addr_low
            and to_t_low in direct_bridge_depositories
            and ca_low in HARD_LIQUID_TOKENS
            and (t.value_float * (snap.bnb_price_usd if ca_low == BSC_WBNB else 1.0)) >= MIN_HARD_TOKEN_FRICTION_USD
            and txh not in protocol_settlement_tx_hashes
            and txh not in seen_clob_hashes
        ):
            leg_br_usd = t.value_float * (snap.bnb_price_usd if ca_low == BSC_WBNB else 1.0)
            verified_bridge_out_usd += leg_br_usd
            if txh:
                seen_clob_hashes.add(txh)
                protocol_settlement_tx_hashes.add(txh)
                if txh in outgoing_tx_hashes and zero_friction_tx_count > 0:
                    zero_friction_tx_count -= 1
            fee_bearing_categories.add("LENDING_YIELD_BRIDGE")
            fee_bearing_tx_count += 1
            fee_bearing_contracts.add(to_t_low)
            if t.timestamp > 0:
                fee_bearing_timestamps.append(t.timestamp)
        elif (
            t.from_addr.lower() == addr_low
            and to_t_low in direct_bridge_depositories
            and ca_low in HARD_LIQUID_TOKENS
            and txh in seen_clob_hashes
        ):
            verified_bridge_out_usd += t.value_float * (snap.bnb_price_usd if ca_low == BSC_WBNB else 1.0)
        elif (
            t.from_addr.lower() == addr_low
            and to_t_low in LENDING_POOL_CONTRACTS
            and ca_low in HARD_LIQUID_TOKENS
            and txh
            and txh not in outgoing_tx_hashes
            and txh not in lending_tx_hashes
        ):
            # Reconcile direct/operator-initiated ERC-20 hard-liquid outflows to lending pools (no matching outer
            # `outgoing_ext` tx) into the lending ledger once so they are never missed and never double-counted.
            supply_leg_usd = max(
                0.0,
                tx_hard_out_usd_pre.get(txh, 0.0) - tx_hard_in_usd_pre.get(txh, 0.0),
            )
            if supply_leg_usd > 0.0:
                lending_tx_hashes.add(txh)
                if t_sel in LENDING_BEHALF_SELECTORS:
                    lending_behalf_drain_usd += supply_leg_usd
                    unreceipted_lending_tx_hashes.add(txh)
                else:
                    lending_supplied_usd += supply_leg_usd
                    has_self_receipt = (
                        t_sel not in ZERO_FRICTION_SELECTORS
                        and bool(tx_non_hard_erc20_in.get(txh, False))
                    )
                    if has_self_receipt:
                        lending_receipted_supplied_usd += supply_leg_usd
                    else:
                        lending_unreceipted_supply_usd += supply_leg_usd
                        unreceipted_lending_tx_hashes.add(txh)

    # Track lending & 0%-fee LP receipt token CAs (e.g. `kUSDT`, `vUSDT`, `vBNB`, `S*USDT`, `Cake-LP`) and
    # reconcile ANY burn (`to == 0x0000`) or outbound transfer BEFORE evaluating `lending_is_wash_roundtrip`!
    receipted_lending_hashes = lending_tx_hashes - unreceipted_lending_tx_hashes
    lending_receipt_token_cas: Set[str] = set(LENDING_POOL_CONTRACTS - {VENUS_COMPTROLLER})
    lp_receipt_token_cas: Set[str] = set()
    lending_rcpt_qty: Dict[str, float] = {}
    lending_rcpt_usd: Dict[str, float] = {}
    lp_rcpt_qty: Dict[str, float] = {}
    lp_rcpt_usd: Dict[str, float] = {}
    counted_lending_rcpt_tx: Set[Tuple[str, str]] = set()
    counted_lp_rcpt_tx: Set[Tuple[str, str]] = set()

    for t in token_transfers:
        txh_r = (t.tx_hash or "").lower()
        ca_r = t.contract_addr.lower()
        if (
            txh_r
            and t.to_addr.lower() == addr_low
            and t.from_addr.lower() != addr_low
            and ca_r not in HARD_LIQUID_TOKENS
        ):
            net_h_spent_r = max(0.0, tx_hard_out_usd_pre.get(txh_r, 0.0) - tx_hard_in_usd_pre.get(txh_r, 0.0))
            if txh_r in receipted_lending_hashes:
                lending_receipt_token_cas.add(ca_r)
                lending_rcpt_qty[ca_r] = lending_rcpt_qty.get(ca_r, 0.0) + t.value_float
                if (txh_r, ca_r) not in counted_lending_rcpt_tx:
                    counted_lending_rcpt_tx.add((txh_r, ca_r))
                    lending_rcpt_usd[ca_r] = lending_rcpt_usd.get(ca_r, 0.0) + net_h_spent_r
            elif txh_r in zero_fee_lp_supply_tx_hashes:
                lp_receipt_token_cas.add(ca_r)
                lp_rcpt_qty[ca_r] = lp_rcpt_qty.get(ca_r, 0.0) + t.value_float
                if (txh_r, ca_r) not in counted_lp_rcpt_tx:
                    counted_lp_rcpt_tx.add((txh_r, ca_r))
                    lp_rcpt_usd[ca_r] = lp_rcpt_usd.get(ca_r, 0.0) + net_h_spent_r

    lending_receipt_exited_usd = 0.0
    lp_receipt_exited_usd = 0.0
    logged_lending_exit_hashes: Set[str] = set()
    for t in token_transfers:
        txh_r = (t.tx_hash or "").lower()
        ca_r = t.contract_addr.lower()
        if t.from_addr.lower() == addr_low and t.to_addr.lower() != addr_low:
            if ca_r in lending_receipt_token_cas and lending_rcpt_qty.get(ca_r, 0.0) > 0.0:
                if txh_r:
                    logged_lending_exit_hashes.add(txh_r)
                lending_receipt_exited_usd += lending_rcpt_usd.get(ca_r, 0.0) * min(
                    1.0, t.value_float / lending_rcpt_qty[ca_r]
                )
            elif ca_r in lp_receipt_token_cas and lp_rcpt_qty.get(ca_r, 0.0) > 0.0:
                lp_receipt_exited_usd += lp_rcpt_usd.get(ca_r, 0.0) * min(
                    1.0, t.value_float / lp_rcpt_qty[ca_r]
                )
    lending_receipt_exited_usd = min(lending_receipted_supplied_usd, lending_receipt_exited_usd)
    lp_receipt_exited_usd = min(lp_supplied_usd, lp_receipt_exited_usd)

    lending_redeemed_usd = internal_bnb_from_lending_usd + lending_token_redeemed_usd
    # Exact Dollar-for-Dollar Lending Receipt Reconciliation (immune to `0.01 USDT` self-redeem AND `withdraw(..., COLLECTOR_EOA)`!):
    # 1) Explicit `mintBehalf` / `repayBorrowBehalf` (`LENDING_BEHALF_SELECTORS`) is unconditionally 100% third-party drain.
    # 2) Self-redemptions (`lending_redeemed_usd`) reconcile against `lending_receipted_supplied_usd` FIRST; third-party
    #    `withdraw(asset, amt, COLLECTOR_EOA)` (`lending_receipt_exited_usd` with `0` hard return to `self`) NEVER offsets
    #    unreceipted supplies, ALWAYS triggers `lending_is_wash_roundtrip`, and flows into `swept_acquired_alt_usd`!
    redeem_left_for_unreceipted = max(0.0, lending_redeemed_usd - lending_receipted_supplied_usd)
    unreconciled_unreceipted_usd = max(0.0, lending_unreceipted_supply_usd - redeem_left_for_unreceipted)
    valid_lending_supplied_usd = max(0.0, lending_supplied_usd - unreconciled_unreceipted_usd)

    unlogged_lending_exit_drain_usd = 0.0
    if any(
        h_ex not in logged_lending_exit_hashes and tx_hard_in_usd_pre.get(h_ex, 0.0) <= 0.0
        for h_ex in lending_active_exit_tx_hashes
    ):
        unlogged_lending_exit_drain_usd = max(
            0.0,
            valid_lending_supplied_usd - max(lending_redeemed_usd, lending_receipt_exited_usd),
        )

    lending_third_party_drain_usd = (
        lending_behalf_drain_usd + unreconciled_unreceipted_usd + unlogged_lending_exit_drain_usd
    )
    effective_lending_exit_usd = max(lending_redeemed_usd, lending_receipt_exited_usd) + unlogged_lending_exit_drain_usd

    lending_is_wash_roundtrip = (
        lending_supply_tx_count > 0
        and valid_lending_supplied_usd > 0.0
        and (
            effective_lending_exit_usd >= 0.50 * valid_lending_supplied_usd
            or (valid_lending_supplied_usd - effective_lending_exit_usd) < MIN_HARD_TOKEN_FRICTION_USD
        )
    )

    hit_categories: Set[str] = set(fee_bearing_categories)
    economic_contracts: Set[str] = set(fee_bearing_contracts)
    economic_timestamps: List[int] = list(fee_bearing_timestamps)
    real_economic_tx_count = fee_bearing_tx_count

    if lending_supply_tx_count > 0:
        if lending_is_wash_roundtrip:
            zero_friction_tx_count += lending_supply_tx_count
            if not history_unverified:
                risk_flags.append("ZERO_FEE_LENDING_WASH_ROUNDTRIP")
        elif (valid_lending_supplied_usd - lending_redeemed_usd) < MIN_HARD_TOKEN_FRICTION_USD:
            zero_friction_tx_count += lending_supply_tx_count
        else:
            hit_categories.add("LENDING_YIELD_BRIDGE")
            real_economic_tx_count += lending_supply_tx_count
            economic_contracts.update(lending_supply_contracts)
            economic_timestamps.extend(lending_supply_timestamps)

    econ_active_days = len({ts // 86400 for ts in economic_timestamps})
    econ_span_sec = (max(economic_timestamps) - min(economic_timestamps)) if len(economic_timestamps) >= 2 else 0
    if len(economic_contracts) >= 3 and fee_bearing_tx_count >= 1 and (econ_active_days >= 2 or econ_span_sec >= 3600):
        hit_categories.add("ECOSYSTEM_DIVERSITY")

    effective_tx_count = max(snap.tx_count, len(outgoing_ext))

    # -------------------------------------------------------------------------
    # Temporal Span & Active Days (Computed early for Cross-Dimensional Guards)
    # -------------------------------------------------------------------------
    ts_sorted = sorted(t.timestamp for t in outgoing_ext if t.timestamp > 0)
    if len(ts_sorted) >= 2:
        span_seconds = ts_sorted[-1] - ts_sorted[0]
        span_days = span_seconds / 86400.0
        active_days = len({ts // 86400 for ts in ts_sorted})
    else:
        span_seconds = 0
        span_days = 0.0
        active_days = 1 if effective_tx_count >= 1 and not history_unverified else 0

    # -------------------------------------------------------------------------
    # Exact 72-Hour Balance-Sheet Conservation & Continuous Minimum Balance
    # -------------------------------------------------------------------------
    # Portfolio tracked: `S(t) = (bnb(t) + wbnb(t)) * price + usdt(t) + usdc(t) + fdusd(t) + usd1(t) + dai(t) + busd(t)`.
    # Crucial WETH9 Conservation Invariant: On BSC `WBNB` (`0xbb4cdb...`), `deposit()` emits `Deposit` (NOT ERC-20
    # `Transfer`) and `withdraw()` emits `Withdrawal` + internal BNB (NOT ERC-20 `Transfer`). Because BOTH `bnb_balance`
    # and `wbnb_balance` are included in `retained_usd`, 1:1 native<->WBNB wraps/unwraps (`addr <-> BSC_WBNB`) leave
    # `S(t)` strictly invariant (`delta == 0`) and MUST NOT create phantom outflows/inflows in `tx_net_delta_72h`!
    zero_addr = "0x0000000000000000000000000000000000000000"
    liquid_bnb_usd = (snap.bnb_balance + snap.wbnb_balance) * snap.bnb_price_usd
    liquid_stable_usd = (
        snap.usdt_balance
        + snap.usdc_balance
        + snap.fdusd_balance
        + snap.usd1_balance
        + snap.dai_balance
        + snap.busd_balance
    )
    retained_usd = liquid_bnb_usd + liquid_stable_usd

    tx_net_delta_72h: Dict[str, float] = {}
    tx_ts_72h: Dict[str, int] = {}
    tx_gross_in_all: Dict[str, float] = {}
    tx_gross_out_all: Dict[str, float] = {}

    for idx_ev, t in enumerate(snap.transfers):
        if t.status != 1 or t.value_float <= 0:
            continue
        frm_l = t.from_addr.lower()
        to_l = t.to_addr.lower()
        ca_l = t.contract_addr.lower()
        if frm_l == addr_low and to_l == addr_low:
            continue

        # Skip 1:1 internal `BNB <-> WBNB` state switches (`deposit()` / `withdraw()`) so `S(t)` is 100% conserved
        if t.category in ("external", "internal") and (
            (frm_l == addr_low and to_l == BSC_WBNB) or (frm_l == BSC_WBNB and to_l == addr_low)
        ):
            continue
        if t.category == "20" and ca_l == BSC_WBNB and (frm_l == zero_addr or to_l == zero_addr):
            continue

        leg_usd = 0.0
        if t.category in ("external", "internal"):
            leg_usd = t.value_float * snap.bnb_price_usd
        elif t.category == "20" and ca_l in HARD_LIQUID_TOKENS:
            leg_usd = t.value_float * (snap.bnb_price_usd if ca_l == BSC_WBNB else 1.0)
        else:
            continue

        txk = (t.tx_hash or f"_ev_{idx_ev}").lower()
        if to_l == addr_low:
            tx_gross_in_all[txk] = tx_gross_in_all.get(txk, 0.0) + leg_usd
        elif frm_l == addr_low:
            tx_gross_out_all[txk] = tx_gross_out_all.get(txk, 0.0) + leg_usd
        else:
            continue

        if t.timestamp > seasoning_cutoff:
            if to_l == addr_low:
                tx_net_delta_72h[txk] = tx_net_delta_72h.get(txk, 0.0) + leg_usd
            elif frm_l == addr_low:
                tx_net_delta_72h[txk] = tx_net_delta_72h.get(txk, 0.0) - leg_usd
            if t.timestamp > tx_ts_72h.get(txk, 0):
                tx_ts_72h[txk] = t.timestamp

    running_bal_72h = retained_usd
    min_bal_72h = retained_usd
    unseasoned_net_inflow_72h_usd = 0.0
    # Pessimistic intra-block tie-break: at identical timestamps, undo positive inflows (`delta > 0`) BEFORE outflows
    for txk in sorted(
        tx_net_delta_72h.keys(),
        key=lambda k: (tx_ts_72h.get(k, 0), 1 if tx_net_delta_72h[k] > 0 else 0, k),
        reverse=True,
    ):
        delta_u = tx_net_delta_72h[txk]
        if delta_u > 0:
            unseasoned_net_inflow_72h_usd += delta_u
        running_bal_72h -= delta_u
        if running_bal_72h < min_bal_72h:
            min_bal_72h = running_bal_72h

    if history_unverified or snap.recent_window_truncated:
        seasoned_retained_usd = 0.0
        if snap.recent_window_truncated and not history_unverified:
            risk_flags.append("RECENT_72H_WINDOW_EVENT_FLOOD_TRUNCATED")
    else:
        seasoned_retained_usd = max(0.0, min(retained_usd, min_bal_72h))
    seasoned_bal_equiv_bnb = seasoned_retained_usd / max(snap.bnb_price_usd, 1.0)

    # Zero historical-bridge / off-chain lockup backdoors: ONLY verified 72h continuous BSC liquid balance counts!
    effective_seasoned_usd = seasoned_retained_usd
    effective_seasoned_bnb = seasoned_bal_equiv_bnb

    # Single-Source-of-Truth Funding Envelope: Identical predicate & candidate bounds as `_extract_candidate_funders`
    # so `PullVault.claim()` (even with `1e12 wei` BNB out) is 100% audited AND reconciled symmetrically!
    funder_low = (snap.funder_address or "").lower()
    (
        external_funding_inflows,
        external_hard_token_inflows,
        first_in_env,
        sec_cands_env,
        tok_cands_env,
    ) = _extract_external_funding_envelope(
        addr_low=addr_low,
        bnb_price_usd=snap.bnb_price_usd,
        transfers=snap.transfers,
        explicit_primary_funder=funder_low,
    )

    primary_bnb_funder = funder_low or (first_in_env.from_addr.lower() if first_in_env else "")
    audited_bnb_funders: Set[str] = (
        ({primary_bnb_funder} if primary_bnb_funder else set())
        | ({first_in_env.from_addr.lower()} if first_in_env else set())
        | {c[0] for c in sec_cands_env}
    )
    audited_tok_funders: Set[str] = {c[0] for c in tok_cands_env}

    credited_bnb_inflows = [t for t in external_funding_inflows if t.from_addr.lower() in audited_bnb_funders]
    credited_tok_inflows = [t for t in external_hard_token_inflows if t.from_addr.lower() in audited_tok_funders]

    # Griefing-Immune 72h Smurf Deduction: `min_bal_72h` ALREADY stripped all inflows with `t.timestamp > seasoning_cutoff`!
    # Deduct ONLY pre-72h (`t.timestamp <= seasoning_cutoff`) unaudited micro-smurfed inflows (AND any unbacked inbound
    # `onBehalfOf` / `mintBehalf` / `addLiquidity(_to=spoke)` vault withdrawals exceeding `105%` of self-supplies)
    # so `d(effective_seasoned_usd)/dG == 0` for BOTH pre-72h AND recent `<72h` unsolicited dust griefing!
    total_self_supplied_vault_usd = (
        valid_lending_supplied_usd + lp_supplied_usd + apx_limit_or_lp_in_usd + apx_market_in_usd
    )
    unbacked_seasoned_vault_inflow_usd = (
        max(0.0, seasoned_vault_self_redeemed_usd - 1.05 * total_self_supplied_vault_usd)
        if seasoned_vault_self_redeemed_usd > (1.05 * total_self_supplied_vault_usd + 0.50)
        else 0.0
    )

    seasoned_unverified_smurf_usd = (
        sum(
            t.value_float * snap.bnb_price_usd
            for t in external_funding_inflows
            if t.from_addr.lower() not in audited_bnb_funders and t.timestamp <= seasoning_cutoff
        )
        + sum(
            t.value_float * (snap.bnb_price_usd if t.contract_addr.lower() == BSC_WBNB else 1.0)
            for t in external_hard_token_inflows
            if t.from_addr.lower() not in audited_tok_funders and t.timestamp <= seasoning_cutoff
        )
        + unbacked_seasoned_vault_inflow_usd
    )
    if seasoned_unverified_smurf_usd > 0.0:
        effective_seasoned_usd = max(0.0, effective_seasoned_usd - seasoned_unverified_smurf_usd)
        effective_seasoned_bnb = effective_seasoned_usd / max(snap.bnb_price_usd, 1.0)

    total_ext_bnb_in = sum(t.value_float for t in credited_bnb_inflows)
    seasoned_ext_bnb_in = sum(
        t.value_float for t in credited_bnb_inflows if 0 < t.timestamp <= seasoning_cutoff
    )
    unseasoned_ext_bnb_in = sum(
        t.value_float for t in external_funding_inflows if t.timestamp > seasoning_cutoff
    )
    ext_hard_tok_all_usd = sum(
        t.value_float * (snap.bnb_price_usd if t.contract_addr.lower() == BSC_WBNB else 1.0)
        for t in credited_tok_inflows
    )
    ext_in_all_usd = total_ext_bnb_in * snap.bnb_price_usd + ext_hard_tok_all_usd
    seasoned_unique_funders = {
        t.from_addr.lower()
        for t in credited_bnb_inflows
        if t.value_float >= 0.001 and 0 < t.timestamp <= seasoning_cutoff
    }

    all_ext_funder_addrs: Set[str] = (
        ({funder_low} if funder_low else set())
        | {t.from_addr.lower() for t in external_funding_inflows if t.from_addr}
        | {t.from_addr.lower() for t in external_hard_token_inflows if t.from_addr}
    )

    tx_has_direct_proto_hard_out: Set[str] = set()
    tx_unknown_hard_out_by_to: Dict[str, Dict[str, float]] = {}
    for t in token_transfers:
        if (
            t.from_addr.lower() == addr_low
            and t.to_addr.lower() != addr_low
            and t.to_addr.lower() != BSC_WBNB
            and t.contract_addr.lower() in HARD_LIQUID_TOKENS
        ):
            h_u = (t.tx_hash or "").lower()
            to_u = t.to_addr.lower()
            if not h_u:
                continue
            u_amt = t.value_float * (snap.bnb_price_usd if t.contract_addr.lower() == BSC_WBNB else 1.0)
            if to_u in KNOWN_BSC_PROTOCOLS:
                tx_has_direct_proto_hard_out.add(h_u)
            else:
                per_to = tx_unknown_hard_out_by_to.setdefault(h_u, {})
                per_to[to_u] = per_to.get(to_u, 0.0) + u_amt

    def _is_verified_protocol_outflow(to_addr_l: str, tx_hash_l: str, leg_usd: float = 0.0) -> bool:
        if not tx_hash_l or tx_hash_l in tx_ctf_split_hashes or tx_hash_l in unreceipted_lp_tx_hashes:
            return False
        if to_addr_l in LENDING_POOL_CONTRACTS or tx_hash_l in lending_tx_hashes:
            # All positive lending outflows (including Aave V3/Kinza `USDT -> kUSDT` aToken & direct ERC-20 flows)
            # are reconciled dollar-for-dollar via `lending_third_party_drain_usd` + `swept_acquired_alt_usd` +
            # `unredeemed_zero_fee_vault_usd` so they are never missed and never double-counted.
            return tx_hash_l in lending_tx_hashes and to_addr_l not in all_ext_funder_addrs
        if to_addr_l == STARGATE_ROUTER_BSC:
            return tx_hash_l in protocol_settlement_tx_hashes or tx_hash_l in zero_fee_lp_supply_tx_hashes
        if to_addr_l == APX_V2_TRADING_DIAMOND:
            return tx_hash_l in protocol_settlement_tx_hashes or tx_hash_l in apx_escrow_tx_hashes
        p_cat = KNOWN_BSC_PROTOCOLS.get(to_addr_l)
        if p_cat == "DEX_SWAP":
            if tx_hash_l not in verified_dex_self_swap_hashes:
                return False
            if leg_usd > 0.0:
                return tx_hash_l in protocol_settlement_tx_hashes or tx_hash_l in zero_fee_lp_supply_tx_hashes
            return (
                tx_hash_l in protocol_settlement_tx_hashes
                or tx_hash_l in zero_fee_lp_supply_tx_hashes
                or tx_hard_out_usd_pre.get(tx_hash_l, 0.0) == 0.0
            )
        if p_cat is not None:
            return tx_hash_l in protocol_settlement_tx_hashes
        if not (
            (tx_hash_l in protocol_settlement_tx_hashes or tx_hash_l in zero_fee_lp_supply_tx_hashes)
            and tx_hash_l in verified_dex_self_swap_hashes
            and to_addr_l not in all_ext_funder_addrs
        ):
            return False
        tot_tx_out = tx_hard_out_usd_pre.get(tx_hash_l, 0.0)
        if tot_tx_out <= 0.0 or leg_usd <= 0.0:
            return True
        # Guard against aggregator `feeReceivers = [COLLECTOR_EOA]` or multi-recipient ERC-20 split drains:
        if tx_hash_l in tx_has_direct_proto_hard_out:
            return leg_usd <= 0.03 * tot_tx_out
        per_to = tx_unknown_hard_out_by_to.get(tx_hash_l, {})
        if not per_to:
            return True
        primary_pool_to = max(per_to.items(), key=lambda kv: kv[1])[0]
        if to_addr_l == primary_pool_to:
            other_sum = sum(v for k, v in per_to.items() if k != primary_pool_to)
            return other_sum <= 0.03 * tot_tx_out
        return per_to.get(to_addr_l, 0.0) <= 0.03 * tot_tx_out

    unverified_dex_tx_hashes: Set[str] = set()
    non_protocol_bnb_out = 0.0
    for t in snap.transfers:
        if (
            t.status == 1
            and t.category in ("external", "internal")
            and t.from_addr.lower() == addr_low
            and t.to_addr.lower() != addr_low
            and t.to_addr.lower() != BSC_WBNB
        ):
            txh_l = (t.tx_hash or "").lower()
            to_l = t.to_addr.lower()
            u_b = t.value_float * snap.bnb_price_usd
            if not _is_verified_protocol_outflow(to_l, txh_l, u_b):
                non_protocol_bnb_out += t.value_float
                if KNOWN_BSC_PROTOCOLS.get(to_l) == "DEX_SWAP" and txh_l:
                    unverified_dex_tx_hashes.add(txh_l)

    non_protocol_hard_tok_out_usd = 0.0
    for t in token_transfers:
        if (
            t.from_addr.lower() == addr_low
            and t.to_addr.lower() != addr_low
            and t.to_addr.lower() != BSC_WBNB
            and t.contract_addr.lower() in HARD_LIQUID_TOKENS
        ):
            txh_l = (t.tx_hash or "").lower()
            to_l = t.to_addr.lower()
            u_t = t.value_float * (snap.bnb_price_usd if t.contract_addr.lower() == BSC_WBNB else 1.0)
            if not _is_verified_protocol_outflow(to_l, txh_l, u_t):
                non_protocol_hard_tok_out_usd += u_t
                if KNOWN_BSC_PROTOCOLS.get(to_l) == "DEX_SWAP" and txh_l:
                    unverified_dex_tx_hashes.add(txh_l)

    # Deduct any partial `<80%` hard refund (`e.g. refundETH()`) already returned in `unverified_dex_tx_hashes`
    partial_dex_refund_usd = sum(
        min(tx_hard_out_usd_pre.get(h_u, 0.0), tx_hard_in_usd_pre.get(h_u, 0.0))
        for h_u in unverified_dex_tx_hashes
    )

    (
        swept_acquired_alt_usd,
        swept_dex_alt_usd,
        swept_acquired_alt_by_to,
        revoked_dex_cnt,
    ) = _reconcile_alt_and_receipt_disposals(
        addr_low=addr_low,
        token_transfers=token_transfers,
        all_seen_tx_hashes=all_seen_tx_hashes,
        tx_hard_out_usd_pre=tx_hard_out_usd_pre,
        tx_hard_in_usd_pre=tx_hard_in_usd_pre,
        tx_non_hard_erc20_in=tx_non_hard_erc20_in,
        tx_batch_or_vm_dex_hashes=tx_batch_or_vm_dex_hashes,
        unverified_dex_tx_hashes=unverified_dex_tx_hashes,
        unreceipted_lending_tx_hashes=unreceipted_lending_tx_hashes,
        unreceipted_lp_tx_hashes=unreceipted_lp_tx_hashes,
        dex_settlement_tx_hashes=dex_settlement_tx_hashes,
        lending_receipt_token_cas=lending_receipt_token_cas,
        lp_receipt_token_cas=lp_receipt_token_cas,
        lending_redeem_tx_hashes=lending_redeem_tx_hashes,
        zero_fee_lp_redeem_tx_hashes=zero_fee_lp_redeem_tx_hashes,
        apx_exit_tx_hashes=apx_exit_tx_hashes,
        is_verified_outflow_fn=_is_verified_protocol_outflow,
    )
    if revoked_dex_cnt > 0:
        fee_bearing_tx_count = max(0, fee_bearing_tx_count - revoked_dex_cnt)
        real_economic_tx_count = max(0, real_economic_tx_count - revoked_dex_cnt)
        zero_friction_tx_count += revoked_dex_cnt

    non_protocol_out_usd = (
        max(
            0.0,
            non_protocol_bnb_out * snap.bnb_price_usd + non_protocol_hard_tok_out_usd - partial_dex_refund_usd,
        )
        + swept_acquired_alt_usd
        + lending_third_party_drain_usd
    )

    verified_dex_hard_out_usd = sum(tx_hard_out_usd_pre.get(h_d, 0.0) for h_d in dex_settlement_tx_hashes)
    verified_dex_hard_in_usd = sum(tx_hard_in_usd_pre.get(h_d, 0.0) for h_d in dex_settlement_tx_hashes)
    unrecovered_dex_alt_usd = max(
        0.0,
        verified_dex_hard_out_usd - verified_dex_hard_in_usd - swept_dex_alt_usd,
    )
    # 0%-fee local lending (`Kinza`/`Venus`), LP (`Stargate.addLiquidity`/`PancakeV2.addLiquidity`), and local perp/limit
    # escrows (`APX V2` `openLimitOrder*` / `mintAlp*` / `stake` / unclosed `openMarketTrade*`) can be canceled or closed
    # on BSC immediately AFTER `attest()`; therefore unredeemed local vaults NEVER satisfy Track B commitment!
    unredeemed_apx_limit_usd = max(0.0, apx_limit_or_lp_in_usd - apx_returned_usd)
    rem_apx_return_usd = max(0.0, apx_returned_usd - apx_limit_or_lp_in_usd)
    apx_market_closed = last_apx_market_open_ts > 0 and last_apx_close_ts >= last_apx_market_open_ts
    unclosed_apx_market_usd = (
        0.0 if (apx_market_in_usd <= 0.0 or apx_market_closed) else max(0.0, apx_market_in_usd - rem_apx_return_usd)
    )
    unredeemed_zero_fee_vault_usd = (
        max(0.0, valid_lending_supplied_usd - effective_lending_exit_usd)
        + max(0.0, lp_supplied_usd - lp_receipt_exited_usd)
        + unredeemed_apx_limit_usd
        + unclosed_apx_market_usd
    )
    out_to_funder_usd = 0.0
    if all_ext_funder_addrs:
        out_to_funder_usd = (
            sum(
                t.value_float * snap.bnb_price_usd
                for t in snap.transfers
                if t.status == 1
                and t.category in ("external", "internal")
                and t.from_addr.lower() == addr_low
                and t.to_addr.lower() in all_ext_funder_addrs
            )
            + sum(
                t.value_float * (snap.bnb_price_usd if t.contract_addr.lower() == BSC_WBNB else 1.0)
                for t in token_transfers
                if t.from_addr.lower() == addr_low
                and t.to_addr.lower() in all_ext_funder_addrs
                and t.contract_addr.lower() in HARD_LIQUID_TOKENS
            )
            + sum(swept_acquired_alt_by_to.get(fa, 0.0) for fa in all_ext_funder_addrs)
        )

    # -------------------------------------------------------------------------
    # D1: Funding Provenance, Dual-Track Qualification & Anti-Cluster/Relay Tree (Max 30)
    # -------------------------------------------------------------------------
    first_bnb = snap.first_funding_bnb
    first_sel = (snap.first_funding_selector or "0x")[:10].lower()
    first_ts = snap.first_funding_timestamp
    if first_ts == 0 and external_funding_inflows:
        first_ts = external_funding_inflows[0].timestamp

    outbound_erc20_cas: Set[str] = {
        t.contract_addr.lower()
        for t in token_transfers
        if t.from_addr.lower() == addr_low and t.to_addr.lower() != addr_low and t.value_float > 0
    }
    any_disperse_inflow = any(
        (
            t.from_addr.lower() in BATCH_DISPERSE_CONTRACTS
            or (t.selector or "0x")[:10].lower() in BATCH_DISPERSE_SELECTORS
        )
        and (
            (
                t.value_float
                * (
                    snap.bnb_price_usd
                    if (t.category in ("external", "internal") or t.contract_addr.lower() == BSC_WBNB)
                    else 1.0
                )
            )
            >= 0.50
            or retained_usd < 50.0
            or t.contract_addr.lower() in outbound_erc20_cas
        )
        for t in list(external_funding_inflows) + list(external_hard_token_inflows)
    ) or any(
        t.to_addr.lower() == addr_low
        and t.contract_addr.lower() in outbound_erc20_cas
        and (
            t.from_addr.lower() in BATCH_DISPERSE_CONTRACTS
            or (t.selector or "0x")[:10].lower() in BATCH_DISPERSE_SELECTORS
        )
        for t in token_transfers
    )
    is_batch_disperse = (
        funder_low in BATCH_DISPERSE_CONTRACTS
        or first_sel in BATCH_DISPERSE_SELECTORS
        or any_disperse_inflow
        or (snap.first_funding_category == "internal" and 0 < first_bnb < 0.005)
    )
    same_amt_cnt = max(snap.funder_same_dust_50, snap.funder_same_amount_50)
    funder_eoa_denom = snap.funder_eoa_out_50 if snap.funder_eoa_out_50 > 0 else max(1, snap.funder_fanout_50)
    same_amt_ratio = same_amt_cnt / max(1, funder_eoa_denom)

    # Mainstream CEX withdrawal hot wallet recognition (whitelist OR high-nonce heterogeneous hot wallet):
    # Exempts honest retail CEX withdrawals while strictly blocking Disperse & homogeneous machine-dust fanouts!
    is_cex_funder = (
        (not is_batch_disperse)
        and (bool(snap.funder_is_cex_hot_wallet) or (funder_low in KNOWN_BSC_CEX_HOT_WALLETS))
    )
    homogeneous_machine_override = same_amt_cnt >= 5 and same_amt_ratio >= 0.45

    # Amount-agnostic homogeneous batch mother check (NO `first_bnb < 0.5` ceiling: catches 0.51 BNB, 2 BNB, etc.!)
    is_dust_or_batch_mother = (
        (0 < first_bnb < 0.005 and snap.funder_same_dust_50 >= 3)
        or (0 < first_bnb <= 0.0015 and snap.funder_fanout_50 >= 15)
        or (
            first_bnb > 0
            and same_amt_cnt >= 5
            and snap.funder_fanout_50 >= 5
            and (same_amt_ratio >= 0.30 or same_amt_cnt >= 10 or first_bnb < 0.05)
        )
    )
    if is_cex_funder and not homogeneous_machine_override:
        is_dust_or_batch_mother = False

    seasoned_hard_tok_in_usd = sum(
        t.value_float * (snap.bnb_price_usd if t.contract_addr.lower() == BSC_WBNB else 1.0)
        for t in credited_tok_inflows
        if 0 < t.timestamp <= seasoning_cutoff
    )
    seasoned_ref_funding_usd = seasoned_ext_bnb_in * snap.bnb_price_usd + seasoned_hard_tok_in_usd
    ref_funding_usd = max(ext_in_all_usd, first_bnb * snap.bnb_price_usd)
    # Never exempt `is_cex_funder` here: legitimate users deposit to per-user CEX deposit addresses,
    # NEVER back to the withdrawal hot wallet (`out_to_funder_usd > 0` is always mother/hub sweep-back!).
    swept_back_to_funder = (
        bool(all_ext_funder_addrs)
        and out_to_funder_usd > 0
        and effective_seasoned_usd < 15.0
        and (
            out_to_funder_usd >= 0.25 * max(ref_funding_usd, 1e-9)
            or (seasoned_ref_funding_usd > 0 and out_to_funder_usd >= 0.25 * seasoned_ref_funding_usd)
            or out_to_funder_usd >= 5.0
            or (ref_funding_usd < 10.0 and out_to_funder_usd >= 0.15 * max(ref_funding_usd, 1e-9))
        )
    )
    swept_out_relay = effective_seasoned_usd < 15.0 and (
        (ref_funding_usd > 0 and non_protocol_out_usd >= 0.65 * ref_funding_usd)
        or (seasoned_ref_funding_usd > 0 and non_protocol_out_usd >= 0.65 * seasoned_ref_funding_usd)
    )

    # Single Source of Truth (`sybil_provenance_tainted`) shared across Dual-Track eligibility AND D1/D2/D3 caps!
    sybil_provenance_tainted = bool(
        (not history_unverified)
        and (
            is_batch_disperse
            or is_dust_or_batch_mother
            or snap.funder_is_relay_pass_through
            or snap.stable_funder_tainted
            or snap.secondary_funder_tainted
            or swept_back_to_funder
            or swept_out_relay
        )
    )
    net_verified_historical_usd = max(0.0, ext_in_all_usd - non_protocol_out_usd)
    track_b_conserved_commitment_usd = max(
        0.0,
        net_verified_historical_usd - unrecovered_dex_alt_usd - unredeemed_zero_fee_vault_usd,
    )

    # Dual-Track Orthogonal Qualification Model (100% Biconditional Parity with On-Chain `totalScore >= 60`):
    # - Common Hard Prerequisites: verified history, untainted provenance, `span_days >= 3.0`, `active_days >= 2`, `fee_bearing_tx_count >= 1`
    # - Track A (72h Seasoned Capital Track): `effective_seasoned_usd >= 10.0`
    # - Track B (Veteran Multi-Day Multi-Protocol Track): `span_days >= 7.0`, `active_days >= 3`, `fee_bearing_tx_count >= 4`,
    #   `>= 2` independent fee-bearing contracts or categories, `ext_in_all_usd >= 10.0`, `track_b_conserved_commitment_usd >= 10.0`
    #   (hard-liquid commitment conserved across cross-chain bridges / prediction markets / self-receipted lending, immune to
    #   one-way unpriced wash-LP / aggregator split swaps), multi-day economic engagement or `>= 72h` seasoned historical inflow,
    #   and zero sweep-back / relay exit.
    common_gate_prereqs = (
        (not history_unverified)
        and (not sybil_provenance_tainted)
        and span_days >= 3.0
        and active_days >= 2
        and fee_bearing_tx_count >= 1
    )
    track_a_eligible = common_gate_prereqs and (effective_seasoned_usd >= MIN_SEASONED_COMMITMENT_USD)
    track_b_eligible = (
        common_gate_prereqs
        and span_days >= 7.0
        and active_days >= 3
        and fee_bearing_tx_count >= 4
        and (len(fee_bearing_contracts) >= 2 or len(fee_bearing_categories) >= 2)
        and ext_in_all_usd >= MIN_SEASONED_COMMITMENT_USD
        and net_verified_historical_usd >= MIN_SEASONED_COMMITMENT_USD
        and track_b_conserved_commitment_usd >= MIN_SEASONED_COMMITMENT_USD
        and (
            seasoned_ref_funding_usd >= MIN_SEASONED_COMMITMENT_USD
            or verified_bridge_out_usd >= MIN_SEASONED_COMMITMENT_USD
        )
        and (seasoned_ref_funding_usd >= MIN_SEASONED_COMMITMENT_USD or econ_active_days >= 2)
        and (not swept_back_to_funder)
        and (not swept_out_relay)
        and bool(funder_low)
        and (not snap.recent_window_truncated)
    )

    if history_unverified:
        d1_score = 8 if (snap.bnb_balance + snap.wbnb_balance) > 0 else 0
        reasons.append(f"D1({d1_score}/30): 历史或入金源流水未完整核验 (Fail-Closed 拒绝签发未溯源高分)")
    elif snap.tx_count == 0 and retained_usd == 0.0 and not external_funding_inflows and not external_hard_token_inflows:
        d1_score = 0
        risk_flags.append("EMPTY_UNFUNDED_WALLET")
        reasons.append("D1(0/30): 空钱包无任何链上入金记录")
    elif is_batch_disperse:
        d1_score = 0
        risk_flags.append("SYBIL_BATCH_DISPERSE_CONTRACT")
        reasons.append("D1(0/30): 入金源命中批量分发合约/内部粉尘空投器")
    elif is_dust_or_batch_mother:
        d1_score = 2
        risk_flags.append("SYBIL_HOMOGENEOUS_DUST_MOTHER")
        reasons.append(
            f"D1(2/30): 命中同源等额批量母钱包聚类 (首笔 {first_bnb:.5f} BNB, 母钱包同额扇出={same_amt_cnt})"
        )
    elif snap.funder_is_relay_pass_through or snap.stable_funder_tainted or snap.secondary_funder_tainted:
        d1_score = 6
        risk_flags.append("SYBIL_RELAY_CHAIN_FUNDING")
        reasons.append(
            f"D1(6/30): 命中串行过桥/二次注资轮转池/稳定币母钱包中继 (首笔上游 {funder_low[:10] or '0x0'}...)"
        )
    elif swept_back_to_funder or swept_out_relay:
        d1_score = 6 if effective_seasoned_bnb >= 0.018 else 4
        risk_flags.append("GAS_SWEEP_BACK_DETECTED")
        reasons.append(f"D1({d1_score}/30): 检测到入金后清退/轮转回抽本金 (72h净留存≈{effective_seasoned_usd:.2f} USD)")
    elif (
        (0 < first_bnb <= 0.0015 or (first_bnb == 0 and 0 < snap.bnb_balance <= 0.0015))
        and effective_seasoned_bnb < 0.005
        and not track_b_eligible
    ):
        if unseasoned_ext_bnb_in >= 0.005 or unseasoned_net_inflow_72h_usd >= 3.0:
            d1_score = 12
            risk_flags.append("UNSEASONED_HOT_MONEY_INJECTION")
            reasons.append(
                f"D1(12/30): 微粉尘老壳近 72h 突击注入热钱 (净未沉淀流入≈{unseasoned_net_inflow_72h_usd:.2f} USD)"
            )
        else:
            d1_score = 8
            risk_flags.append("EXTREME_MICRO_DUST_FUNDING")
            reasons.append(f"D1(8/30): 极限微粉尘单点中继入金 ({max(first_bnb, snap.bnb_balance):.5f} BNB)，仅够注册 Gas")
    elif not funder_low:
        d1_score = 8
        risk_flags.append("UNVERIFIED_FUNDER_ORIGIN")
        reasons.append("D1(8/30): 未捕获明确首笔外部入金源地址，按保守上限计分")
    else:
        seasoned_effective = effective_seasoned_bnb

        if track_b_eligible and effective_seasoned_usd < MIN_SEASONED_COMMITMENT_USD:
            # Track B (Veteran Multi-Protocol Cross-Chain Agent): credit verified conserved historical net inflow (22..27 pts)
            if track_b_conserved_commitment_usd >= 100.0:
                d1_score = 27
            elif track_b_conserved_commitment_usd >= 35.0:
                d1_score = 25
            else:
                d1_score = 22
            reasons.append(
                f"D1({d1_score}/30): 轨B资深多协议合规入金溯源通过 (历史净合规入金≈{track_b_conserved_commitment_usd:.2f} USD, 首笔 {first_bnb:.4f} BNB)"
            )
        else:
            # Track A / standard commitment path anchored on NET 72h-seasoned commitment (`effective_seasoned_bnb`)
            if seasoned_bal_equiv_bnb >= 0.05 or (seasoned_effective >= 0.05 and first_bnb >= 0.015) or (
                seasoned_effective >= 0.02 and len(seasoned_unique_funders) >= 2
            ):
                d1_score = 30
            elif seasoned_effective >= 0.018:
                d1_score = 27
            elif seasoned_effective >= 0.005:
                d1_score = 24 if seasoned_effective >= 0.01 else 18
            elif seasoned_effective > 0.001:
                d1_score = 15
            else:
                raw_unseasoned = max(first_bnb, total_ext_bnb_in, snap.bnb_balance + snap.wbnb_balance)
                d1_score = 18 if raw_unseasoned >= 0.05 else (15 if raw_unseasoned >= 0.005 else 12)
                if unseasoned_net_inflow_72h_usd >= 1.0:
                    risk_flags.append("UNSEASONED_NEW_CAPITAL_72H")

            # Apply `< 10 USD` commitment ceiling BEFORE formatting `reasons` when neither Track A nor Track B is met
            if effective_seasoned_usd < MIN_SEASONED_COMMITMENT_USD and d1_score > 18:
                d1_score = 18

            cex_note = ", CEX热钱包豁免" if is_cex_funder else ""
            reasons.append(
                f"D1({d1_score}/30): 入金溯源完成 (首笔 {first_bnb:.4f} BNB, 72h净沉淀={seasoned_effective:.4f} BNB, 同源扇出={same_amt_cnt}{cex_note})"
            )

    # -------------------------------------------------------------------------
    # D2: Multi-Day Temporal Maturity & Inter-Arrival Entropy (Max 25 pts)
    # -------------------------------------------------------------------------
    d2_score, entropy_bits, cv = _compute_d2_temporal_dimension(
        ts_sorted=ts_sorted,
        span_days=span_days,
        active_days=active_days,
        effective_tx_count=effective_tx_count,
        snap_tx_count=snap.tx_count,
        history_unverified=history_unverified,
        fee_bearing_tx_count=fee_bearing_tx_count,
        sybil_provenance_tainted=sybil_provenance_tainted,
        track_b_eligible=track_b_eligible,
        effective_seasoned_usd=effective_seasoned_usd,
        risk_flags=risk_flags,
        reasons=reasons,
    )

    # -------------------------------------------------------------------------
    # D3: Whitelisted Cross-Protocol Friction & Seasoned Retention (Max 30 pts)
    # -------------------------------------------------------------------------
    if history_unverified:
        # Strict Fail-Closed (< 35 invariant): unverified history/funder ALWAYS zeros friction_pts!
        friction_pts = 0
    elif real_economic_tx_count == 0 or fee_bearing_tx_count == 0:
        # Pure 0-fee lending supply without any fee-bearing Swap/Prediction/Bridge earns 0 friction (caps total <= 58 < 60)
        friction_pts = 0
        if real_economic_tx_count == 0 and (
            (zero_friction_tx_count >= 2 and effective_tx_count >= 3) or zero_friction_tx_count >= 4
        ):
            risk_flags.append("ZERO_FRICTION_APPROVE_OR_CHECKIN_FARMER")
    else:
        proto_breadth = max(len(hit_categories), 2 if (track_b_eligible and len(fee_bearing_contracts) >= 2) else 0)
        cat_pts = min(11, proto_breadth * 4)
        vol_tx_pts = min(5, int(math.log2(real_economic_tx_count + 1) * 1.8))
        friction_pts = min(16, cat_pts + vol_tx_pts)
        if econ_span_sec < 3600 and econ_active_days <= 1:
            friction_pts = min(friction_pts, 8)
        # Strict 3-day multi-day maturity cap so `span_days < 3.0` NEVER reaches `totalScore >= 60`!
        if span_days < 3.0 or active_days < 2:
            friction_pts = min(friction_pts, 4)

    if history_unverified:
        if retained_usd >= 50.0:
            retention_pts = 6
        elif retained_usd >= 10.0:
            retention_pts = 4
        elif retained_usd >= 2.0:
            retention_pts = 2
        else:
            retention_pts = 0
    elif real_economic_tx_count == 0 or fee_bearing_tx_count == 0:
        if effective_seasoned_usd >= 50.0:
            retention_pts = 6
        elif effective_seasoned_usd >= 10.0:
            retention_pts = 4
        elif effective_seasoned_usd >= 2.0 or retained_usd >= 10.0:
            retention_pts = 2
        else:
            retention_pts = 0
    else:
        # Retention points anchored on 72h continuous seasoned capital, plus bounded historical protocol commitment on Track B
        if effective_seasoned_usd >= 200.0:
            retention_pts = 14
        elif effective_seasoned_usd >= 50.0:
            retention_pts = 12
        elif effective_seasoned_usd >= 10.0:
            retention_pts = 9
        elif effective_seasoned_usd >= 2.0:
            retention_pts = 3
        elif retained_usd >= 10.0:
            retention_pts = 2
        else:
            retention_pts = 0

        if track_b_eligible and effective_seasoned_usd < MIN_SEASONED_COMMITMENT_USD:
            retention_pts = max(retention_pts, 4 if net_verified_historical_usd >= 50.0 else 3)

        if span_days < 3.0 or active_days < 2:
            retention_pts = min(retention_pts, 3)

    d3_score = min(30, friction_pts + retention_pts)
    if sybil_provenance_tainted:
        d3_score = min(d3_score, 12)
    elif (not history_unverified) and (not track_b_eligible) and effective_seasoned_usd < MIN_SEASONED_COMMITMENT_USD:
        d3_score = min(d3_score, 11)
        if fee_bearing_tx_count >= 1 and span_days >= 3.0:
            risk_flags.append("INSUFFICIENT_72H_SEASONED_CAPITAL")

    reasons.append(
        f"D3({d3_score}/30): 白名单协议={sorted(hit_categories) or ['NONE']} (有效摩擦 {real_economic_tx_count}笔 / 计费摩擦 {fee_bearing_tx_count}笔 / 零摩擦 {zero_friction_tx_count}笔), 留存≈{retained_usd:.2f} USD (72h连续净沉淀≈{effective_seasoned_usd:.2f} USD, BNB@{snap.bnb_price_usd:.2f})"
    )

    # -------------------------------------------------------------------------
    # D4: EIP-712 Cryptographic Attestation & SPACE ID .ai Binding (Max 15 pts)
    # -------------------------------------------------------------------------
    norm_handle = normalize_handle(snap.onchain_handle)
    bare_handle = strip_ai_suffix(norm_handle)

    if not norm_handle:
        d4_score = 0
        risk_flags.append("NO_SPACE_ID_AI_BOUND")
        reasons.append("D4(0/15): 链上 0x60B9...022F 未绑定任何 .ai Agent ID")
    else:
        d4_score = 8
        forward_matches = (snap.nameapi_address is None) or (snap.nameapi_address.lower() == addr_low)
        is_gibberish_bot_name = bool(_BOT_HANDLE_RE.match(bare_handle))
        if forward_matches and not is_gibberish_bot_name:
            d4_score += 4
        elif forward_matches and is_gibberish_bot_name:
            d4_score += 1
            risk_flags.append("SUSPICIOUS_GENERATED_HANDLE_PATTERN")
        d4_score += 3

    # Cross-dimensional numerical ceiling when neither Track A nor Track B is met so `d1 + d2 + d3 + d4 < 60` holds unconditionally
    if (not history_unverified) and (not track_b_eligible) and effective_seasoned_usd < MIN_SEASONED_COMMITMENT_USD and d1_score > 18:
        d1_score = 18

    total_score = int(d1_score + d2_score + d3_score + d4_score)

    # Hard Mathematical Parity Invariants (100% Biconditional Equivalence with On-Chain `AgentPulseGate.isLiveAgent(user, 60)`)
    live_prereqs_met = (not sybil_provenance_tainted) and (track_a_eligible or track_b_eligible)
    if history_unverified and total_score >= 35:
        raise RuntimeError(f"CRITICAL Fail-Closed violation: unverified wallet scored {total_score} >= 35")
    if (not live_prereqs_met) and total_score >= 60:
        raise RuntimeError(
            f"CRITICAL Gate Parity violation: disqualified wallet scored {total_score} >= 60 "
            f"(unverified={history_unverified}, tainted={sybil_provenance_tainted}, span={span_days:.2f}, "
            f"active={active_days}, feeTx={fee_bearing_tx_count}, effSeasonedUSD={effective_seasoned_usd:.2f}, "
            f"trackB={track_b_eligible})"
        )

    # Generate & self-verify EIP-712 payload using live contract_nonce
    digest, domain_sep, struct_hash = compute_attestation_digest(
        wallet=snap.address,
        handle=norm_handle or "unbound.ai",
        total_score=total_score,
        d1_funding=d1_score,
        d2_temporal=d2_score,
        d3_economic=d3_score,
        d4_proof=d4_score,
        issued_at=issued_at,
        expires_at=expires_at,
        nonce=snap.contract_nonce,
        chain_id=chain_id,
        verifying_contract=verifying_contract,
    )
    sig_bundle = sign_attestation_digest(digest, private_key_hex=signer_private_key)
    recovered = recover_attestation_signer(digest, sig_bundle["signature"])
    if recovered.lower() != sig_bundle["signer"].lower():
        raise RuntimeError("CRITICAL: EIP-712 local ecrecover self-check failed")

    if norm_handle:
        reasons.append(
            f"D4({d4_score}/15): 链上强验 {norm_handle} 归属一致 (nonce={snap.contract_nonce})，已签发 EIP-712 存证摘要 ({sig_bundle['digest'][:14]}...)"
        )

    # Verify `reasons` dimension headers match final `(d1_score, d2_score, d3_score, d4_score)` 100%
    expected_prefixes = {
        "D1(": f"D1({d1_score}/30):",
        "D2(": f"D2({d2_score}/25):",
        "D3(": f"D3({d3_score}/30):",
        "D4(": f"D4({d4_score}/15):",
    }
    for r_line in reasons:
        p3 = r_line[:3]
        if p3 in expected_prefixes and not r_line.startswith(expected_prefixes[p3]):
            raise RuntimeError(f"CRITICAL Reason/Score mismatch: '{r_line}' vs '{expected_prefixes[p3]}'")

    # Exact Biconditional Equivalence: for any bound `.ai` wallet, `is_live_60 <==> (total_score >= 60) <==> (qualified_track != "NONE")`!
    is_live_60 = bool(norm_handle) and (not history_unverified) and (total_score >= 60)
    qualified_track = (
        (
            "TRACK_A_SEASONED_CAPITAL"
            if track_a_eligible
            else ("TRACK_B_VETERAN_MULTI_PROTOCOL" if track_b_eligible else "NONE")
        )
        if is_live_60
        else "NONE"
    )
    if norm_handle and (is_live_60 != (total_score >= 60)):
        raise RuntimeError("CRITICAL: Off-chain isLiveAgent60 diverged from on-chain totalScore >= 60")
    if (qualified_track != "NONE") != is_live_60:
        raise RuntimeError("CRITICAL: Off-chain qualifiedTrack diverged from isLiveAgent60")
    if not norm_handle:
        tier, label = "UNREGISTERED", "未绑定 .ai 身份"
    elif history_unverified:
        tier, label = "UNVERIFIED", "索引器限流/历史未核验 (Fail-Closed 暂缓放行)"
    elif is_live_60 and total_score >= 80:
        tier, label = "S", "Sovereign Live Agent (高净值实战活体)"
    elif is_live_60:
        tier, label = "A", "Verified Live Agent (真实活跃智能体)"
    elif total_score >= 40 and not sybil_provenance_tainted:
        tier, label = "B", "Emerging / Low-Friction Agent (新晋/低摩擦待沉淀)"
    else:
        tier, label = "SYBIL", "High-Risk Sybil / Dormant Dust Shell (高危女巫/休眠粉尘壳)"

    return {
        "ok": True,
        "address": to_checksum_address(snap.address),
        "addressLower": addr_low,
        "handle": norm_handle,
        "hasAgentId": bool(norm_handle),
        "totalScore": total_score,
        "tier": tier,
        "verdictLabel": label,
        "isLiveAgent60": is_live_60,
        "qualifiedTrack": qualified_track,
        "historyUnverified": history_unverified,
        "dimensions": {
            "d1Funding": {
                "score": d1_score,
                "max": 30,
                "firstFundingBNB": round(first_bnb, 6),
                "seasonedFundingBNB": round(seasoned_ext_bnb_in, 6),
                "historicalExtInUSD": round(ext_in_all_usd, 2),
                "netHistoricalCommitmentUSD": round(net_verified_historical_usd, 2),
                "trackBConservedCommitmentUSD": round(track_b_conserved_commitment_usd, 2),
                "funder": funder_low,
                "funderTxCount": snap.funder_tx_count,
                "funderIsCexHotWallet": is_cex_funder,
                "funderFanout50": snap.funder_fanout_50,
                "funderSameDust50": same_amt_cnt,
                "funderRelayPassThrough": snap.funder_is_relay_pass_through,
            },
            "d2Temporal": {
                "score": d2_score,
                "max": 25,
                "txCount": effective_tx_count,
                "spanDays": round(span_days, 2),
                "activeDays": active_days,
                "entropyBits": round(entropy_bits, 3),
                "intervalCV": round(cv, 3),
            },
            "d3Economic": {
                "score": d3_score,
                "max": 30,
                "protocolsHit": sorted(hit_categories),
                "feeBearingContracts": len(fee_bearing_contracts),
                "realEconomicTxs": real_economic_tx_count,
                "feeBearingTxs": fee_bearing_tx_count,
                "zeroFrictionTxs": zero_friction_tx_count,
                "retainedUSD": round(retained_usd, 2),
                "seasonedRetainedUSD": round(seasoned_retained_usd, 2),
                "effectiveSeasonedUSD": round(effective_seasoned_usd, 2),
                "bnbBalance": round(snap.bnb_balance, 6),
                "wbnbBalance": round(snap.wbnb_balance, 6),
                "stableUSD": round(liquid_stable_usd, 2),
                "bnbPriceUSD": round(snap.bnb_price_usd, 2),
                "priceSource": snap.bnb_price_source,
            },
            "d4Proof": {
                "score": d4_score,
                "max": 15,
                "registry": SPACE_ID_AI_REGISTRY,
                "forwardConsistent": (snap.nameapi_address is None or snap.nameapi_address.lower() == addr_low),
                "contractNonce": snap.contract_nonce,
            },
        },
        "riskFlags": risk_flags,
        "reasons": reasons,
        "eip712": {
            "domain": {
                "name": "AgentPulse",
                "version": "1",
                "chainId": chain_id,
                "verifyingContract": to_checksum_address(verifying_contract),
            },
            "domainSeparator": "0x" + domain_sep.hex(),
            "structHash": "0x" + struct_hash.hex(),
            "payload": {
                "wallet": to_checksum_address(snap.address),
                "handle": norm_handle,
                "handleHash": "0x" + keccak((norm_handle or "unbound.ai").encode("utf-8")).hex(),
                "totalScore": total_score,
                "d1Funding": d1_score,
                "d2Temporal": d2_score,
                "d3Economic": d3_score,
                "d4Proof": d4_score,
                "issuedAt": issued_at,
                "expiresAt": expires_at,
                "nonce": snap.contract_nonce,
            },
            "signature": sig_bundle["signature"],
            "digest": sig_bundle["digest"],
            "verifierSigner": sig_bundle["signer"],
            "isDemoSigner": sig_bundle["isDemoSigner"],
        },
    }


# =============================================================================
# Live BSC Read-Only Collector (Dual-Source SPACE ID + Batch RPC + NodeReal/V2)
# =============================================================================

class AgentLivenessScorer:
    def __init__(
        self,
        rpc_pool: Sequence[str] = BSC_RPC_POOL,
        indexer_pool: Sequence[str] = NODEREAL_INDEXER_POOL,
        verifying_contract: str = DEFAULT_VERIFYING_CONTRACT,
        cache_ttl_sec: int = 180,
    ):
        self.rpc_pool = list(rpc_pool)
        custom_nr = os.environ.get("NODEREAL_BSC_RPC", "").strip()
        self.indexer_pool = ([custom_nr] if custom_nr else []) + list(indexer_pool)
        self.verifying_contract = verifying_contract
        self.cache_ttl_sec = cache_ttl_sec
        self._cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        # TTL-bounded funder transfer & nonce caches: never store degraded or empty lists permanently!
        self._funder_tx_cache: Dict[str, Tuple[float, List[TransferEvent]]] = {}
        self._funder_nonce_cache: Dict[str, Tuple[float, int]] = {}
        self._rpc_cursor = 0
        self._idx_cursor = 0

    def _should_check_onchain_nonce(self) -> bool:
        vc_low = (self.verifying_contract or "").strip().lower()
        return (
            vc_low.startswith("0x")
            and len(vc_low) == 42
            and int(vc_low, 16) != 0
            and vc_low != PLACEHOLDER_VERIFYING_CONTRACT.lower()
        )

    def _rpc_batch(self, calls: List[Dict[str, Any]], timeout: float = 6.5) -> List[Any]:
        for offset in range(len(self.rpc_pool)):
            url = self.rpc_pool[(self._rpc_cursor + offset) % len(self.rpc_pool)]
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(calls).encode("utf-8"),
                    headers={"Content-Type": "application/json", "User-Agent": "AgentPulse/1.2"},
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw = json.loads(resp.read().decode("utf-8"))
                if isinstance(raw, list):
                    self._rpc_cursor = (self._rpc_cursor + offset) % len(self.rpc_pool)
                    by_id = {}
                    for item in raw:
                        if isinstance(item, dict) and "error" not in item:
                            by_id[item.get("id")] = item.get("result")
                    return [by_id.get(c["id"]) for c in calls]
            except Exception:
                continue
        return [None] * len(calls)

    def _rpc_single(self, method: str, params: list, timeout: float = 6.5) -> Any:
        res = self._rpc_batch([{"jsonrpc": "2.0", "method": method, "params": params, "id": 1}], timeout=timeout)
        return res[0]

    def query_onchain_contract_nonce(
        self,
        addr_low: str,
        prefetched_code: Any = None,
        prefetched_nonce: Any = None,
    ) -> int:
        """
        Queries live `AgentPulseGate.nonces(address)` (`0x7ecebe00`) Fail-Closed.
        If `verifying_contract` has deployed bytecode on-chain and `nonces(address)` fails, raises RuntimeError.
        """
        if not self._should_check_onchain_nonce():
            return 0
        vc_low = self.verifying_contract.strip().lower()
        code_hex = prefetched_code
        nonce_hex = prefetched_nonce
        if code_hex is None and nonce_hex is None:
            res = self._rpc_batch(
                [
                    {"jsonrpc": "2.0", "method": "eth_getCode", "params": [vc_low, "latest"], "id": 1},
                    {
                        "jsonrpc": "2.0",
                        "method": "eth_call",
                        "params": [{"to": vc_low, "data": SELECTOR_NONCES + "000000000000000000000000" + addr_low[2:]}, "latest"],
                        "id": 2,
                    },
                ]
            )
            code_hex, nonce_hex = res[0], res[1]
        if code_hex is None:
            code_hex = self._rpc_single("eth_getCode", [vc_low, "latest"])

        has_deployed_code = (
            isinstance(code_hex, str)
            and code_hex.startswith("0x")
            and len(code_hex) > 2
            and any(c != "0" for c in code_hex[2:])
        )
        if not has_deployed_code:
            return 0

        if not (isinstance(nonce_hex, str) and nonce_hex.startswith("0x") and len(nonce_hex) >= 66):
            nonce_hex = self._rpc_single(
                "eth_call",
                [{"to": vc_low, "data": SELECTOR_NONCES + "000000000000000000000000" + addr_low[2:]}, "latest"],
            )
        if not (isinstance(nonce_hex, str) and nonce_hex.startswith("0x") and len(nonce_hex) >= 66):
            raise RuntimeError(
                f"Fail-Closed: unable to query nonces(address) (0x7ecebe00) on deployed contract {self.verifying_contract}"
            )
        return int(nonce_hex, 16)

    def resolve_handle_to_address(self, handle: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Resolves `<name>.ai` -> (canonical_address, nameapi_address) using:
        1) SPACE ID NameAPI (`https://nameapi.space.id/getAddress?domain=name.ai`)
        2) On-chain BSC SPACE ID Registry `ownerOfHandle(name)` (`0x1da94fb4`)
        """
        norm = normalize_handle(handle)
        bare = strip_ai_suffix(norm)
        if not bare:
            return None, None

        nameapi_addr: Optional[str] = None
        try:
            q = urllib.parse.quote(norm)
            req = urllib.request.Request(
                f"{SPACE_ID_NAMEAPI_BASE}/getAddress?domain={q}",
                headers={"User-Agent": "AgentPulse/1.2"},
            )
            with urllib.request.urlopen(req, timeout=4.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                addr = (data.get("address") or "").strip()
                if data.get("code") == 0 and addr.startswith("0x") and len(addr) == 42 and int(addr, 16) != 0:
                    nameapi_addr = addr.lower()
        except Exception:
            pass

        onchain_addr: Optional[str] = None
        try:
            call_data = SELECTOR_OWNER_OF_HANDLE + abi_encode(["string"], [bare]).hex()
            res_hex = self._rpc_single(
                "eth_call",
                [{"to": SPACE_ID_AI_REGISTRY, "data": call_data}, "latest"],
            )
            if res_hex and len(res_hex) >= 66:
                decoded = abi_decode(["address"], bytes.fromhex(res_hex[2:]))[0]
                if int(decoded, 16) != 0:
                    onchain_addr = decoded.lower()
        except Exception:
            pass

        return (onchain_addr or nameapi_addr), nameapi_addr

    def reverse_resolve_address(self, address: str) -> str:
        """Calls BSC `0x60B9...022F.handleOf(address)` (`0xc50a1514`) directly."""
        addr_low = (address or "").strip().lower()
        if not addr_low.startswith("0x") or len(addr_low) != 42:
            return ""
        call_data = SELECTOR_HANDLE_OF + "000000000000000000000000" + addr_low[2:]
        res_hex = self._rpc_single(
            "eth_call",
            [{"to": SPACE_ID_AI_REGISTRY, "data": call_data}, "latest"],
        )
        if res_hex and len(res_hex) > 130:
            try:
                handle_str = abi_decode(["string"], bytes.fromhex(res_hex[2:]))[0].strip()
                if handle_str:
                    return normalize_handle(handle_str)
            except Exception:
                pass
        return ""

    def _fetch_etherscan_v2_with_truncation(
        self,
        address: str,
        categories: Optional[Sequence[str]] = None,
        order: str = "asc",
        max_count: int = 80,
        page: int = 1,
        max_pages: int = 1,
        cutoff_ts: int = 0,
    ) -> Tuple[Optional[List[Dict[str, Any]]], bool]:
        """
        Secondary fallback via Etherscan V2 API (`chainid=56`) when `BSCSCAN_API_KEY` / `ETHERSCAN_API_KEY` is set.
        - Strictly Fail-Closed on HTTP 200 `status="0"` / `message="NOTOK"` (returns `(None, False)`).
        - Paginates EACH category (`txlist`, `txlistinternal`, `tokentx`) independently when `max_pages > 1` so an
          old timestamp in `txlist` NEVER prematurely terminates Page 2..N of `tokentx`!
        - Preserves genuine `logIndex` (for `20`) and `traceId` (for `internal`) without conflating `transactionIndex`.
        """
        api_key = (os.environ.get("BSCSCAN_API_KEY") or os.environ.get("ETHERSCAN_API_KEY") or "").strip()
        if not api_key:
            return None, False

        wanted = set(categories or ("external", "internal", "20"))
        action_specs = [
            (action, cat)
            for action, cat in (("txlist", "external"), ("txlistinternal", "internal"), ("tokentx", "20"))
            if cat in wanted
        ]
        merged: List[Dict[str, Any]] = []
        any_cat_truncated = False
        req_count = 0

        for action, cat in action_specs:
            for p_offset in range(max(1, max_pages)):
                cur_page = max(1, page) + p_offset
                if req_count > 0:
                    time.sleep(0.21)  # Respect Etherscan V2 5 calls/sec rate limit
                req_count += 1
                qs = urllib.parse.urlencode(
                    {
                        "chainid": "56",
                        "module": "account",
                        "action": action,
                        "address": address.lower(),
                        "startblock": "0",
                        "endblock": "99999999",
                        "page": str(cur_page),
                        "offset": str(max_count),
                        "sort": order,
                        "apikey": api_key,
                    }
                )
                try:
                    req = urllib.request.Request(
                        f"{ETHERSCAN_V2_API_BASE}?{qs}",
                        headers={"User-Agent": "AgentPulse/1.2"},
                    )
                    with urllib.request.urlopen(req, timeout=7.0) as resp:
                        body = json.loads(resp.read().decode("utf-8"))
                    if not isinstance(body, dict):
                        return None, False

                    status_str = str(body.get("status", "")).strip()
                    msg_low = str(body.get("message", "")).strip().lower()
                    rows = body.get("result")

                    if status_str == "1" and isinstance(rows, list):
                        cat_ts: List[int] = []
                        for r in rows:
                            if isinstance(r, dict):
                                r_ts = int(r.get("timeStamp") or 0)
                                if r_ts > 0:
                                    cat_ts.append(r_ts)
                                raw_log_idx = r.get("logIndex")
                                raw_trace_id = r.get("traceId")
                                merged.append(
                                    {
                                        "hash": r.get("hash"),
                                        "category": cat,
                                        "from": r.get("from"),
                                        "to": r.get("to"),
                                        "value": r.get("value", "0"),
                                        "decimal": int(r.get("tokenDecimal") or 18) if cat == "20" else 18,
                                        "asset": r.get("tokenSymbol") or ("BNB" if cat != "20" else ""),
                                        "contractAddress": r.get("contractAddress") or "",
                                        "blockTimeStamp": r_ts,
                                        "input": r.get("input") or "0x",
                                        "isError": r.get("isError", "0"),
                                        "txreceipt_status": r.get("txreceipt_status", "1"),
                                        "logIndex": int(raw_log_idx) if (cat == "20" and raw_log_idx not in (None, "")) else 0,
                                        "traceId": str(raw_trace_id).strip() if (cat == "internal" and raw_trace_id not in (None, "")) else "",
                                    }
                                )
                        if order != "desc" or max_pages <= 1:
                            break
                        cat_min_ts = min(cat_ts) if cat_ts else 0
                        if len(rows) < max_count or (cutoff_ts > 0 and cat_min_ts <= cutoff_ts):
                            break
                        if p_offset == max_pages - 1:
                            any_cat_truncated = True
                    elif status_str == "0" and "no transactions found" in msg_low and (
                        rows == [] or (isinstance(rows, str) and "no transactions found" in rows.lower())
                    ):
                        # Valid Etherscan V2 empty category response (NOT a rate-limit or key error)
                        break
                    else:
                        # `NOTOK`, `"Max rate limit reached"`, `"Invalid API Key"`, etc. -> Fail-Closed!
                        return None, False
                except Exception:
                    return None, False
        return merged, any_cat_truncated

    def _fetch_etherscan_v2_fallback(
        self,
        address: str,
        categories: Optional[Sequence[str]] = None,
        order: str = "asc",
        max_count: int = 80,
        page: int = 1,
    ) -> Optional[List[Dict[str, Any]]]:
        rows, _ = self._fetch_etherscan_v2_with_truncation(
            address=address,
            categories=categories,
            order=order,
            max_count=max_count,
            page=page,
            max_pages=1,
            cutoff_ts=0,
        )
        return rows

    def _fetch_nodereal_transfers_paged(
        self,
        address: str,
        categories: List[str],
        order: str = "asc",
        max_count: int = 80,
        page_key: Optional[str] = None,
        v2_page: int = 1,
        v2_max_pages: int = 1,
        v2_cutoff_ts: int = 0,
    ) -> Tuple[List[Dict[str, Any]], bool, Optional[str], bool]:
        params_obj: Dict[str, Any] = {
            "address": address.lower(),
            "category": categories,
            "order": order,
            "maxCount": hex(max_count),
        }
        if page_key:
            params_obj["pageKey"] = page_key

        max_attempts = max(4, len(self.indexer_pool) * 3)
        for attempt in range(max_attempts):
            url = self.indexer_pool[(self._idx_cursor + attempt) % len(self.indexer_pool)]
            try:
                payload = {"jsonrpc": "2.0", "method": "nr_getTransactionByAddress", "params": [params_obj], "id": 1}
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json", "User-Agent": "AgentPulse/1.2"},
                )
                with urllib.request.urlopen(req, timeout=7.5) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                if "result" in body and isinstance(body["result"], dict):
                    self._idx_cursor = (self._idx_cursor + attempt + 1) % len(self.indexer_pool)
                    nxt_key = body["result"].get("pageKey")
                    nxt_str = str(nxt_key).strip() if nxt_key else None
                    return body["result"].get("transfers") or [], False, nxt_str, False
                if "error" in body and isinstance(body["error"], dict) and body["error"].get("code") == -32005:
                    time.sleep(min(7.0, 3.0 + attempt * 1.5))
                    continue
            except urllib.error.HTTPError as he:
                if he.code == 429:
                    time.sleep(min(8.0, 3.2 + attempt * 1.6))
                    continue
            except Exception:
                pass
            time.sleep(min(4.0, 0.8 * (1.5 ** attempt)))

        v2_rows, v2_trunc = self._fetch_etherscan_v2_with_truncation(
            address,
            categories=categories,
            order=order,
            max_count=max_count,
            page=v2_page,
            max_pages=v2_max_pages,
            cutoff_ts=v2_cutoff_ts,
        )
        if v2_rows is not None:
            # When `v2_max_pages > 1`, Etherscan V2 already paginated each category independently!
            return v2_rows, False, None, v2_trunc

        return [], True, None, False

    def _fetch_nodereal_transfers(
        self,
        address: str,
        categories: List[str],
        order: str = "asc",
        max_count: int = 80,
    ) -> Tuple[List[Dict[str, Any]], bool]:
        rows, deg, _, _ = self._fetch_nodereal_transfers_paged(
            address=address, categories=categories, order=order, max_count=max_count
        )
        return rows, deg

    @staticmethod
    def _parse_transfers_with_keys(
        raw_list: List[Dict[str, Any]],
    ) -> List[Tuple[Tuple[str, str, str, str, str, int, str, int], TransferEvent]]:
        """
        Parses transfer items from a single query stream while preserving ALL multi-leg transfers in the same tx!
        - Includes `contract_addr` AND exact `val_int` in the base signature so `1 wei` + `250 USDT` / `0.50 BNB`
          NEVER collide even when `logIndex` / `traceIndex` / `traceId` are 0 or absent!
        - Uses explicit event identifiers (`id` / `logIndex` / `traceId` / `traceIndex`) when present, and assigns
          an intra-stream multiplicity ordinal `occ = 0, 1, ...` when absent so even identical-amount multi-legs
          in the same transaction are 100% preserved without double-counting across `asc` + `desc` merges!
        """
        out: List[Tuple[Tuple[str, str, str, str, str, int, str, int], TransferEvent]] = []
        seen_explicit_uids: Set[Tuple[str, str, str, str, str, int, str]] = set()
        occ_counter: Dict[Tuple[str, str, str, str, str, int, str], int] = {}

        for item in raw_list:
            tx_hash = (item.get("hash") or "").lower()
            cat = str(item.get("category") or "external")
            frm = (item.get("from") or "").lower()
            to = (item.get("to") or "").lower()
            ca_low = (item.get("contractAddress") or "").lower()
            ts = int(item.get("blockTimeStamp") or 0)

            raw_val = item.get("value")
            if raw_val is None or raw_val == "":
                raw_val = "0x0"
            decimals = int(item.get("decimal") or 18) if cat == "20" else 18
            try:
                val_int = int(raw_val, 16) if isinstance(raw_val, str) and raw_val.startswith("0x") else int(raw_val)
            except Exception:
                val_int = 0

            event_uid = ""
            if item.get("id") not in (None, ""):
                event_uid = f"nrid:{item['id']}"
            elif cat == "20" and item.get("logIndex") not in (None, "", 0, "0"):
                event_uid = f"log:{int(item['logIndex'])}"
            elif cat == "internal" and item.get("traceId") not in (None, ""):
                event_uid = f"trace:{str(item['traceId']).strip()}"
            elif cat == "internal" and item.get("traceIndex") not in (None, "", 0, "0"):
                event_uid = f"tidx:{int(item['traceIndex'])}"

            base_sig = (tx_hash, cat, ca_low, frm, to, val_int, event_uid)
            if event_uid:
                if base_sig in seen_explicit_uids:
                    continue
                seen_explicit_uids.add(base_sig)
                occ = 0
            else:
                occ = occ_counter.get(base_sig, 0)
                occ_counter[base_sig] = occ + 1

            val_float = val_int / (10 ** max(0, decimals))
            inp = item.get("input") or "0x"
            sel = inp[:10].lower() if len(inp) >= 10 else "0x"
            status = parse_tx_status(item)
            ev = TransferEvent(
                tx_hash=tx_hash,
                category=cat,
                from_addr=frm,
                to_addr=to,
                value_float=val_float,
                asset=str(item.get("asset") or ("BNB" if cat in ("external", "internal") else "")),
                contract_addr=ca_low,
                timestamp=ts,
                selector=sel,
                status=status,
            )
            out.append(((*base_sig, occ), ev))
        return out

    @classmethod
    def _parse_transfers(cls, raw_list: List[Dict[str, Any]]) -> List[TransferEvent]:
        return [ev for _, ev in cls._parse_transfers_with_keys(raw_list)]

    @classmethod
    def _merge_transfer_streams(
        cls,
        asc_raw: List[Dict[str, Any]],
        desc_raw: List[Dict[str, Any]],
    ) -> List[TransferEvent]:
        merged_map: Dict[Tuple[str, str, str, str, str, int, str, int], TransferEvent] = {}
        for full_key, ev in cls._parse_transfers_with_keys(asc_raw):
            merged_map[full_key] = ev
        for full_key, ev in cls._parse_transfers_with_keys(desc_raw):
            if full_key not in merged_map:
                merged_map[full_key] = ev
        events = list(merged_map.values())
        events.sort(key=lambda x: x.timestamp)
        return events

    @staticmethod
    def _is_cex_hot_wallet(
        funder_addr: str,
        funder_tx_count: int,
        funder_txs: Sequence[TransferEvent],
        is_token_stream: bool = False,
        target_wallet: str = "",
    ) -> bool:
        """
        Recognizes mainstream CEX withdrawal hot wallets while strictly rejecting Disperse contracts,
        homogeneous machine-dust dispensers, and high-nonce ping-pong / revolving Sybil pools:
        1) Curated `KNOWN_BSC_CEX_HOT_WALLETS` (Binance, OKX, Bybit, Gate, Ceffu), provided `target_wallet`
           never swept funds back into `funder_addr` and no homogeneous machine-dust override occurred; OR
        2) Unlisted ultra-high outgoing nonce (`eth_getTransactionCount >= 50,000`) satisfying ALL of:
           - Zero self-transfers (`from_addr == to_addr`) in sampled history (anti 0.05-gwei nonce stuffing);
           - Zero bidirectional spoke overlap (`out_recipients & eoa_in_senders == empty`) and zero sweep-back;
           - Real CEX withdrawal fanout scale (`>= 12` unique external recipients and `>= 70%` unique-recipient density);
           - Multi-magnitude retail heterogeneity (`>= 8` distinct values, `CV >= 0.50`, `max/min >= 10.0x`,
             dominant single-amount share `< 35%`, and micro-dust share `< 65%`).
        """
        f_low = (funder_addr or "").lower()
        t_low = (target_wallet or "").lower()
        if not f_low or f_low in BATCH_DISPERSE_CONTRACTS or f_low in KNOWN_BSC_PROTOCOLS:
            return False

        self_tx_count = sum(1 for t in funder_txs if t.from_addr == f_low and t.to_addr == f_low)
        cand_outs = [
            t
            for t in funder_txs
            if t.from_addr == f_low
            and t.to_addr != f_low
            and t.value_float > 0
            and t.status == 1
            and t.to_addr not in KNOWN_BSC_PROTOCOLS
        ]
        if any((t.selector or "0x")[:10].lower() in BATCH_DISPERSE_SELECTORS for t in cand_outs):
            return False

        out_recipients = {t.to_addr for t in cand_outs}
        eoa_in_senders = {
            t.from_addr
            for t in funder_txs
            if t.to_addr == f_low
            and t.from_addr != f_low
            and t.value_float > 0
            and t.status == 1
            and (
                ((t.selector or "0x")[:10].lower() == "0x" and t.category in ("external", "internal"))
                or t.category == "20"
            )
            and t.from_addr not in KNOWN_BSC_PROTOCOLS
        }

        # Legitimate users deposit to per-user CEX deposit addresses, NEVER back to the withdrawal hot wallet!
        if t_low and t_low in eoa_in_senders:
            return False

        vals = [t.value_float for t in cand_outs]
        dust_floor = 0.50 if is_token_stream else 0.002
        rel_floor = 0.01 if is_token_stream else 0.00005

        max_cluster_recipients = 0
        max_same_share = 0.0
        dust_share = 0.0
        distinct_vals = 0
        cv_vals = 0.0
        val_span_ratio = 0.0

        if vals:
            dust_share = sum(1 for v in vals if v < dust_floor) / len(vals)
            distinct_vals = len({round(v, 2 if is_token_stream else 4) for v in vals})
            val_span_ratio = max(vals) / max(min(vals), 1e-9)
            mean_v = sum(vals) / len(vals)
            if mean_v > 0 and len(vals) >= 2:
                var_v = sum((v - mean_v) ** 2 for v in vals) / len(vals)
                cv_vals = math.sqrt(var_v) / mean_v
            for v in vals:
                tol = max(rel_floor, v * 0.05)
                recip_cnt = len({t.to_addr for t in cand_outs if abs(t.value_float - v) <= tol})
                share_v = sum(1 for x in vals if abs(x - v) <= tol) / len(vals)
                if recip_cnt > max_cluster_recipients:
                    max_cluster_recipients = recip_cnt
                if share_v > max_same_share:
                    max_same_share = share_v

        # Hard reject any wallet exhibiting homogeneous batch fanout or pure machine micro-dust spraying
        if len(vals) >= 5 and (
            (max_cluster_recipients >= 5 and max_same_share >= 0.45)
            or (dust_share >= 0.75 and max_cluster_recipients >= 3)
            or distinct_vals <= 2
        ):
            return False

        if f_low in KNOWN_BSC_CEX_HOT_WALLETS:
            return True

        # Unlisted high-nonce CEX check: zero bidirectional spoke overlap, zero self-tx stuffing,
        # real CEX fanout scale (`>=12` unique recipients), and multi-magnitude retail heterogeneity (`>=10x`).
        if (
            funder_tx_count >= CEX_HOT_WALLET_MIN_NONCE
            and self_tx_count == 0
            and len(out_recipients & eoa_in_senders) == 0
            and len(out_recipients) >= 12
            and len(out_recipients) >= 0.70 * len(cand_outs)
            and distinct_vals >= 8
            and cv_vals >= 0.50
            and val_span_ratio >= 10.0
            and max_same_share < 0.35
            and dust_share < 0.65
        ):
            return True

        return False

    @classmethod
    def _detect_funder_cluster_and_relay(
        cls,
        funder_addr: str,
        target_wallet: str,
        first_bnb: float,
        first_ts: int,
        funder_txs: Sequence[TransferEvent],
        funder_tx_count: int = 0,
        is_token_stream: bool = False,
        extra_ref_amounts: Sequence[float] = (),
        cross_hard_txs: Optional[Sequence[TransferEvent]] = None,
        target_had_same_tx_outflow: bool = False,
    ) -> Tuple[int, int, int, bool]:
        """
        Analyzes funder's recent outgoing/incoming transfers WITHOUT any `< 0.5 BNB` ceiling to detect:
        1) `fanout`: unique outgoing recipients
        2) `same_dust`: equal-sized (<0.005) dust transfers
        3) `same_amount`: equal-sized batch transfers at ANY magnitude (`first_bnb > 0`, e.g. 0.51 BNB, 2.0 BNB),
           evaluated across BOTH single-leg amounts (including max leg to defeat micro-decoy front-running) AND
           per-recipient aggregated totals (defeating multi-leg split funding such as `6 x 1.95 USDT = 11.70 USDT`)!
        4) `is_relay_pass_through`:
           - Exempts verified mainstream CEX withdrawal hot wallets & `>= 50,000`-nonce zero-overlap CEX hot wallets;
           - Pattern A: Pass-through relay shell (low unique EOA fanout `<=7` or short-lived `<72h`/`<=30` txs forwarding
             `50%..105%` of a recent inflow across single or split legs);
           - Pattern B: Revolving Hub-and-Spoke / Ping-Pong Pool at ANY BNB/USD size (`eoa_fanout >= 8` with `>=2`
             bidirectional EOA spoke overlaps or `target_wallet` sweep-back).
        """
        f_low = funder_addr.lower()
        t_low = target_wallet.lower()
        fouts = [t for t in funder_txs if t.from_addr == f_low and t.to_addr != f_low and t.value_float > 0 and t.status == 1]
        eoa_fouts = [
            t for t in fouts
            if (
                t.category == "internal"
                or (t.category == "external" and (t.selector or "0x")[:10].lower() == "0x")
                or t.category == "20"
            )
            and t.to_addr not in KNOWN_BSC_PROTOCOLS
        ]
        fins = [
            t for t in funder_txs
            if t.to_addr == f_low
            and t.from_addr != f_low
            and t.value_float > 0
            and t.status == 1
        ]

        fanout = len({t.to_addr for t in fouts})
        eoa_fanout = len({t.to_addr for t in eoa_fouts})

        if cls._is_cex_hot_wallet(
            funder_addr=f_low,
            funder_tx_count=funder_tx_count,
            funder_txs=funder_txs,
            is_token_stream=is_token_stream,
            target_wallet=t_low,
        ):
            return fanout, 0, 0, False

        cand_outs = eoa_fouts if eoa_fouts else [t for t in fouts if t.to_addr not in KNOWN_BSC_PROTOCOLS]
        recip_totals: Dict[str, float] = {}
        for t in cand_outs:
            recip_totals[t.to_addr] = recip_totals.get(t.to_addr, 0.0) + t.value_float

        min_probe = 0.50 if is_token_stream else 0.0001
        probe_amounts: List[float] = []
        if first_bnb > 0:
            probe_amounts.append(first_bnb)
        for xv in extra_ref_amounts:
            if xv >= min_probe:
                probe_amounts.append(xv)
        for t in cand_outs:
            if t.to_addr == t_low and t.value_float >= min_probe:
                probe_amounts.append(t.value_float)
        if recip_totals.get(t_low, 0.0) >= min_probe:
            probe_amounts.append(recip_totals[t_low])

        same_dust = 0
        same_amount = 0
        for pv in probe_amounts:
            tol = max(0.01 if is_token_stream else 0.00005, pv * 0.05)
            leg_same_recips = len({t.to_addr for t in cand_outs if abs(t.value_float - pv) <= tol})
            tot_same_recips = len({r_a for r_a, r_tot in recip_totals.items() if abs(r_tot - pv) <= tol})
            distinct_same_recipients = max(leg_same_recips, tot_same_recips)
            if not is_token_stream and pv < 0.005:
                same_dust = max(same_dust, leg_same_recips)
            same_amount = max(same_amount, distinct_same_recipients)

        f_timestamps = [t.timestamp for t in funder_txs if t.timestamp > 0]
        funder_span_sec = (max(f_timestamps) - min(f_timestamps)) if len(f_timestamps) >= 2 else 0
        same_tx_internal_out_hashes: Set[str] = {
            (t.tx_hash or "").lower() for t in fouts if t.category == "internal" and t.tx_hash
        }

        is_relay = False
        if f_low not in KNOWN_BSC_PROTOCOLS and f_low not in BATCH_DISPERSE_CONTRACTS and probe_amounts:
            # Pattern A: Pass-through relay shell (uses unique `eoa_fanout <= 7` and tests `probe_amounts` including
            # aggregated target outflow so split-leg relays `12 USDT in -> 6 x 1.95 USDT out` NEVER evade detection!)
            if (
                1 <= eoa_fanout <= 7
                and (
                    funder_span_sec < CAPITAL_SEASONING_WINDOW_SEC
                    or (eoa_fanout >= 2 and max(len(funder_txs), funder_tx_count) <= 30)
                )
                and fins
            ):
                for fin in fins:
                    if fin.from_addr == t_low:
                        continue
                    if (
                        fanout == 1
                        and fin.category == "internal"
                        and (fin.tx_hash or "").lower() in same_tx_internal_out_hashes
                    ):
                        continue
                    dt = (first_ts - fin.timestamp) if (first_ts > 0 and fin.timestamp > 0) else 0
                    if -60 <= dt <= CAPITAL_SEASONING_WINDOW_SEC and any(
                        0.50 * fin.value_float <= pv <= 1.05 * fin.value_float for pv in probe_amounts
                    ):
                        is_relay = True
                        break

            # Pattern B: Revolving Hub-and-Spoke / Ping-Pong Pool (`eoa_fanout >= 8`), OR Smart-Contract
            # `BounceFundVault` (`funder_tx_count <= 1`, evaluated across BOTH native BNB and ERC-20 hard streams so
            # cross-asset `BNB <-> USDT` & two-contract bounce vaults NEVER evade detection)!
            if not is_relay:
                all_hard_stream = list(cross_hard_txs) if cross_hard_txs is not None else list(funder_txs)
                all_hard_outs = [
                    t
                    for t in all_hard_stream
                    if t.from_addr == f_low
                    and t.to_addr != f_low
                    and t.value_float > 0
                    and t.status == 1
                    and t.to_addr not in KNOWN_BSC_PROTOCOLS
                ]
                all_hard_ins = [
                    t
                    for t in all_hard_stream
                    if t.to_addr == f_low
                    and t.from_addr != f_low
                    and t.value_float > 0
                    and t.status == 1
                    and t.from_addr not in KNOWN_BSC_PROTOCOLS
                ]
                eoa_recipients = {t.to_addr for t in eoa_fouts} | {t.to_addr for t in all_hard_outs}
                eoa_in_senders = (
                    {t.from_addr for t in fins if t.from_addr not in KNOWN_BSC_PROTOCOLS}
                    | {t.from_addr for t in all_hard_ins}
                )
                overlap = eoa_recipients & eoa_in_senders
                out_tx_pairs = {(t.to_addr, (t.tx_hash or "").lower()) for t in all_hard_outs if t.tx_hash}
                in_tx_pairs = {(t.from_addr, (t.tx_hash or "").lower()) for t in all_hard_ins if t.tx_hash}
                same_tx_bounce_spokes = {sp_a for (sp_a, _) in (out_tx_pairs & in_tx_pairs)}
                if (
                    (eoa_fanout >= 8 and (len(overlap) >= 2 or t_low in eoa_in_senders))
                    or (funder_tx_count <= 1 and len(same_tx_bounce_spokes) >= 1)
                    or (funder_tx_count <= 1 and eoa_fanout >= 2 and target_had_same_tx_outflow)
                ):
                    is_relay = True

        return fanout, same_dust, same_amount, is_relay

    @staticmethod
    def _extract_candidate_funders(
        addr_low: str,
        bnb_price_usd: float,
        transfers: Sequence[TransferEvent],
    ) -> Tuple[List[TransferEvent], Optional[TransferEvent], List[Tuple[str, float, TransferEvent]], List[Tuple[str, float, TransferEvent]]]:
        ext_bnb_events, _ext_tok_events, first_in, sec_candidates, tok_candidates = _extract_external_funding_envelope(
            addr_low=addr_low,
            bnb_price_usd=bnb_price_usd,
            transfers=transfers,
        )
        return ext_bnb_events, first_in, sec_candidates, tok_candidates

    def _query_funder_nonces_cached(self, addrs: Sequence[str], now_cache: float) -> Dict[str, int]:
        unique_addrs: List[str] = []
        out: Dict[str, int] = {}
        ttl = max(60, self.cache_ttl_sec)
        for a in addrs:
            a_low = (a or "").strip().lower()
            if not (a_low.startswith("0x") and len(a_low) == 42):
                continue
            cached_n = self._funder_nonce_cache.get(a_low)
            if cached_n is not None and (now_cache - cached_n[0]) <= ttl:
                out[a_low] = cached_n[1]
            elif a_low not in unique_addrs:
                unique_addrs.append(a_low)

        if unique_addrs:
            calls = [
                {"jsonrpc": "2.0", "method": "eth_getTransactionCount", "params": [addr_i, "latest"], "id": idx + 1}
                for idx, addr_i in enumerate(unique_addrs)
            ]
            batch_nonces = self._rpc_batch(calls)
            for addr_i, res_hex in zip(unique_addrs, batch_nonces):
                try:
                    n_val = int(res_hex, 16) if isinstance(res_hex, str) and res_hex.startswith("0x") else int(res_hex or 0)
                except Exception:
                    n_val = 0
                out[addr_i] = n_val
                if res_hex is not None:
                    self._funder_nonce_cache[addr_i] = (now_cache, n_val)
        return out

    def collect_raw_snapshot_bundle(self, target: str) -> Dict[str, Any]:
        """
        Fetches raw read-only BSC RPC + SPACE ID + NodeReal/Etherscan V2 transfer streams and funder histories
        into a pure JSON-serializable bundle (prior to Sybil/Track scoring interpretation).
        """
        raw = (target or "").strip()
        if not raw:
            raise ValueError("Empty address or .ai handle")

        nameapi_addr: Optional[str] = None
        if raw.lower().startswith("0x") and len(raw) == 42:
            addr_low = raw.lower()
        else:
            resolved_addr, nameapi_addr = self.resolve_handle_to_address(raw)
            if not resolved_addr:
                raise ValueError(f"Unregistered or unresolvable .ai handle: {normalize_handle(raw)}")
            addr_low = resolved_addr.lower()

        def _bal_call(token_ca: str, cid: int) -> Dict[str, Any]:
            return {
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [{"to": token_ca, "data": SELECTOR_BALANCE_OF + "000000000000000000000000" + addr_low[2:]}, "latest"],
                "id": cid,
            }

        vc_low = (self.verifying_contract or "").strip().lower()
        check_onchain_nonce = self._should_check_onchain_nonce()

        rpc_calls: List[Dict[str, Any]] = [
            {
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [{"to": SPACE_ID_AI_REGISTRY, "data": SELECTOR_HANDLE_OF + "000000000000000000000000" + addr_low[2:]}, "latest"],
                "id": 1,
            },
            {"jsonrpc": "2.0", "method": "eth_getTransactionCount", "params": [addr_low, "latest"], "id": 2},
            {"jsonrpc": "2.0", "method": "eth_getBalance", "params": [addr_low, "latest"], "id": 3},
            _bal_call(BSC_USDT, 4),
            _bal_call(BSC_USDC, 5),
            _bal_call(BSC_FDUSD, 6),
            _bal_call(BSC_WBNB, 7),
            {
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [{"to": PANCAKE_WBNB_USDT_PAIR, "data": SELECTOR_GET_RESERVES}, "latest"],
                "id": 8,
            },
        ]
        if check_onchain_nonce:
            rpc_calls.append({"jsonrpc": "2.0", "method": "eth_getCode", "params": [vc_low, "latest"], "id": 9})
            rpc_calls.append(
                {
                    "jsonrpc": "2.0",
                    "method": "eth_call",
                    "params": [{"to": vc_low, "data": SELECTOR_NONCES + "000000000000000000000000" + addr_low[2:]}, "latest"],
                    "id": 10,
                }
            )
        extra_stable_idx = len(rpc_calls)
        rpc_calls.extend(
            [
                _bal_call(BSC_USD1, extra_stable_idx + 1),
                _bal_call(BSC_DAI, extra_stable_idx + 2),
                _bal_call(BSC_BUSD, extra_stable_idx + 3),
            ]
        )

        batch_res = self._rpc_batch(rpc_calls)

        onchain_handle = ""
        if batch_res[0] and len(batch_res[0]) > 130:
            try:
                h_str = abi_decode(["string"], bytes.fromhex(batch_res[0][2:]))[0].strip()
                if h_str:
                    onchain_handle = normalize_handle(h_str)
            except Exception:
                pass

        if onchain_handle and nameapi_addr is None:
            _, nameapi_addr = self.resolve_handle_to_address(onchain_handle)

        tx_count = int(batch_res[1] or "0x0", 16)
        bnb_bal = int(batch_res[2] or "0x0", 16) / 1e18
        usdt_bal = int(batch_res[3] or "0x0", 16) / 1e18
        usdc_bal = int(batch_res[4] or "0x0", 16) / 1e18
        fdusd_bal = int(batch_res[5] or "0x0", 16) / 1e18
        wbnb_bal = int(batch_res[6] or "0x0", 16) / 1e18
        usd1_bal = int(batch_res[extra_stable_idx] or "0x0", 16) / 1e18 if len(batch_res) > extra_stable_idx else 0.0
        dai_bal = int(batch_res[extra_stable_idx + 1] or "0x0", 16) / 1e18 if len(batch_res) > extra_stable_idx + 1 else 0.0
        busd_bal = int(batch_res[extra_stable_idx + 2] or "0x0", 16) / 1e18 if len(batch_res) > extra_stable_idx + 2 else 0.0

        bnb_price_usd = FALLBACK_BNB_PRICE_USD
        bnb_price_source = "fallback_default"
        if batch_res[7] and len(batch_res[7]) >= 130:
            try:
                r0, r1, _ = abi_decode(["uint112", "uint112", "uint32"], bytes.fromhex(batch_res[7][2:]))
                if r1 > 0:
                    price_cand = float(r0) / float(r1)
                    if 100.0 <= price_cand <= 5000.0:
                        bnb_price_usd = price_cand
                        bnb_price_source = "pancakeswap_v2_wbnb_usdt"
            except Exception:
                pass

        contract_nonce = 0
        if check_onchain_nonce:
            contract_nonce = self.query_onchain_contract_nonce(
                addr_low,
                prefetched_code=batch_res[8],
                prefetched_nonce=batch_res[9],
            )

        captured_at = int(time.time())
        asc_raw, degraded_asc = self._fetch_nodereal_transfers(
            addr_low, ["external", "internal", "20"], order="asc", max_count=80
        )
        desc_all_raw: List[Dict[str, Any]] = []
        degraded_desc = False
        recent_window_truncated = False
        now_cutoff_72h = captured_at - CAPITAL_SEASONING_WINDOW_SEC

        if (len(asc_raw) >= 80 or tx_count > 40) and not degraded_asc:
            max_asc_ts = max((int(r.get("blockTimeStamp") or 0) for r in asc_raw), default=0)
            target_cutoff_ts = max(now_cutoff_72h, max_asc_ts)
            desc_page_key: Optional[str] = None
            min_desc_ts = captured_at + 1
            for _page_idx in range(3):
                desc_raw, page_deg, next_key, v2_trunc = self._fetch_nodereal_transfers_paged(
                    addr_low,
                    ["external", "internal", "20"],
                    order="desc",
                    max_count=100,
                    page_key=desc_page_key,
                    v2_page=1,
                    v2_max_pages=3,
                    v2_cutoff_ts=target_cutoff_ts,
                )
                if page_deg:
                    degraded_desc = True
                    break
                desc_all_raw.extend(desc_raw)
                if v2_trunc:
                    recent_window_truncated = True
                    desc_page_key = None
                    break
                page_ts = [int(r.get("blockTimeStamp") or 0) for r in desc_raw if int(r.get("blockTimeStamp") or 0) > 0]
                if page_ts:
                    min_desc_ts = min(min_desc_ts, min(page_ts))
                if not next_key or len(desc_raw) < 100 or min_desc_ts <= now_cutoff_72h or min_desc_ts <= max_asc_ts:
                    desc_page_key = None
                    break
                desc_page_key = next_key

            if not degraded_desc and desc_page_key is not None and min_desc_ts > now_cutoff_72h and min_desc_ts > max_asc_ts:
                recent_window_truncated = True

        # NodeReal Multi-Category Starvation Guard: When `tx_count` is large (e.g. `0xsun.ai` 264 external txs, or
        # an attacker spamming 100 zero-value external txs), NodeReal's combined `["external", "internal", "20"]`
        # query fills all 80/100 slots with `"external"` first and crowds out `"internal"` and `"20"`. Explicitly pull
        # starved `["internal", "20"]` streams so native-BNB & ERC-20 swap return legs and 72h inflows are NEVER starved!
        starved_cats = [
            c_name for c_name in ("internal", "20")
            if not any(str(r.get("category") or "") == c_name for r in asc_raw)
        ]
        if (
            len(asc_raw) >= 80
            and not degraded_asc
            and not degraded_desc
            and starved_cats
        ):
            asc_20_raw, deg_20_asc = self._fetch_nodereal_transfers(
                addr_low, starved_cats, order="asc", max_count=80
            )
            if deg_20_asc:
                degraded_asc = True
            else:
                asc_raw.extend(asc_20_raw)
                if len(asc_20_raw) >= 80 or tx_count > 40:
                    max_20_asc_ts = max((int(r.get("blockTimeStamp") or 0) for r in asc_20_raw), default=0)
                    tok_cutoff_ts = max(now_cutoff_72h, max_20_asc_ts)
                    d20_key: Optional[str] = None
                    min_d20_ts = captured_at + 1
                    for _p20 in range(3):
                        d20_rows, p20_deg, nxt_20, v2_20_trunc = self._fetch_nodereal_transfers_paged(
                            addr_low,
                            starved_cats,
                            order="desc",
                            max_count=100,
                            page_key=d20_key,
                            v2_page=1,
                            v2_max_pages=3,
                            v2_cutoff_ts=tok_cutoff_ts,
                        )
                        if p20_deg:
                            degraded_desc = True
                            break
                        desc_all_raw.extend(d20_rows)
                        if v2_20_trunc:
                            recent_window_truncated = True
                            d20_key = None
                            break
                        p20_ts = [int(r.get("blockTimeStamp") or 0) for r in d20_rows if int(r.get("blockTimeStamp") or 0) > 0]
                        if p20_ts:
                            min_d20_ts = min(min_d20_ts, min(p20_ts))
                        if not nxt_20 or len(d20_rows) < 100 or min_d20_ts <= now_cutoff_72h or min_d20_ts <= max_20_asc_ts:
                            d20_key = None
                            break
                        d20_key = nxt_20
                    if not degraded_desc and d20_key is not None and min_d20_ts > now_cutoff_72h and min_d20_ts > max_20_asc_ts:
                        recent_window_truncated = True

        transfers = self._merge_transfer_streams(asc_raw, desc_all_raw)
        ext_bnb_events, first_in, sec_candidates, tok_candidates = self._extract_candidate_funders(
            addr_low=addr_low,
            bnb_price_usd=bnb_price_usd,
            transfers=transfers,
        )

        funder = first_in.from_addr if first_in else ""
        first_cat = first_in.category if first_in else ""
        funder_deg = False
        secondary_funder_deg = False
        stable_funder_deg = False
        now_cache = time.time()

        funder_streams: Dict[str, Dict[str, Any]] = {}

        def _ensure_funder_entry(fa: str) -> Dict[str, Any]:
            if fa not in funder_streams:
                funder_streams[fa] = {"txCount": 0, "bnbTxs": None, "erc20Txs": None}
            return funder_streams[fa]

        def _fetch_cached_funder_txs(
            f_addr: str,
            f_cats: List[str],
            cache_prefix: str,
            allow_empty: bool = False,
        ) -> Tuple[List[TransferEvent], bool]:
            ckey = f"{cache_prefix}:{f_addr}" if cache_prefix else f_addr
            cached_entry = self._funder_tx_cache.get(ckey)
            if cached_entry is not None and (now_cache - cached_entry[0]) <= max(60, self.cache_ttl_sec):
                return cached_entry[1], False
            f_raw, f_deg = self._fetch_nodereal_transfers(f_addr, f_cats, order="desc", max_count=80)
            f_parsed = self._parse_transfers(f_raw) if not f_deg else []
            if not f_deg and len(f_parsed) == 0 and not allow_empty:
                f_deg = True
            if not f_deg and (len(f_parsed) > 0 or allow_empty):
                self._funder_tx_cache[ckey] = (now_cache, f_parsed)
            return f_parsed, f_deg

        cand_addrs_all: List[str] = []
        if funder and funder not in BATCH_DISPERSE_CONTRACTS:
            cand_addrs_all.append(funder)
        for sec_addr_k, _, _ in sec_candidates:
            if sec_addr_k not in cand_addrs_all:
                cand_addrs_all.append(sec_addr_k)
        for sf_addr_k, _, _ in tok_candidates:
            if sf_addr_k not in cand_addrs_all:
                cand_addrs_all.append(sf_addr_k)
        nonce_map = (
            self._query_funder_nonces_cached(cand_addrs_all, now_cache=now_cache)
            if (cand_addrs_all and not degraded_asc and not degraded_desc)
            else {}
        )
        same_tx_outbound_hashes: Set[str] = {
            (t.tx_hash or "").lower()
            for t in transfers
            if t.status == 1 and t.from_addr == addr_low and t.to_addr != addr_low and t.tx_hash
        }
        inflow_hashes_by_funder: Dict[str, Set[str]] = {}
        has_erc20_with_funder: Set[str] = set()
        has_bnb_with_funder: Set[str] = set()
        for t in transfers:
            if t.status != 1 or t.value_float <= 0:
                continue
            if t.to_addr == addr_low and t.tx_hash:
                inflow_hashes_by_funder.setdefault(t.from_addr, set()).add(t.tx_hash.lower())
            if t.category == "20":
                has_erc20_with_funder.add(t.from_addr)
                has_erc20_with_funder.add(t.to_addr)
            elif t.category in ("external", "internal"):
                has_bnb_with_funder.add(t.from_addr)
                has_bnb_with_funder.add(t.to_addr)

        if funder and funder not in BATCH_DISPERSE_CONTRACTS and not degraded_asc and not degraded_desc:
            funder_cats = ["external", "internal"] if first_cat == "internal" else ["external"]
            funder_txs, funder_deg = _fetch_cached_funder_txs(funder, funder_cats, "int" if first_cat == "internal" else "")
            if not funder_deg:
                _ensure_funder_entry(funder)["bnbTxs"] = [ev.to_dict() for ev in funder_txs]
                need_cross_20 = (
                    int(nonce_map.get(funder, 0)) <= 1
                    or bool(inflow_hashes_by_funder.get(funder, set()) & same_tx_outbound_hashes)
                )
                if need_cross_20:
                    f_20_txs, f_20_deg = _fetch_cached_funder_txs(
                        funder, ["20"], "erc20", allow_empty=(funder not in has_erc20_with_funder)
                    )
                    if f_20_deg:
                        funder_deg = True
                    else:
                        _ensure_funder_entry(funder)["erc20Txs"] = [ev.to_dict() for ev in f_20_txs]

        if not degraded_asc and not degraded_desc and not funder_deg:
            for sec_addr, _sec_tot, sec_ev in sec_candidates:
                need_cross_sec = (
                    int(nonce_map.get(sec_addr, 0)) <= 1
                    or bool(inflow_hashes_by_funder.get(sec_addr, set()) & same_tx_outbound_hashes)
                )
                sec_cats = ["external", "internal"] if (sec_ev.category == "internal" or need_cross_sec) else ["external"]
                sec_txs, s_deg = _fetch_cached_funder_txs(
                    sec_addr, sec_cats, "int" if len(sec_cats) == 2 else ""
                )
                if s_deg:
                    secondary_funder_deg = True
                    break
                _ensure_funder_entry(sec_addr)["bnbTxs"] = [ev.to_dict() for ev in sec_txs]
                if need_cross_sec:
                    sec_20_txs, s20_deg = _fetch_cached_funder_txs(
                        sec_addr, ["20"], "erc20", allow_empty=(sec_addr not in has_erc20_with_funder)
                    )
                    if s20_deg:
                        secondary_funder_deg = True
                        break
                    _ensure_funder_entry(sec_addr)["erc20Txs"] = [ev.to_dict() for ev in sec_20_txs]

        if not degraded_asc and not degraded_desc and not funder_deg and not secondary_funder_deg:
            for sf_addr, _sf_tot_usd, _sf_ev in tok_candidates:
                sf_txs_all, sf_deg = _fetch_cached_funder_txs(sf_addr, ["20"], "erc20")
                if sf_deg:
                    stable_funder_deg = True
                    break
                _ensure_funder_entry(sf_addr)["erc20Txs"] = [ev.to_dict() for ev in sf_txs_all]
                need_cross_bnb = (
                    int(nonce_map.get(sf_addr, 0)) <= 1
                    or bool(inflow_hashes_by_funder.get(sf_addr, set()) & same_tx_outbound_hashes)
                )
                if need_cross_bnb and _ensure_funder_entry(sf_addr)["bnbTxs"] is None:
                    sf_bnb_txs, sfb_deg = _fetch_cached_funder_txs(
                        sf_addr, ["external", "internal"], "int", allow_empty=(sf_addr not in has_bnb_with_funder)
                    )
                    if sfb_deg:
                        stable_funder_deg = True
                        break
                    _ensure_funder_entry(sf_addr)["bnbTxs"] = [ev.to_dict() for ev in sf_bnb_txs]

        any_indexer_degraded = bool(
            degraded_asc or degraded_desc or funder_deg or secondary_funder_deg or stable_funder_deg
        )

        if funder_streams and not any_indexer_degraded:
            for fa_k, entry_v in funder_streams.items():
                entry_v["txCount"] = int(nonce_map.get(fa_k, 0))

        return {
            "schemaVersion": 1,
            "capturedAt": captured_at,
            "address": addr_low,
            "onchainHandle": onchain_handle,
            "nameapiAddress": nameapi_addr,
            "txCount": tx_count,
            "bnbBalance": bnb_bal,
            "wbnbBalance": wbnb_bal,
            "usdtBalance": usdt_bal,
            "usdcBalance": usdc_bal,
            "fdusdBalance": fdusd_bal,
            "usd1Balance": usd1_bal,
            "daiBalance": dai_bal,
            "busdBalance": busd_bal,
            "bnbPriceUSD": bnb_price_usd,
            "bnbPriceSource": bnb_price_source,
            "contractNonce": contract_nonce,
            "recentWindowTruncated": recent_window_truncated,
            "indexerDegraded": any_indexer_degraded,
            "transfers": [ev.to_dict() for ev in transfers],
            "funders": funder_streams,
        }

    @classmethod
    def build_snapshot_from_raw_bundle(cls, bundle: Mapping[str, Any]) -> WalletSnapshot:
        """
        Deterministically builds a `WalletSnapshot` (including CEX hot wallet exemption, primary/secondary
        BNB cluster/relay checks, and hard-token funder checks) purely from a raw snapshot bundle in memory.
        """
        addr_low = str(bundle["address"]).lower()
        bnb_price_usd = float(bundle.get("bnbPriceUSD") or FALLBACK_BNB_PRICE_USD)
        transfers = [TransferEvent.from_dict(item) for item in (bundle.get("transfers") or [])]
        any_indexer_degraded = bool(bundle.get("indexerDegraded"))
        funder_map: Mapping[str, Any] = bundle.get("funders") or {}

        ext_bnb_events, first_in, sec_candidates, tok_candidates = cls._extract_candidate_funders(
            addr_low=addr_low,
            bnb_price_usd=bnb_price_usd,
            transfers=transfers,
        )

        funder = first_in.from_addr if first_in else ""
        first_bnb = first_in.value_float if first_in else 0.0
        first_cat = first_in.category if first_in else ""
        first_sel = first_in.selector if first_in else "0x"
        first_ts = first_in.timestamp if first_in else 0
        primary_legs = [ev.value_float for ev in ext_bnb_events if funder and ev.from_addr == funder]
        primary_max_bnb = max(primary_legs, default=first_bnb)
        primary_tot_bnb = sum(primary_legs)

        funder_fanout = 0
        funder_same_dust = 0
        funder_same_amount = 0
        funder_is_relay = False
        funder_eoa_out = 0
        funder_tx_count = 0
        funder_is_cex = False
        secondary_funder_tainted = False
        stable_funder_tainted = False

        same_tx_out_hard_hashes: Set[str] = {
            (t.tx_hash or "").lower()
            for t in transfers
            if t.status == 1
            and t.from_addr == addr_low
            and t.to_addr != addr_low
            and t.to_addr != BSC_WBNB
            and (
                t.category == "external"
                or (t.value_float > 0 and t.category in ("internal", "20"))
            )
            and t.tx_hash
        }
        hard_in_hashes_by_funder: Dict[str, Set[str]] = {}
        for t in transfers:
            if (
                t.status == 1
                and t.value_float > 0
                and t.to_addr == addr_low
                and t.from_addr != addr_low
                and (t.category in ("external", "internal") or (t.category == "20" and t.contract_addr in HARD_LIQUID_TOKENS))
                and t.tx_hash
            ):
                hard_in_hashes_by_funder.setdefault(t.from_addr, set()).add(t.tx_hash.lower())

        if funder and funder not in BATCH_DISPERSE_CONTRACTS and not any_indexer_degraded:
            f_entry = funder_map.get(funder) or {}
            funder_tx_count = int(f_entry.get("txCount") or 0)
            raw_bnb_txs = f_entry.get("bnbTxs")
            raw_f_erc20 = f_entry.get("erc20Txs")
            if raw_bnb_txs is not None:
                funder_txs = [TransferEvent.from_dict(x) for x in raw_bnb_txs]
                f_erc20_all = [TransferEvent.from_dict(x) for x in (raw_f_erc20 or [])]
                f_hard_erc20 = [t for t in f_erc20_all if t.contract_addr in HARD_LIQUID_TOKENS]
                funder_eoa_out = len(
                    {
                        t.to_addr
                        for t in funder_txs
                        if t.from_addr == funder
                        and t.to_addr != funder
                        and t.value_float > 0
                        and t.status == 1
                        and (t.category == "internal" or (t.selector or "0x")[:10].lower() == "0x")
                        and t.to_addr not in KNOWN_BSC_PROTOCOLS
                    }
                )
                funder_is_cex = cls._is_cex_hot_wallet(
                    funder_addr=funder,
                    funder_tx_count=funder_tx_count,
                    funder_txs=funder_txs,
                    is_token_stream=False,
                    target_wallet=addr_low,
                )
                funder_fanout, funder_same_dust, funder_same_amount, funder_is_relay = (
                    cls._detect_funder_cluster_and_relay(
                        funder_addr=funder,
                        target_wallet=addr_low,
                        first_bnb=first_bnb,
                        first_ts=first_ts,
                        funder_txs=funder_txs,
                        funder_tx_count=funder_tx_count,
                        is_token_stream=False,
                        extra_ref_amounts=(primary_max_bnb, primary_tot_bnb),
                        cross_hard_txs=list(funder_txs) + f_hard_erc20,
                        target_had_same_tx_outflow=bool(
                            hard_in_hashes_by_funder.get(funder, set()) & same_tx_out_hard_hashes
                        ),
                    )
                )

        if not any_indexer_degraded:
            for sec_addr, sec_tot, sec_ev in sec_candidates:
                s_entry = funder_map.get(sec_addr) or {}
                s_nonce = int(s_entry.get("txCount") or 0)
                s_raw_txs = s_entry.get("bnbTxs")
                s_raw_20 = s_entry.get("erc20Txs")
                if s_raw_txs is None:
                    continue
                sec_txs = [TransferEvent.from_dict(x) for x in s_raw_txs]
                sec_20_all = [TransferEvent.from_dict(x) for x in (s_raw_20 or [])]
                sec_hard_20 = [t for t in sec_20_all if t.contract_addr in HARD_LIQUID_TOKENS]
                s_fanout, s_dust, s_same, s_relay = cls._detect_funder_cluster_and_relay(
                    funder_addr=sec_addr,
                    target_wallet=addr_low,
                    first_bnb=sec_ev.value_float,
                    first_ts=sec_ev.timestamp,
                    funder_txs=sec_txs,
                    funder_tx_count=s_nonce,
                    is_token_stream=False,
                    extra_ref_amounts=(sec_tot,),
                    cross_hard_txs=list(sec_txs) + sec_hard_20,
                    target_had_same_tx_outflow=bool(
                        hard_in_hashes_by_funder.get(sec_addr, set()) & same_tx_out_hard_hashes
                    ),
                )
                s_eoa_outs = max(
                    1,
                    len(
                        {
                            t.to_addr
                            for t in sec_txs
                            if t.from_addr == sec_addr
                            and t.to_addr != sec_addr
                            and t.value_float > 0
                            and t.status == 1
                            and (t.category == "internal" or (t.selector or "0x")[:10].lower() == "0x")
                            and t.to_addr not in KNOWN_BSC_PROTOCOLS
                        }
                    ),
                )
                s_batch = (
                    (0 < sec_ev.value_float < 0.005 and s_dust >= 3)
                    or (
                        s_fanout >= 5
                        and s_same >= 5
                        and (s_same / s_eoa_outs >= 0.30 or s_same >= 10 or sec_ev.value_float < 0.05)
                    )
                )
                if s_relay or s_batch:
                    secondary_funder_tainted = True
                    break

            self_called_dapp_hashes: Set[Tuple[str, str]] = {
                ((t.tx_hash or "").lower(), t.to_addr)
                for t in transfers
                if t.status == 1 and t.category == "external" and t.from_addr == addr_low and t.tx_hash
            }
            raw_portfolio_usd = (
                (float(bundle.get("bnbBalance") or 0.0) + float(bundle.get("wbnbBalance") or 0.0)) * bnb_price_usd
                + float(bundle.get("usdtBalance") or 0.0)
                + float(bundle.get("usdcBalance") or 0.0)
                + float(bundle.get("fdusdBalance") or 0.0)
                + float(bundle.get("usd1Balance") or 0.0)
                + float(bundle.get("daiBalance") or 0.0)
                + float(bundle.get("busdBalance") or 0.0)
            )
            untainted_primary_ok = (not funder_is_relay) and (
                funder_is_cex or (primary_tot_bnb * bnb_price_usd >= 25.0 and funder_same_amount < 5)
            )

            for sf_addr, sf_tot_usd, sf_ev in tok_candidates:
                sf_entry = funder_map.get(sf_addr) or {}
                sf_nonce = int(sf_entry.get("txCount") or 0)
                sf_raw_txs = sf_entry.get("erc20Txs")
                sf_raw_bnb = sf_entry.get("bnbTxs")
                if sf_raw_txs is None:
                    continue
                sf_txs_all = [TransferEvent.from_dict(x) for x in sf_raw_txs]
                sf_bnb_txs = [TransferEvent.from_dict(x) for x in (sf_raw_bnb or [])]
                sf_txs = [t for t in sf_txs_all if t.contract_addr in HARD_LIQUID_TOKENS]
                sf_unit_tot = (
                    sf_tot_usd / max(bnb_price_usd, 1.0) if sf_ev.contract_addr == BSC_WBNB else sf_tot_usd
                )
                sf_fanout, _, sf_same, sf_relay = cls._detect_funder_cluster_and_relay(
                    funder_addr=sf_addr,
                    target_wallet=addr_low,
                    first_bnb=sf_ev.value_float,
                    first_ts=sf_ev.timestamp,
                    funder_txs=sf_txs,
                    funder_tx_count=sf_nonce,
                    is_token_stream=True,
                    extra_ref_amounts=(sf_unit_tot,),
                    cross_hard_txs=list(sf_txs) + list(sf_bnb_txs),
                    target_had_same_tx_outflow=bool(
                        hard_in_hashes_by_funder.get(sf_addr, set()) & same_tx_out_hard_hashes
                    ),
                )
                sf_sel = (sf_ev.selector or "0x")[:10].lower()
                is_self_claimed_dapp_contract = (
                    sf_nonce == 1
                    and sf_fanout >= 10
                    and sf_same < 5
                    and ((sf_ev.tx_hash or "").lower(), sf_addr) in self_called_dapp_hashes
                    and sf_sel not in ("0x", "0xa9059cbb", "0x23b872dd")
                    and sf_sel not in BATCH_DISPERSE_SELECTORS
                    and not any(t.from_addr == addr_low and t.to_addr == sf_addr for t in sf_txs)
                    and untainted_primary_ok
                    and (raw_portfolio_usd - sf_tot_usd) >= 50.0
                )
                if is_self_claimed_dapp_contract:
                    continue
                sf_eoa_outs = max(
                    1,
                    len(
                        {
                            t.to_addr
                            for t in sf_txs
                            if t.from_addr == sf_addr
                            and t.to_addr != sf_addr
                            and t.value_float > 0
                            and t.status == 1
                            and t.to_addr not in KNOWN_BSC_PROTOCOLS
                        }
                    ),
                )
                if sf_relay or (sf_fanout >= 5 and sf_same >= 5 and (sf_same / sf_eoa_outs >= 0.30 or sf_same >= 10)):
                    stable_funder_tainted = True
                    break

        return WalletSnapshot(
            address=addr_low,
            onchain_handle=str(bundle.get("onchainHandle") or ""),
            nameapi_address=bundle.get("nameapiAddress"),
            tx_count=int(bundle.get("txCount") or 0),
            bnb_balance=float(bundle.get("bnbBalance") or 0.0),
            wbnb_balance=float(bundle.get("wbnbBalance") or 0.0),
            usdt_balance=float(bundle.get("usdtBalance") or 0.0),
            usdc_balance=float(bundle.get("usdcBalance") or 0.0),
            fdusd_balance=float(bundle.get("fdusdBalance") or 0.0),
            bnb_price_usd=bnb_price_usd,
            bnb_price_source=str(bundle.get("bnbPriceSource") or "fallback_default"),
            transfers=transfers,
            funder_address=funder,
            first_funding_bnb=first_bnb,
            first_funding_category=first_cat,
            first_funding_selector=first_sel,
            first_funding_timestamp=first_ts,
            funder_fanout_50=funder_fanout,
            funder_same_dust_50=funder_same_dust,
            funder_same_amount_50=funder_same_amount,
            funder_is_relay_pass_through=funder_is_relay,
            contract_nonce=int(bundle.get("contractNonce") or 0),
            indexer_degraded=any_indexer_degraded,
            funder_eoa_out_50=funder_eoa_out,
            stable_funder_tainted=stable_funder_tainted,
            secondary_funder_tainted=secondary_funder_tainted,
            recent_window_truncated=bool(bundle.get("recentWindowTruncated")),
            funder_tx_count=funder_tx_count,
            funder_is_cex_hot_wallet=funder_is_cex,
            usd1_balance=float(bundle.get("usd1Balance") or 0.0),
            dai_balance=float(bundle.get("daiBalance") or 0.0),
            busd_balance=float(bundle.get("busdBalance") or 0.0),
        )

    def collect_live_snapshot(self, target: str) -> WalletSnapshot:
        bundle = self.collect_raw_snapshot_bundle(target)
        return self.build_snapshot_from_raw_bundle(bundle)

    def evaluate(self, target: str, use_cache: bool = True) -> Dict[str, Any]:
        key = (target or "").strip().lower()
        now = time.time()
        if use_cache and key in self._cache:
            ts, cached_val = self._cache[key]
            if now - ts <= self.cache_ttl_sec:
                # Live Nonce Sync Guard: Even on a 180s cache hit, verify on-chain `nonces(address)` (`0x7ecebe00`)
                # so immediate post-mint renewal (nonce 0 -> 1) NEVER reuses a stale nonce signature!
                if self._should_check_onchain_nonce():
                    live_nonce = self.query_onchain_contract_nonce(cached_val["addressLower"])
                    if live_nonce != int(cached_val["eip712"]["payload"]["nonce"]):
                        refreshed = refresh_report_attestation(
                            cached_val,
                            nonce=live_nonce,
                            verifying_contract=self.verifying_contract,
                        )
                        self._cache[key] = (ts, refreshed)
                        self._cache[refreshed["addressLower"]] = (ts, refreshed)
                        if refreshed["handle"]:
                            self._cache[refreshed["handle"]] = (ts, refreshed)
                        return refreshed
                return cached_val

        snap = self.collect_live_snapshot(target)
        report = score_wallet_snapshot(snap, verifying_contract=self.verifying_contract)
        # Never cache transient indexer-degraded or funder-degraded results so subsequent retries recover immediately
        if not report.get("historyUnverified"):
            self._cache[key] = (now, report)
            self._cache[report["addressLower"]] = (now, report)
            if report["handle"]:
                self._cache[report["handle"]] = (now, report)
        return report


def format_cli_report(res: Dict[str, Any]) -> str:
    dims = res["dimensions"]
    d1, d2, d3, d4 = dims["d1Funding"], dims["d2Temporal"], dims["d3Economic"], dims["d4Proof"]
    gate_str = "PASS (isLiveAgent >= 60 -> TRUE)" if res["isLiveAgent60"] else "BLOCKED (isLiveAgent >= 60 -> FALSE)"
    lines = [
        "=" * 74,
        f"AgentPulse 4D Liveness Audit | {res['handle'] or '[NO .ai BOUND]'}",
        "=" * 74,
        f"Wallet Address : {res['address']}",
        f"Total Score    : {res['totalScore']} / 100  [{res['tier']}] {res['verdictLabel']}",
        f"B2B Gate Check : {gate_str}",
        "-" * 74,
        f"  [D1] 资金同源树与反聚类 : {d1['score']:2d} / 30 | 首笔入金={d1['firstFundingBNB']:.5f} BNB | 母钱包同额扇出={d1['funderSameDust50']}",
        f"  [D2] 时间跨度与间隔熵   : {d2['score']:2d} / 25 | 交易={d2['txCount']}笔 | 跨度={d2['spanDays']}天 | 熵={d2['entropyBits']}bit (CV={d2['intervalCV']})",
        f"  [D3] 真实经济摩擦与留存 : {d3['score']:2d} / 30 | 协议={','.join(d3['protocolsHit']) or 'NONE'} | 留存≈{d3['retainedUSD']:.2f} USD (72h沉淀≈{d3.get('seasonedRetainedUSD', d3['retainedUSD']):.2f} USD, BNB@{d3['bnbPriceUSD']:.2f})",
        f"  [D4] EIP-712 链上存证   : {d4['score']:2d} / 15 | 合约={d4['registry']} | Nonce={d4['contractNonce']}",
        "-" * 74,
    ]
    if res.get("riskFlags"):
        lines.append(f"Risk Flags     : {', '.join(res['riskFlags'])}")
    lines.append(f"EIP-712 Digest : {res['eip712']['digest']}")
    lines.append(f"Verifier Sig   : {res['eip712']['signature'][:42]}... (signer={res['eip712']['verifierSigner']})")
    lines.append("=" * 74)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="AgentPulse 4D Deterministic Liveness Scorer for BSC .ai Agents")
    parser.add_argument("target", nargs="?", help="Wallet address (0x...) or SPACE ID handle (e.g. redkoi.ai)")
    parser.add_argument("--json", action="store_true", help="Output full machine-readable JSON including EIP-712 payload")
    parser.add_argument("--verifying-contract", type=str, default=DEFAULT_VERIFYING_CONTRACT, help="AgentPulseGate address")
    args = parser.parse_args()

    if not args.target:
        parser.print_help()
        return 1

    scorer = AgentLivenessScorer(verifying_contract=args.verifying_contract)
    try:
        res = scorer.evaluate(args.target)
    except Exception as exc:
        err_payload = {"ok": False, "target": args.target, "error": str(exc)}
        if args.json:
            print(json.dumps(err_payload, indent=2, ensure_ascii=False))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print(format_cli_report(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
