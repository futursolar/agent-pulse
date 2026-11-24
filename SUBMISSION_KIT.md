# AgentPulse — Official Hackathon Submission Kit (EN / 中文双语填表包)

> **Target Event:** BNB Chain × Binance Wallet `.ai` Agent ID Hackathon (60,000 USDC Total Pool + 2,000 USDC Community Promo Pool)
> **Deadline:** 2026-12-09 16:00 (UTC+8)
> **Main Project Submission Form:** `https://app.binance.com/uni-qr/user-survey/fb26d2bd25e04329b1ba77c7b3811d23`
> **Community Promotion Form (2,000 USDC Pool):** `https://app.binance.com/uni-qr/user-survey/ff6832f8d2984af289068c9450a3c98c`

---

## Part A — Standard Form Fields (Copy-Paste Ready)

### 1. Project Name
```text
AgentPulse
```
*(Compliant with official branding rules: independent brand name, zero misuse of Binance / BNB trademarks.)*

### 2. Live Website / Demo URL
```text
https://futursolar.github.io/agent-pulse/
```

### 2b. 60s Product Demo Video URL (1080p MP4)
```text
https://futursolar.github.io/agent-pulse/demo/agent-pulse-demo.mp4
```

### 3. Open-Source GitHub Repository URL
```text
https://github.com/futursolar/agent-pulse
```

### 4. Smart Contract Address (BNB Smart Chain Mainnet, ChainID 56 — LIVE DEPLOYED)
```text
0x6cC807d492D8a10A16E5A7309d408801aaD025B5
```
- **Deployment TxHash (Block `135429223`):** `0x67a82cbaa39ac0455b06ac860cd33d810ff1d166b2380943c925bf61d12d8444`
- **Live Mainnet Attestation TxHash (`PULSE-SBT #1`, Block `135461669`):** `0xdf3395fcbaee5376602f17fb3a3f9255a4e3251e4d42e2f315716364ab88aee5` *(Executed natively via Binance Agentic Wallet CLI `baw v1.12.0 contract-call` for `redkoi.ai`: `totalScore = 84/100`, `uniqueAttestedAgents = 1`, `isLiveAgent(..., 60) = true`, `ERC-5192 locked(1) = true`, zero risk flags)*
- **Official SPACE ID `.ai` Registry Integrated:** `0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F`
- **Isolated Deployer (`owner`, `nonce=0`):** `0x46C4732D496b4f4d10aA41BA4164d89fF1d3b54D`
- **Isolated EIP-712 `verifierSigner`:** `0x55c69DED9987840718186164dE1947486163a2Bc`
- **Compiler / EVM / License:** `solc v0.8.24+commit.e11b9ed9` · Optimizer `200 runs` · `evmVersion = paris` · `MIT`
- **Open-Source Verification (BscScan + Sourcify Dual Verified):**
  - **BscScan Verified (`Pass - Verified`):** `https://bscscan.com/address/0x6cC807d492D8a10A16E5A7309d408801aaD025B5#code` (`GUID = zmwg7x9vfimhxhkptyuhsiyrmfsix5lvth63e288nvf3wz2mwc`)
  - **Sourcify V2 `exact_match`:** `matchId = 59824360` (`creationMatch = exact_match`, `runtimeMatch = exact_match`, verified `2026-11-24T08:18:23Z` at `https://sourcify.dev/server/v2/contract/56/0x6cC807d492D8a10A16E5A7309d408801aaD025B5`)

### 5. Author / Team Name
```text
RedKoi Research
```

---

## Part B — Short & Long Project Descriptions

### One-Sentence Pitch (EN)
> AgentPulse is a privacy-first Self-Check Liveness Attestation & 1-line B2B Sybil-Resistance Gate (`isLiveAgent`) for `.ai` Agent IDs on BNB Smart Chain — combining 4D deterministic on-chain physics with zero-approval ERC-5192 Soulbound proofs.

### 一句话简介（中文）
> AgentPulse 是面向 BNB Smart Chain `.ai` Agent ID 的隐私优先本人活体自检存证与一行代码 B2B 防女巫门禁（`isLiveAgent`），以四维确定性链上物理算法与零授权 ERC-5192 灵魂绑定徽章过滤批量粉尘女巫壳。

### Detailed Project Summary & Agent ID Integration Depth (EN — For Judges)
```text
1. Core Problem Solved:
Low-cost .ai Agent ID minting attracts automated Sybil farms (one mother wallet dispersing 0.0001 BNB dust to thousands of fresh wallets in 1-hour bursts with zero real protocol usage). Downstream BNB dApps, Launchpads, and airdrops need a trust-minimized way to verify whether a .ai holder is a genuine live agent without invasive KYC or hallucination-prone LLM scoring.

2. Deep Native Integration with SPACE ID .ai Agent ID (0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F):
- Off-chain & Browser RPC Layer: Queries both `ownerOfHandle(string)` (0x1da94fb4) and `handleOf(address)` (0xc50a1514) directly on BSC Mainnet to verify forward/reverse .ai binding consistency.
- Smart Contract Layer (`AgentPulseGate.sol`):
  * On `attestLiveness(payload, signature)`, the contract calls `ISpaceIdAiRegistry(0x60B9...022F).handleOf(msg.sender)` directly on-chain, normalizes the .ai handle, binds `keccak256(normalizedHandle)` + `nonces[msg.sender]++` inside the EIP-712 struct hash, and verifies `ecrecover` against `verifierSigner` before minting/updating an ERC-5192 Soulbound badge.
  * On `isLiveAgent(address user, uint8 minScore)`, the contract re-queries `handleOf(user)` live on SPACE ID so that if a user unbinds or transfers their .ai handle, `isLiveAgent` immediately flips to `false` with zero stale-badge bypass.

3. 4D Deterministic Physical Anti-Sybil Engine (0-100 pts, Zero LLM):
- D1 Funding Provenance & 72h Capital Seasoning (0-30): Detects mother-wallet 50-tx equal-dust fanout, 15s flash-rotated capital pools, and gas sweep-backs while recognizing legitimate CEX hot-wallet withdrawals.
- D2 Temporal Maturity & Interval Entropy (0-25): Enforces multi-day span gates and measures inter-transaction Shannon entropy (bits) + coefficient of variation (CV) to penalize fixed-interval cron bots.
- D3 Real Economic Friction & Net Retention (0-30): Counts only fee-bearing calls on whitelisted BSC protocols (DEX swaps, lending, prediction, staking, bridges) while assigning 0 pts to zero-value `approve()` spam and WBNB wrap/unwrap loops; prices live retention via PancakeSwap V2 WBNB/USDT reserves.
- D4 SPACE ID Binding & EIP-712 Proof (0-15): Enforces forward/reverse .ai handle consistency and anti-replay contract nonces.

4. Strict Privacy-Preserving Design (Anti-Doxxing Compliance):
AgentPulse is strictly positioned as a Self-Check Liveness Attestation & B2B Sybil Gate — NEVER a tool for looking up other people's wallets by name. Whenever `!connectedAccount || connectedAccount.toLowerCase() !== report.addressLower`, all wallet and funder 0x addresses are masked (`0x9556••••6A7f · Privacy-Masked`) across the UI, EIP-712 viewer, and static benchmark snapshots. Full addresses are displayed exclusively to the verified wallet owner upon connecting their wallet.
```

---

## Part C — Owner Permissions & Security Disclosure (Copy-Paste for Security Section)

```text
Contract: AgentPulseGate (0x6cC807d492D8a10A16E5A7309d408801aaD025B5, Solidity 0.8.24, MIT Open-Source, Non-Upgradeable)
Owner Address: 0x46C4732D496b4f4d10aA41BA4164d89fF1d3b54D (Isolated deployer)
Verifier Signer: 0x55c69DED9987840718186164dE1947486163a2Bc (Isolated EIP-712 oracle key)

Disclosed `onlyOwner` Functions (Exhaustive List):
1. `setVerifierSigner(address newSigner)`: Rotates the backend EIP-712 attestation signer address (reverts on `address(0)`). Cannot access user funds, cannot alter user balances, and cannot forge an attestation without a transaction initiated by `msg.sender` holding a live SPACE ID .ai handle.
2. `transferOwnership(address newOwner)`: Rotates or renounces admin ownership to a multisig (reverts on `address(0)`).

Hard Safety Guarantees:
- Zero Token Approvals: Never requests ERC-20 `approve`, `permit`, or NFT `setApprovalForAll`.
- Zero Fees & Zero Custody: `attestLiveness` is non-payable (`value = 0`); `receive()` and `fallback()` hard-revert with `ZeroValueOnly()`.
- Zero Backdoors: No proxy upgradeability, no `pause`, no `freeze`, no `blacklist`, no `mint-token`, no `withdraw`, and no `selfdestruct`.
- Soulbound Integrity: Implements ERC-5192 (`locked(tokenId) == true`); all transfer and approval methods revert with `SoulboundNonTransferable()`.
```

---

## Part D — Judge Demo Walkthrough Steps (60 Seconds)

```text
Step 1 (Zero-Connect Privacy-Masked Audit):
Open https://futursolar.github.io/agent-pulse/ (English UI by default; click "中文 / EN" in the top bar to switch languages). Click benchmark chips such as `redkoi.ai` (84/100, Track B Live Agent -> PASS) vs `m6n3b7v1.ai` (16/100, Sybil Dust Cluster -> BLOCK) or enter any live BSC `.ai` handle. Observe that third-party wallet and funder addresses remain strictly masked (`0x•••• · Privacy-Masked`), and when running serverless on GitHub Pages, the app seamlessly queries BSC JSON-RPC (`0x60B9...022F`) directly in the browser.

Step 2 (Self-Check Owner Verification & Soulbound Attestation):
Click "Connect Wallet (Self-Verify & Mint)" in Binance Wallet or any EVM browser wallet on BNB Smart Chain (`chainId = 56`). Once `connectedAccount` matches the `.ai` owner, the full wallet address unlocks for the owner, and clicking "Mint Soulbound Liveness Badge" submits a `0 BNB`, zero-approval `attestLiveness` call (`<$0.01` gas) to `AgentPulseGate` (`0x6cC807d492D8a10A16E5A7309d408801aaD025B5`).

Step 3 (B2B 1-Line Solidity Integration):
Any BNB Chain Launchpad, airdrop distributor, or agentic dApp calls `IAgentPulseGate(0x6cC807d492D8a10A16E5A7309d408801aaD025B5).isLiveAgent(msg.sender, 60)` to enforce real-time Sybil resistance backed by live `SPACE ID handleOf` verification.
```

---

## Part E — 10-Second BscScan Web Verification Fallback Bundle

If verifying manually on `https://bscscan.com/verifyContract` (without API key):
- **Contract Address:** `0x6cC807d492D8a10A16E5A7309d408801aaD025B5`
- **Compiler Type:** `Solidity (Single file)` -> upload/paste [`contracts/AgentPulseGate_flat.sol`](./contracts/AgentPulseGate_flat.sol)
- **Compiler Version:** `v0.8.24+commit.e11b9ed9`
- **Open Source License Type:** `3) MIT License (MIT)`
- **Optimization:** `Yes` (`200` runs) · **EVM Version:** `paris`
- **Constructor Arguments ABI-encoded (NO `0x` prefix):** see [`artifacts/constructor_arguments.txt`](./artifacts/constructor_arguments.txt)
  ```text
  00000000000000000000000055c69ded9987840718186164de1947486163a2bc0000000000000000000000000000000000000000000000000000000000000000
  ```
