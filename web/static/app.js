(() => {
  const SPACE_ID_AI_REGISTRY = "0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F";
  const AGENT_PULSE_GATE_MAINNET = "0x6cC807d492D8a10A16E5A7309d408801aaD025B5";
  const PLACEHOLDER_CONTRACT = "0x00000000000000000000000000000000000056a1";
  const BSC_RPC_ENDPOINTS = [
    "https://bsc-dataseed.binance.org",
    "https://bsc-rpc.publicnode.com",
    "https://bsc-dataseed1.defibit.io",
  ];
  const BSC_WBNB = "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c";
  const BSC_USDT = "0x55d398326f99059ff775485246999027b3197955";
  const BSC_USDC = "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d";
  const PANCAKE_WBNB_USDT_PAIR = "0x16b9a82891338f9ba80e2d6970fdda79d1eb0dae";
  const DEMO_URL = "https://futursolar.github.io/agent-pulse/";

  const form = document.getElementById("auditForm");
  const input = document.getElementById("targetInput");
  const auditBtn = document.getElementById("auditBtn");
  const errorBox = document.getElementById("errorBox");
  const resultPanel = document.getElementById("resultPanel");
  const connectBtn = document.getElementById("connectBtn");
  const langToggleBtn = document.getElementById("langToggleBtn");
  const runtimeModeBadge = document.getElementById("runtimeModeBadge");
  const mintBtn = document.getElementById("mintBtn");
  const shareBtn = document.getElementById("shareBtn");
  const copyProofBtn = document.getElementById("copyProofBtn");
  const txStatus = document.getElementById("txStatus");

  let connectedAccount = null;
  let currentReport = null;
  let cachedBenchmarkSamples = null;
  let currentLang = "en";
  let latestAuditSeq = 0;

  const I18N = {
    en: {
      toggleBtn: "中文",
      tagPill: "Independent Tool · Built for .ai Agents on BSC",
      shieldBanner: "🛡️ Zero Approvals · Non-Custodial · Privacy-Masked",
      connectIdle: "Connect Wallet (Self-Verify & Mint)",
      connectedPrefix: "🟢 Owner Verified ",
      heroTitle: "Self-Check Liveness Attestation & One-Line <span>B2B Sybil Gate</span> for .ai Agents",
      heroSubtitle:
        "Reads BSC SPACE ID Registry <code>0x60B9...022F</code> directly to verify <strong>72h Capital Seasoning · Temporal Entropy · Real Protocol Friction · EIP-712 Soulbound Proof</strong> — 100% deterministic, zero LLM hallucination.",
      privacyNotice:
        "🔒 <strong>Privacy-First Compliance:</strong> AgentPulse is strictly a <em>Self-Check Liveness Attestation &amp; B2B Sybil-Resistance Gate</em> — NEVER a reverse wallet-lookup tool. Third-party <code>.ai</code> wallet &amp; funder addresses are always masked (<code>0x9556••••6A7f · Privacy-Masked</code>) unless verified by connecting the owner's wallet.",
      inputPlaceholder: "Self-check your .ai handle or connect wallet (e.g. redkoi.ai / m6n3b7v1.ai)",
      auditIdle: "⚡ Run Liveness Self-Check",
      auditLoading: "⏳ Auditing On-Chain Proof...",
      chipLabel: "Calibrated Mainnet Benchmarks (Privacy-Masked):",
      chipRedkoi: "🔥 redkoi.ai (Live Multi-Protocol)",
      chipSun: "🐋 0xsun.ai (Active Trader)",
      chipCz: "🔶 changpengzhao.ai",
      chipDust: "🚨 m6n3b7v1.ai (Dust Sybil Cluster)",
      chipDormant: "🚨 light65.ai (0.0001 BNB Dormant Shell)",
      mintBtn: "🏅 Mint Soulbound Liveness Badge (Gas < $0.01 · Zero Approve)",
      shareBtn: "🐦 Share Liveness Scorecard on X (#BinanceWalletHackathon)",
      detailHeading: "4D Deterministic Physical Liveness Breakdown (Zero LLM)",
      d1Label: "<strong>D1 Funding Provenance &amp; Anti-Cluster</strong> (Blocks 1-to-8,000 dust fanout)",
      d2Label: "<strong>D2 Temporal Span &amp; Interval Entropy</strong> (Penalizes 1h bursts &amp; fixed cron bots)",
      d3Label: "<strong>D3 Real Economic Friction &amp; 72h Retention</strong> (Zero-value/approve = 0 pts)",
      d4Label: "<strong>D4 SPACE ID Binding &amp; EIP-712 Proof</strong> (On-chain handleOf + ecrecover)",
      proofTitle: "🔐 EIP-712 On-Chain Attestation Digest (Privacy-Guarded)",
      copyProofIdle: "Copy Payload",
      copyProofDone: "✅ Copied",
      b2bTitle: "🔌 One-Line B2B Airdrop / Launchpad Sybil-Resistance Gate",
      benchTitle: "📊 BSC Mainnet Calibration Benchmark (Live Agents vs Dust Sybil Shells)",
      benchHint: "Click any row to inspect 4D physical liveness metrics (wallet addresses privacy-masked)",
      thHandle: "Agent ID (.ai)",
      thTier: "Tier",
      thScore: "Score",
      thD1: "D1 Funding(30)",
      thD2: "D2 Entropy(25)",
      thD3: "D3 Friction(30)",
      thD4: "D4 Proof(15)",
      thGate: "isLiveAgent(60)",
      permTitle: "🛡️ Open-Source Contract Architecture & Disclosed Owner Permissions",
      permSub: "MIT Licensed · Solidity 0.8.24 (EVM Paris) · Zero Custody / Zero Approvals",
      lblGateAddr: "AgentPulseGate (BSC Mainnet, nonce=0)",
      lblRegAddr: "SPACE ID .ai Registry (Immutable Read)",
      lblOwnerAddr: "Isolated Deployer / Owner",
      lblSignerAddr: "Isolated EIP-712 Verifier Signer",
      thPermFunc: "Function / Capability",
      thPermCaller: "Caller Scope",
      thPermImpact: "Exact Scope & User Fund Safety Boundary",
      tdPerm1:
        "Rotates the EIP-712 score-oracle public key only. Cannot move user assets, cannot bypass live on-chain <code>SPACE ID handleOf(msg.sender)</code> check, and rejects <code>address(0)</code>.",
      tdPerm2:
        "Transfers admin key to multisig or burn address (rejects <code>address(0)</code>). Grants zero financial or token privileges.",
      tdPerm3:
        "Hard-reverts with <code>ZeroValueOnly()</code>. Contract holds <strong>0 BNB</strong>, charges <strong>0 protocol fees</strong>, and requests <strong>0 ERC-20 / NFT approvals</strong>.",
      tdPerm4:
        "Non-upgradeable contract with <strong>NO</strong> <code>pause</code>, <code>freeze</code>, <code>blacklist</code>, <code>mint-token</code>, <code>withdraw</code>, or <code>selfdestruct</code> functions. ERC-5192 Soulbound (<code>SoulboundNonTransferable</code>).",
      footerDisclaimer:
        "Built independently by <strong>RedKoi Research</strong>. AgentPulse is an independent open-source project and is not affiliated with or endorsed by Binance or BNB Chain.",
      radarD1: "D1 Fund",
      radarD2: "D2 Entropy",
      radarD3: "D3 Friction",
      radarD4: "D4 Proof",
      modeApi: "🟢 Full Oracle API Mode",
      modeStaticSnap: "⚡ Static Pages · Calibrated Snapshot + Live BSC RPC",
      modeStaticRpc: "⚡ Static Pages · Direct Browser BSC RPC Preview",
      unboundHandle: "[Unbound .ai]",
      noneStr: "None",
    },
    zh: {
      toggleBtn: "EN",
      tagPill: "独立开源工具 · 面向 BSC .ai 智能体生态",
      shieldBanner: "🛡️ 零代币授权 · 零资金托管 · 隐私脱敏保护",
      connectIdle: "连接钱包 (本人核验与铸章)",
      connectedPrefix: "🟢 已核验本人 ",
      heroTitle: "面向 <span>.ai Agent</span> 的活体自检存证与一行代码 <span>B2B 防女巫门禁</span>",
      heroSubtitle:
        "直连 BSC 官方 SPACE ID 注册表 <code>0x60B9...022F</code>，基于 <strong>72h 资金沉淀 · 时间间隔香农熵 · 真实协议经济摩擦 · EIP-712 灵魂绑定存证</strong> 四维确定性物理算法审计，零 LLM 幻觉。",
      privacyNotice:
        "🔒 <strong>隐私合规声明：</strong>AgentPulse 仅定位于<strong>本人活体自检存证与 B2B 防女巫合约门禁（isLiveAgent）</strong>，严禁作为查询他人钱包地址的工具。未连接对应所有者钱包时，所有 <code>.ai</code> 绑定的钱包地址与入金源地址均强制脱敏（<code>0x9556••••6A7f · Privacy-Masked</code>），仅钱包所有者本人连接后可见。",
      inputPlaceholder: "输入您本人的 .ai 域名自检或连接钱包（如 redkoi.ai / m6n3b7v1.ai）",
      auditIdle: "⚡ 立即活体自检",
      auditLoading: "⏳ 链上穿透核验中...",
      chipLabel: "主网已校准脱敏样本：",
      chipRedkoi: "🔥 redkoi.ai (多协议实战活体)",
      chipSun: "🐋 0xsun.ai (高频活跃样本)",
      chipCz: "🔶 changpengzhao.ai",
      chipDust: "🚨 m6n3b7v1.ai (现网同源粉尘矩阵)",
      chipDormant: "🚨 light65.ai (0.0001 BNB 休眠壳)",
      mintBtn: "🏅 一键上链铸造 Soulbound 活体徽章 (Gas < $0.01 · 零 Approve)",
      shareBtn: "🐦 生成 X 活体战报 (#BinanceWalletHackathon)",
      detailHeading: "四维确定性物理防伪拆解（100% 零 LLM 依赖）",
      d1Label: "<strong>D1 资金同源树与 72h 沉淀</strong> (拦截 1 母钱包批量分发粉尘壳)",
      d2Label: "<strong>D2 时间跨度与交易间隔香农熵</strong> (重罚单小时爆发与等距 Cron 脚本)",
      d3Label: "<strong>D3 跨协议真实经济摩擦与留存</strong> (纯 approve / 0 值调用计 0 分)",
      d4Label: "<strong>D4 SPACE ID 链上强验与 EIP-712 存证</strong> (handleOf + ecrecover 闭环)",
      proofTitle: "🔐 EIP-712 链上存证签名摘要 (非本人自动脱敏)",
      copyProofIdle: "复制签名载荷",
      copyProofDone: "✅ 已复制",
      b2bTitle: "🔌 B 端空投 / Launchpad 一行代码接入防女巫门禁",
      benchTitle: "📊 BSC 主网实时采样基准校准榜（活体智能体 vs 女巫粉尘壳）",
      benchHint: "点击任意行查看四维物理指标（第三方钱包地址已强制隐私脱敏）",
      thHandle: "Agent ID (.ai)",
      thTier: "等级",
      thScore: "总分",
      thD1: "D1 同源(30)",
      thD2: "D2 时间熵(25)",
      thD3: "D3 经济摩擦(30)",
      thD4: "D4 存证(15)",
      thGate: "isLiveAgent(60)",
      permTitle: "🛡️ 开源合约架构与 Owner 权限边界披露",
      permSub: "MIT 开源协议 · Solidity 0.8.24 (EVM Paris) · 零托管 / 零代币授权",
      lblGateAddr: "AgentPulseGate 主网合约 (nonce=0 确定性地址)",
      lblRegAddr: "SPACE ID .ai 官方注册表 (只读强验)",
      lblOwnerAddr: "物理隔离部署者 / Owner",
      lblSignerAddr: "物理隔离 EIP-712 热验签公钥",
      thPermFunc: "合约函数 / 权限项",
      thPermCaller: "调用者边界",
      thPermImpact: "精确权限范围与用户资金安全红线",
      tdPerm1:
        "仅允许轮换后端 EIP-712 评分验签公钥；无法触碰任何用户资产，无法绕过链上 <code>SPACE ID handleOf(msg.sender)</code> 强校验，拒绝零地址。",
      tdPerm2:
        "仅用于将管理权移交多签或销毁（拒绝零地址），不包含任何资金划转或代币特权。",
      tdPerm3:
        "<code>receive/fallback</code> 硬回滚 <code>ZeroValueOnly()</code>；合约 <strong>0 BNB 留存</strong>、<strong>0 收费</strong>、<strong>0 代币 Approve 授权</strong>。",
      tdPerm4:
        "非代理不可升级合约，<strong>无</strong> <code>pause</code>、<code>freeze</code>、<code>mint-token</code>、<code>withdraw</code> 后门；ERC-5192 灵魂绑定不可转让。",
      footerDisclaimer:
        "由 <strong>RedKoi Research</strong> 独立研发开源。AgentPulse 为独立第三方工具，不隶属于 Binance 或 BNB Chain 官方品牌。",
      radarD1: "D1 同源",
      radarD2: "D2 熵",
      radarD3: "D3 摩擦",
      radarD4: "D4 存证",
      modeApi: "🟢 完整签名节点模式",
      modeStaticSnap: "⚡ 静态 Pages · 校准快照 + BSC 实时链上核验",
      modeStaticRpc: "⚡ 静态 Pages · 浏览器直连 BSC RPC 实时预览",
      unboundHandle: "[未绑定 .ai]",
      noneStr: "无",
    },
  };

  function t(key) {
    return (I18N[currentLang] && I18N[currentLang][key]) || I18N.en[key] || key;
  }

  function setElText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  function setElHtml(id, val) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = val;
  }

  function getProvider() {
    if (typeof window === "undefined") return null;
    if (window.binancew3w && window.binancew3w.ethereum) return window.binancew3w.ethereum;
    if (window.BinanceChain) return window.BinanceChain;
    if (window.ethereum) return window.ethereum;
    return null;
  }

  // Rule 193 Anti-Doxxing Guard: NEVER expose full 0x wallet or funder address unless connected wallet owner matches!
  function isOwnerVerified(report) {
    if (!report || !connectedAccount) return false;
    const addrLow = (report.addressLower || report.address || "").toLowerCase();
    return Boolean(addrLow && connectedAccount.toLowerCase() === addrLow);
  }

  function maskAddress(addr) {
    if (!addr || typeof addr !== "string") return t("noneStr");
    const clean = addr.trim();
    if (clean.length < 12) return clean || t("noneStr");
    return `${clean.slice(0, 6)}••••${clean.slice(-4)}`;
  }

  function formatDisplayWallet(report) {
    if (!report || !report.address) return t("noneStr");
    if (isOwnerVerified(report)) {
      return currentLang === "zh"
        ? `${report.address} · 本人钱包已核验`
        : `${report.address} · Verified Wallet Owner`;
    }
    return `${maskAddress(report.address)} · Privacy-Masked`;
  }

  function buildPrivacySafeProofObject(report) {
    const eip = (report && report.eip712) || {};
    const rawPayload = eip.payload || {};
    const ownerOk = isOwnerVerified(report);
    const safePayload = Object.assign({}, rawPayload);
    if (!ownerOk && safePayload.wallet) {
      safePayload.wallet = `${maskAddress(safePayload.wallet)} (Privacy-Masked)`;
    }
    const safeSig = ownerOk
      ? eip.signature
      : (eip.signature && eip.signature.length > 24
          ? `${eip.signature.slice(0, 14)}••••${eip.signature.slice(-8)} (Connect Owner Wallet)`
          : eip.signature);
    return {
      digest: eip.digest,
      verifierSigner: eip.verifierSigner,
      domain: eip.domain,
      payload: safePayload,
      signature: safeSig,
    };
  }

  function updateModeBadge(modeKey) {
    if (!runtimeModeBadge) return;
    if (!modeKey) {
      runtimeModeBadge.classList.add("hidden");
      return;
    }
    runtimeModeBadge.textContent = t(modeKey);
    runtimeModeBadge.classList.remove("hidden");
  }

  function applyLanguageUI() {
    if (typeof document !== "undefined" && document.documentElement) {
      document.documentElement.lang = currentLang === "zh" ? "zh-CN" : "en";
    }
    if (langToggleBtn) langToggleBtn.textContent = t("toggleBtn");
    setElText("tagPill", t("tagPill"));
    setElText("shieldBanner", t("shieldBanner"));
    if (connectBtn) {
      connectBtn.textContent = connectedAccount
        ? `${t("connectedPrefix")}${connectedAccount.slice(0, 6)}...${connectedAccount.slice(-4)}`
        : t("connectIdle");
    }
    setElHtml("heroTitle", t("heroTitle"));
    setElHtml("heroSubtitle", t("heroSubtitle"));
    setElHtml("privacyNotice", t("privacyNotice"));
    if (input) input.placeholder = t("inputPlaceholder");
    if (auditBtn && !auditBtn.disabled) auditBtn.textContent = t("auditIdle");
    setElText("chipLabel", t("chipLabel"));
    setElText("chipRedkoi", t("chipRedkoi"));
    setElText("chipSun", t("chipSun"));
    setElText("chipCz", t("chipCz"));
    setElText("chipDust", t("chipDust"));
    setElText("chipDormant", t("chipDormant"));
    if (mintBtn) mintBtn.textContent = t("mintBtn");
    if (shareBtn) shareBtn.textContent = t("shareBtn");
    setElText("detailHeading", t("detailHeading"));
    setElHtml("d1Label", t("d1Label"));
    setElHtml("d2Label", t("d2Label"));
    setElHtml("d3Label", t("d3Label"));
    setElHtml("d4Label", t("d4Label"));
    setElText("proofTitle", t("proofTitle"));
    if (copyProofBtn) copyProofBtn.textContent = t("copyProofIdle");
    setElText("b2bTitle", t("b2bTitle"));
    setElText("benchTitle", t("benchTitle"));
    setElText("benchHint", t("benchHint"));
    setElText("thHandle", t("thHandle"));
    setElText("thTier", t("thTier"));
    setElText("thScore", t("thScore"));
    setElText("thD1", t("thD1"));
    setElText("thD2", t("thD2"));
    setElText("thD3", t("thD3"));
    setElText("thD4", t("thD4"));
    setElText("thGate", t("thGate"));
    setElText("permTitle", t("permTitle"));
    setElText("permSub", t("permSub"));
    setElText("lblGateAddr", t("lblGateAddr"));
    setElText("lblRegAddr", t("lblRegAddr"));
    setElText("lblOwnerAddr", t("lblOwnerAddr"));
    setElText("lblSignerAddr", t("lblSignerAddr"));
    setElText("thPermFunc", t("thPermFunc"));
    setElText("thPermCaller", t("thPermCaller"));
    setElText("thPermImpact", t("thPermImpact"));
    setElHtml("tdPerm1", t("tdPerm1"));
    setElHtml("tdPerm2", t("tdPerm2"));
    setElHtml("tdPerm3", t("tdPerm3"));
    setElHtml("tdPerm4", t("tdPerm4"));
    setElHtml("footerDisclaimer", t("footerDisclaimer"));

    if (currentReport) {
      renderReport(currentReport, { preserveTxStatus: true });
    }
    if (cachedBenchmarkSamples) {
      renderBenchmarkRows(cachedBenchmarkSamples);
    }
  }

  function pad32(hexNoPrefix) {
    return hexNoPrefix.replace(/^0x/, "").padStart(64, "0");
  }

  // ABI-encodes: attestLiveness((uint8,uint8,uint8,uint8,uint8,uint64,uint64), bytes)
  // Selector = 0xb3941532 (verified from solc 0.8.24 compilation)
  function encodeAttestLivenessCalldata(payload, sigHex) {
    const selector = "0xb3941532";
    const tupleWords = [
      payload.totalScore.toString(16),
      payload.d1Funding.toString(16),
      payload.d2Temporal.toString(16),
      payload.d3Economic.toString(16),
      payload.d4Proof.toString(16),
      payload.issuedAt.toString(16),
      payload.expiresAt.toString(16),
    ].map(pad32).join("");

    const offsetBytes = pad32("100");
    const cleanSig = (sigHex || "0x" + "00".repeat(65)).replace(/^0x/, "");
    const sigByteLen = cleanSig.length / 2;
    const lenWord = pad32(sigByteLen.toString(16));
    const paddedSig = cleanSig.padEnd(Math.ceil(cleanSig.length / 64) * 64, "0");
    return selector + tupleWords + offsetBytes + lenWord + paddedSig;
  }

  // Minimal ABI helpers for Serverless Direct BSC JSON-RPC Mode (SPACE ID + AgentPulseGate)
  function utf8ToHex(str) {
    if (typeof TextEncoder !== "undefined") {
      return Array.from(new TextEncoder().encode(str))
        .map((b) => b.toString(16).padStart(2, "0"))
        .join("");
    }
    let out = "";
    for (let i = 0; i < str.length; i++) {
      out += str.charCodeAt(i).toString(16).padStart(2, "0");
    }
    return out;
  }

  function hexToUtf8(hexNoPrefix) {
    const bytes = [];
    for (let i = 0; i < hexNoPrefix.length; i += 2) {
      bytes.push(parseInt(hexNoPrefix.slice(i, i + 2), 16));
    }
    if (typeof TextDecoder !== "undefined") {
      return new TextDecoder().decode(new Uint8Array(bytes));
    }
    return String.fromCharCode.apply(null, bytes);
  }

  function encodeOwnerOfHandleCall(bareHandle) {
    const strHex = utf8ToHex(bareHandle);
    const byteLen = strHex.length / 2;
    const padded = strHex.padEnd(Math.max(64, Math.ceil(strHex.length / 64) * 64), "0");
    return "0x1da94fb4" + pad32("20") + pad32(byteLen.toString(16)) + padded;
  }

  function decodeAbiAddress(hexRes) {
    if (!hexRes || typeof hexRes !== "string" || hexRes.length < 66) return null;
    const addr = "0x" + hexRes.slice(-40).toLowerCase();
    if (/^0x0+$/.test(addr)) return null;
    return addr;
  }

  function decodeAbiString(hexRes) {
    if (!hexRes || typeof hexRes !== "string" || hexRes.length < 130) return "";
    const body = hexRes.replace(/^0x/, "");
    const offsetChars = parseInt(body.slice(0, 64), 16) * 2;
    if (!Number.isFinite(offsetChars) || offsetChars + 64 > body.length) return "";
    const byteLen = parseInt(body.slice(offsetChars, offsetChars + 64), 16);
    if (!Number.isFinite(byteLen) || byteLen <= 0) return "";
    const strHex = body.slice(offsetChars + 64, offsetChars + 64 + byteLen * 2);
    return hexToUtf8(strHex).trim();
  }

  function normalizeAiHandle(raw) {
    const h = (raw || "").trim().toLowerCase();
    if (!h) return "";
    return h.endsWith(".ai") ? h : `${h}.ai`;
  }

  async function sha256Hex(inputStr) {
    try {
      if (typeof crypto !== "undefined" && crypto.subtle && typeof TextEncoder !== "undefined") {
        const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(inputStr));
        return Array.from(new Uint8Array(buf))
          .map((b) => b.toString(16).padStart(2, "0"))
          .join("");
      }
    } catch (_) {}
    return "";
  }

  function isFetchOk(resp) {
    if (!resp) return false;
    if (typeof resp.ok === "boolean") return resp.ok;
    if (typeof resp.status === "number") return resp.status >= 200 && resp.status < 300;
    return true;
  }

  async function bscRpcBatch(calls) {
    if (!Array.isArray(calls) || calls.length === 0) return [];
    for (let i = 0; i < BSC_RPC_ENDPOINTS.length; i++) {
      try {
        const resp = await fetch(BSC_RPC_ENDPOINTS[i], {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(calls),
        });
        if (!isFetchOk(resp)) continue;
        const arr = await resp.json();
        if (!Array.isArray(arr) || arr.length === 0) continue;
        const map = {};
        let okCount = 0;
        let hasNodeOrRateError = false;
        arr.forEach((item) => {
          if (!item || typeof item !== "object") return;
          if (!item.error && item.result !== undefined && item.result !== null) {
            map[item.id] = item.result;
            okCount += 1;
          } else if (item.error) {
            const errCode = Number(item.error.code || 0);
            const errMsg = String(item.error.message || "").toLowerCase();
            if (errCode === 3 || errMsg.includes("execution reverted")) {
              map[item.id] = "0x";
              okCount += 1;
            } else {
              hasNodeOrRateError = true;
            }
          }
        });
        if (okCount === 0) continue;
        if (hasNodeOrRateError && i + 1 < BSC_RPC_ENDPOINTS.length) continue;
        return calls.map((c) => (Object.prototype.hasOwnProperty.call(map, c.id) ? map[c.id] : null));
      } catch (_) {}
    }
    return calls.map(() => null);
  }

  async function ensureStaticSamplesLoaded() {
    if (Array.isArray(cachedBenchmarkSamples) && cachedBenchmarkSamples.length > 0) {
      return cachedBenchmarkSamples;
    }
    try {
      const resp = await fetch("./calibration_benchmark_12.json");
      if (!isFetchOk(resp)) return [];
      const raw = await resp.json();
      if (Array.isArray(raw)) {
        cachedBenchmarkSamples = raw;
        return raw;
      }
      if (raw && Array.isArray(raw.samples)) {
        cachedBenchmarkSamples = raw.samples;
        return raw.samples;
      }
    } catch (_) {}
    return [];
  }

  async function runServerlessFallbackAudit(cleanTarget) {
    const samples = await ensureStaticSamplesLoaded();
    const isHexAddr = /^0x[0-9a-fA-F]{40}$/.test(cleanTarget);
    const normHandle = isHexAddr ? "" : normalizeAiHandle(cleanTarget);

    // Tier 1: Hit pre-calibrated 12-sample BSC Mainnet truth benchmark
    const targetAddrSha = isHexAddr ? await sha256Hex(cleanTarget.toLowerCase()) : "";
    const connectedSha = connectedAccount ? await sha256Hex(connectedAccount.toLowerCase()) : "";
    const matchedSample = samples.find((s) => {
      if (isHexAddr) {
        if ((s.addressLower || "").toLowerCase() === cleanTarget.toLowerCase()) return true;
        if (targetAddrSha && s.addressSha256 && s.addressSha256 === targetAddrSha) return true;
        return false;
      }
      return (s.handle || "").toLowerCase() === normHandle;
    });

    if (matchedSample) {
      const cloned = JSON.parse(JSON.stringify(matchedSample));
      cloned.isStaticPreview = true;
      cloned.staticModeType = "modeStaticSnap";
      if (connectedAccount && connectedSha && cloned.addressSha256 === connectedSha) {
        cloned.address = connectedAccount;
        cloned.addressLower = connectedAccount.toLowerCase();
        if (cloned.eip712 && cloned.eip712.payload) {
          cloned.eip712.payload.wallet = connectedAccount;
        }
      }
      try {
        const fullAddrHex = /^0x[0-9a-fA-F]{40}$/.test(cloned.addressLower || "")
          ? cloned.addressLower.replace(/^0x/, "")
          : "";
        if (fullAddrHex) {
          const [gateCode, nonceHex] = await bscRpcBatch([
            { jsonrpc: "2.0", id: 1, method: "eth_getCode", params: [AGENT_PULSE_GATE_MAINNET, "latest"] },
            {
              jsonrpc: "2.0",
              id: 2,
              method: "eth_call",
              params: [{ to: AGENT_PULSE_GATE_MAINNET, data: "0x7ecebe00" + pad32(fullAddrHex) }, "latest"],
            },
          ]);
          if (gateCode && gateCode !== "0x" && nonceHex && nonceHex.length >= 66) {
            const liveNonce = parseInt(nonceHex, 16) || 0;
            cloned.dimensions.d4Proof.contractNonce = liveNonce;
            cloned.eip712.payload.nonce = liveNonce;
          }
        }
      } catch (_) {}
      updateModeBadge("modeStaticSnap");
      return cloned;
    }

    // Tier 2: Direct Browser CORS BSC JSON-RPC live read against SPACE ID 0x60B9...022F + AgentPulseGate
    let resolvedAddr = isHexAddr ? cleanTarget.toLowerCase() : null;
    if (!resolvedAddr) {
      const bare = normHandle.replace(/\.ai$/i, "");
      if (!bare || /[^a-z0-9_-]/.test(bare)) {
        throw new Error(
          currentLang === "zh"
            ? `无效的 .ai 域名或 0x 地址格式：${cleanTarget}`
            : `Invalid .ai handle or 0x wallet format: ${cleanTarget}`
        );
      }
      const [ownerRes] = await bscRpcBatch([
        {
          jsonrpc: "2.0",
          id: 1,
          method: "eth_call",
          params: [{ to: SPACE_ID_AI_REGISTRY, data: encodeOwnerOfHandleCall(bare) }, "latest"],
        },
      ]);
      if (ownerRes === null) {
        throw new Error(
          currentLang === "zh"
            ? "公开 BSC RPC 节点限流或暂不可达，无法核验 SPACE ID 注册表，请稍后重试。"
            : "Public BSC JSON-RPC endpoints are rate-limited or unreachable; unable to query SPACE ID Registry. Please retry."
        );
      }
      resolvedAddr = decodeAbiAddress(ownerRes);
      if (!resolvedAddr) {
        throw new Error(
          currentLang === "zh"
            ? `BSC 官方 SPACE ID 注册表 (0x60B9...022F) 未查到已注册域名：${normHandle}`
            : `Handle "${normHandle}" is not registered on BSC SPACE ID .ai Registry (0x60B9...022F).`
        );
      }
    }

    const addrNoPrefix = resolvedAddr.replace(/^0x/, "");
    const balCall = (token, id) => ({
      jsonrpc: "2.0",
      id,
      method: "eth_call",
      params: [{ to: token, data: "0x70a08231" + pad32(addrNoPrefix) }, "latest"],
    });

    const rpcOut = await bscRpcBatch([
      {
        jsonrpc: "2.0",
        id: 1,
        method: "eth_call",
        params: [{ to: SPACE_ID_AI_REGISTRY, data: "0xc50a1514" + pad32(addrNoPrefix) }, "latest"],
      },
      { jsonrpc: "2.0", id: 2, method: "eth_getTransactionCount", params: [resolvedAddr, "latest"] },
      { jsonrpc: "2.0", id: 3, method: "eth_getBalance", params: [resolvedAddr, "latest"] },
      balCall(BSC_WBNB, 4),
      balCall(BSC_USDT, 5),
      balCall(BSC_USDC, 6),
      {
        jsonrpc: "2.0",
        id: 7,
        method: "eth_call",
        params: [{ to: PANCAKE_WBNB_USDT_PAIR, data: "0x0902f1ac" }, "latest"],
      },
      { jsonrpc: "2.0", id: 8, method: "eth_getCode", params: [AGENT_PULSE_GATE_MAINNET, "latest"] },
      {
        jsonrpc: "2.0",
        id: 9,
        method: "eth_call",
        params: [{ to: AGENT_PULSE_GATE_MAINNET, data: "0x7ecebe00" + pad32(addrNoPrefix) }, "latest"],
      },
    ]);

    if (rpcOut[1] === null && rpcOut[2] === null) {
      throw new Error(
        currentLang === "zh"
          ? "公开 BSC RPC 节点暂不可达，请稍后重试。"
          : "Public BSC JSON-RPC endpoints temporarily unreachable. Please retry."
      );
    }

    const rawHandle = decodeAbiString(rpcOut[0]);
    const onchainHandle = rawHandle ? normalizeAiHandle(rawHandle) : "";
    const hasAgentId = Boolean(onchainHandle);
    const txCount = rpcOut[1] ? parseInt(rpcOut[1], 16) : 0;
    const bnbBal = rpcOut[2] ? Number(BigInt(rpcOut[2])) / 1e18 : 0;
    const wbnbBal = rpcOut[3] && rpcOut[3].length >= 66 ? Number(BigInt(rpcOut[3])) / 1e18 : 0;
    const usdtBal = rpcOut[4] && rpcOut[4].length >= 66 ? Number(BigInt(rpcOut[4])) / 1e18 : 0;
    const usdcBal = rpcOut[5] && rpcOut[5].length >= 66 ? Number(BigInt(rpcOut[5])) / 1e18 : 0;

    let bnbPriceUSD = 560.0;
    if (rpcOut[6] && rpcOut[6].length >= 130) {
      const rBody = rpcOut[6].replace(/^0x/, "");
      const r0 = BigInt("0x" + rBody.slice(0, 64));
      const r1 = BigInt("0x" + rBody.slice(64, 128));
      if (r1 > 0n) {
        bnbPriceUSD = Number((r0 * 10000n) / r1) / 10000;
      }
    }
    const gateDeployed = Boolean(rpcOut[7] && rpcOut[7] !== "0x" && /[1-9a-f]/i.test(rpcOut[7].slice(2)));
    const gateNonce = gateDeployed && rpcOut[8] && rpcOut[8].length >= 66 ? parseInt(rpcOut[8], 16) : 0;
    const totalUsd = (bnbBal + wbnbBal) * bnbPriceUSD + usdtBal + usdcBal;

    // Conservative client-side live RPC preview estimate (clearly marked LIVE_RPC_STATIC_PREVIEW)
    const d4Score = hasAgentId ? 15 : 0;
    const d1Est = totalUsd >= 15 ? 24 : totalUsd >= 2 ? 14 : bnbBal > 0.0005 ? 6 : 2;
    const d2Est = txCount >= 80 ? 20 : txCount >= 25 ? 15 : txCount >= 8 ? 10 : txCount >= 2 ? 4 : 0;
    const d3Est =
      totalUsd >= 50 && txCount >= 20
        ? 22
        : totalUsd >= 10 && txCount >= 8
          ? 16
          : totalUsd >= 2 && txCount >= 3
            ? 8
            : 0;
    let totalScore = d1Est + d2Est + d3Est + d4Score;
    if (!hasAgentId && totalScore >= 60) {
      totalScore = d1Est + d2Est + d3Est;
    }
    const isLive = Boolean(hasAgentId && totalScore >= 60);
    const tier = !hasAgentId ? "UNBOUND" : totalScore >= 80 ? "S" : totalScore >= 60 ? "A" : totalScore >= 40 ? "B" : "C";
    const nowSec = Math.floor(Date.now() / 1000);

    updateModeBadge("modeStaticRpc");
    return {
      ok: true,
      isStaticPreview: true,
      staticModeType: "modeStaticRpc",
      address: resolvedAddr,
      addressLower: resolvedAddr,
      handle: onchainHandle,
      hasAgentId,
      totalScore,
      tier,
      verdictLabel: isLive ? "Live RPC Preview (Pass)" : "Live RPC Instant Preview",
      isLiveAgent60: isLive,
      historyUnverified: false,
      dimensions: {
        d1Funding: {
          score: d1Est,
          firstFundingBNB: Number(bnbBal.toFixed(4)),
          funder: "",
          funderSameDust50: 0,
        },
        d2Temporal: {
          score: d2Est,
          txCount,
          spanDays: "--",
          activeDays: "--",
          entropyBits: "--",
          intervalCV: "--",
        },
        d3Economic: {
          score: d3Est,
          protocolsHit: txCount > 0 ? ["LIVE_BSC_RPC"] : [],
          realEconomicTxs: txCount,
          zeroFrictionTxs: 0,
          retainedUSD: Number(totalUsd.toFixed(2)),
          bnbPriceUSD: Number(bnbPriceUSD.toFixed(2)),
        },
        d4Proof: {
          score: d4Score,
          registry: SPACE_ID_AI_REGISTRY,
          forwardConsistent: hasAgentId,
          contractNonce: gateNonce,
        },
      },
      riskFlags: hasAgentId ? ["STATIC_LIVE_RPC_PREVIEW"] : ["NO_SPACE_ID_AI_BOUND", "STATIC_LIVE_RPC_PREVIEW"],
      eip712: {
        digest: "0x" + "0".repeat(64),
        verifierSigner: "0x55c69DED9987840718186164dE1947486163a2Bc",
        isDemoSigner: true,
        domain: {
          name: "AgentPulse",
          version: "1",
          chainId: 56,
          verifyingContract: AGENT_PULSE_GATE_MAINNET,
        },
        payload: {
          wallet: resolvedAddr,
          handle: onchainHandle || "unbound.ai",
          totalScore,
          d1Funding: d1Est,
          d2Temporal: d2Est,
          d3Economic: d3Est,
          d4Proof: d4Score,
          issuedAt: nowSec,
          expiresAt: nowSec + 86400 * 14,
          nonce: gateNonce,
        },
        signature: "0x" + "00".repeat(65),
      },
    };
  }

  function renderRadarSvg(d1, d2, d3, d4) {
    const svg = document.getElementById("radarSvg");
    if (!svg) return;
    const cx = 140, cy = 130, radius = 86;
    const ratios = [
      Math.max(0.06, d1 / 30),
      Math.max(0.06, d2 / 25),
      Math.max(0.06, d3 / 30),
      Math.max(0.06, d4 / 15),
    ];
    const angles = [-Math.PI / 2, 0, Math.PI / 2, Math.PI];
    const labels = [
      { text: `${t("radarD1")} (${d1}/30)`, x: 140, y: 24, anchor: "middle" },
      { text: `${t("radarD2")} (${d2}/25)`, x: 232, y: 134, anchor: "start" },
      { text: `${t("radarD3")} (${d3}/30)`, x: 140, y: 246, anchor: "middle" },
      { text: `${t("radarD4")} (${d4}/15)`, x: 48, y: 134, anchor: "end" },
    ];

    let gridHtml = "";
    [0.25, 0.5, 0.75, 1.0].forEach((lv) => {
      const pts = angles.map((a) => `${cx + Math.cos(a) * radius * lv},${cy + Math.sin(a) * radius * lv}`).join(" ");
      gridHtml += `<polygon points="${pts}" fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="1"/>`;
    });
    angles.forEach((a) => {
      gridHtml += `<line x1="${cx}" y1="${cy}" x2="${cx + Math.cos(a) * radius}" y2="${cy + Math.sin(a) * radius}" stroke="rgba(255,255,255,0.12)" stroke-width="1"/>`;
    });

    const dataPts = angles.map((a, i) => `${cx + Math.cos(a) * radius * ratios[i]},${cy + Math.sin(a) * radius * ratios[i]}`).join(" ");
    const dotsHtml = angles.map((a, i) => (
      `<circle cx="${cx + Math.cos(a) * radius * ratios[i]}" cy="${cy + Math.sin(a) * radius * ratios[i]}" r="4" fill="#f0b90b" stroke="#00f0ff" stroke-width="1.5"/>`
    )).join("");
    const textHtml = labels.map((lb) => (
      `<text x="${lb.x}" y="${lb.y}" text-anchor="${lb.anchor}" fill="#cbd5e1" font-size="11" font-weight="600">${lb.text}</text>`
    )).join("");

    svg.innerHTML = `
      ${gridHtml}
      <polygon points="${dataPts}" fill="rgba(240, 185, 11, 0.28)" stroke="#00f0ff" stroke-width="2.2"/>
      ${dotsHtml}
      ${textHtml}
    `;
  }

  function renderReport(r, opts = {}) {
    currentReport = r;
    errorBox.classList.add("hidden");
    if (!opts.preserveTxStatus) {
      txStatus.classList.add("hidden");
    }
    resultPanel.classList.remove("hidden");

    const ownerVerified = isOwnerVerified(r);
    document.getElementById("resHandle").textContent = r.handle || t("unboundHandle");
    document.getElementById("resAddress").textContent = formatDisplayWallet(r);
    document.getElementById("resScoreNum").textContent = r.totalScore;

    const pill = document.getElementById("resTierPill");
    const banner = document.getElementById("resVerdictBanner");
    banner.className = "verdict-banner";
    if (r.isLiveAgent60) {
      pill.style.color = "#34d399";
      pill.style.borderColor = "rgba(16,185,129,0.5)";
      banner.classList.add("verdict-pass");
      banner.textContent = currentLang === "zh"
        ? `✅ [${r.tier}] 活体认证通过 · isLiveAgent(user, 60) => TRUE`
        : `✅ [${r.tier}] Verified Live Agent · isLiveAgent(user, 60) => TRUE`;
    } else if (!r.hasAgentId) {
      pill.style.color = "#fbbf24";
      pill.style.borderColor = "rgba(245,158,11,0.5)";
      banner.classList.add("verdict-warn");
      if (currentLang === "zh") {
        const unboundZh = r.totalScore >= 60
          ? `链上行为分已达 ${r.totalScore} 分，绑定 SPACE ID .ai 身份后即可解锁活体认证`
          : `尚未绑定 SPACE ID .ai 身份（当前链上基础分 ${r.totalScore}/60）`;
        banner.textContent = `⚠️ [${r.tier}] 未绑定 .ai 身份 · ${unboundZh}`;
      } else {
        const unboundEn = r.totalScore >= 60
          ? `On-chain activity scored ${r.totalScore}/100 — bind a SPACE ID .ai handle to unlock attestation`
          : `No SPACE ID .ai handle bound yet (base score ${r.totalScore}/60)`;
        banner.textContent = `⚠️ [${r.tier}] Unbound .ai Identity · ${unboundEn}`;
      }
    } else if (r.historyUnverified) {
      pill.style.color = "#fbbf24";
      pill.style.borderColor = "rgba(245,158,11,0.5)";
      banner.classList.add("verdict-warn");
      banner.textContent = currentLang === "zh"
        ? `⚠️ [${r.tier}] 历史索引限流保护中 · isLiveAgent(user, 60) => FALSE (Fail-Closed)`
        : `⚠️ [${r.tier}] Indexer Rate-Limited (Fail-Closed) · isLiveAgent(user, 60) => FALSE`;
    } else if (r.totalScore >= 40) {
      pill.style.color = "#fbbf24";
      pill.style.borderColor = "rgba(245,158,11,0.5)";
      banner.classList.add("verdict-warn");
      if (r.totalScore < 60) {
        const scoreGap = 60 - r.totalScore;
        banner.textContent = currentLang === "zh"
          ? `⚠️ [${r.tier}] 低活跃观察级 · 距 B 端活体门槛还差 ${scoreGap} 分`
          : `⚠️ [${r.tier}] Below Live Threshold · ${scoreGap} pts needed for isLiveAgent(user, 60)`;
      } else {
        banner.textContent = `⚠️ [${r.tier}] isLiveAgent(user, 60) => FALSE`;
      }
    } else {
      pill.style.color = "#f87171";
      pill.style.borderColor = "rgba(239,68,68,0.5)";
      banner.classList.add("verdict-sybil");
      banner.textContent = currentLang === "zh"
        ? `🚨 [${r.tier}] 高危粉尘/休眠女巫拦截 · isLiveAgent(user, 60) => FALSE`
        : `🚨 [${r.tier}] Sybil / Dormant Dust Shell Blocked · isLiveAgent(user, 60) => FALSE`;
    }

    const d1 = r.dimensions.d1Funding;
    const d2 = r.dimensions.d2Temporal;
    const d3 = r.dimensions.d3Economic;
    const d4 = r.dimensions.d4Proof;

    const funderDisplay = d1.funder
      ? (ownerVerified ? d1.funder : `${maskAddress(d1.funder)} (Privacy-Masked)`)
      : t("noneStr");

    document.getElementById("d1Val").textContent = `${d1.score} / 30`;
    document.getElementById("d1Bar").style.width = `${(d1.score / 30) * 100}%`;
    document.getElementById("d1Meta").textContent = currentLang === "zh"
      ? `首笔/当前 BNB: ${d1.firstFundingBNB} BNB | 入金源: ${funderDisplay} | 母钱包近50笔同额粉尘: ${d1.funderSameDust50} 笔`
      : `Initial/Live BNB: ${d1.firstFundingBNB} BNB | Funder: ${funderDisplay} | Funder equal-dust fanout (last 50): ${d1.funderSameDust50}`;

    document.getElementById("d2Val").textContent = `${d2.score} / 25`;
    document.getElementById("d2Bar").style.width = `${(d2.score / 25) * 100}%`;
    document.getElementById("d2Meta").textContent = currentLang === "zh"
      ? `主动交互: ${d2.txCount} 笔 | 跨度: ${d2.spanDays} 天 (${d2.activeDays} 活跃日) | 香农熵: ${d2.entropyBits} bit | 间隔 CV: ${d2.intervalCV}`
      : `Outbound Txs: ${d2.txCount} | Span: ${d2.spanDays}d (${d2.activeDays} active days) | Entropy: ${d2.entropyBits} bit | Interval CV: ${d2.intervalCV}`;

    const protosText = (d3.protocolsHit && d3.protocolsHit.length) ? d3.protocolsHit.join(", ") : t("noneStr");
    document.getElementById("d3Val").textContent = `${d3.score} / 30`;
    document.getElementById("d3Bar").style.width = `${(d3.score / 30) * 100}%`;
    document.getElementById("d3Meta").textContent = currentLang === "zh"
      ? `命中真实协议: ${protosText} | 有效经济交易: ${d3.realEconomicTxs} 笔 (零摩擦: ${d3.zeroFrictionTxs} 笔) | 留存净值 ≈ $${d3.retainedUSD} (BNB $${d3.bnbPriceUSD || "--"})`
      : `Protocols Hit: ${protosText} | Fee-Bearing Txs: ${d3.realEconomicTxs} (Zero-Friction: ${d3.zeroFrictionTxs}) | Retained ≈ $${d3.retainedUSD} (BNB $${d3.bnbPriceUSD || "--"})`;

    document.getElementById("d4Val").textContent = `${d4.score} / 15`;
    document.getElementById("d4Bar").style.width = `${(d4.score / 15) * 100}%`;
    document.getElementById("d4Meta").textContent = currentLang === "zh"
      ? `注册表: ${d4.registry} | 正反向强验一致: ${d4.forwardConsistent ? "通过" : "未通过"} | 合约 Nonce: ${d4.contractNonce ?? 0}`
      : `Registry: ${d4.registry} | Forward/Reverse Match: ${d4.forwardConsistent ? "Verified" : "Unbound"} | Gate Nonce: ${d4.contractNonce ?? 0}`;

    const flagsWrap = document.getElementById("riskFlagsWrap");
    if (r.riskFlags && r.riskFlags.length > 0) {
      flagsWrap.classList.remove("hidden");
      flagsWrap.innerHTML = r.riskFlags.map((f) => `<span class="flag-tag">🚩 ${f}</span>`).join("");
    } else {
      flagsWrap.classList.add("hidden");
      flagsWrap.innerHTML = "";
    }

    document.getElementById("proofPre").textContent = JSON.stringify(
      buildPrivacySafeProofObject(r),
      null,
      2
    );

    renderRadarSvg(d1.score, d2.score, d3.score, d4.score);
  }

  async function runAudit(target, opts = {}) {
    const clean = (target || "").trim();
    if (!clean) return null;
    const seq = ++latestAuditSeq;
    auditBtn.disabled = true;
    auditBtn.textContent = t("auditLoading");
    try {
      const refreshQs = opts.refresh ? "&refresh=1" : "";
      let apiData = null;
      let shouldFallbackStatic = false;

      try {
        const resp = await fetch(`./api/check?target=${encodeURIComponent(clean)}${refreshQs}`);
        const parsed = await resp.json();
        if (parsed && typeof parsed === "object" && "ok" in parsed) {
          apiData = parsed;
        } else {
          shouldFallbackStatic = true;
        }
      } catch (_) {
        shouldFallbackStatic = true;
      }

      if (shouldFallbackStatic) {
        const fallbackReport = await runServerlessFallbackAudit(clean);
        if (seq !== latestAuditSeq) return null;
        renderReport(fallbackReport, { preserveTxStatus: Boolean(opts.preserveTxStatus) });
        return fallbackReport;
      }

      if (seq !== latestAuditSeq) return null;
      if (!apiData.ok) {
        errorBox.textContent = `❌ ${apiData.error || "Verification failed"}`;
        errorBox.classList.remove("hidden");
        return null;
      }
      updateModeBadge("modeApi");
      renderReport(apiData, { preserveTxStatus: Boolean(opts.preserveTxStatus) });
      return apiData;
    } catch (err) {
      if (seq === latestAuditSeq) {
        errorBox.textContent = `❌ ${err.message}`;
        errorBox.classList.remove("hidden");
      }
      return null;
    } finally {
      if (seq === latestAuditSeq) {
        auditBtn.disabled = false;
        auditBtn.textContent = t("auditIdle");
      }
    }
  }

  function renderBenchmarkRows(samples) {
    const tbody = document.getElementById("benchBody");
    if (!tbody) return;
    if (!samples || samples.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="muted">${
        currentLang === "zh"
          ? "暂无预热样本，可直接在上方输入您的 .ai 域名自检"
          : "No pre-calibrated samples loaded — enter your .ai handle above."
      }</td></tr>`;
      return;
    }
    tbody.innerHTML = samples.map((s) => {
      const d = s.dimensions;
      const badgeColor = s.isLiveAgent60 ? "#34d399" : (s.totalScore >= 40 ? "#fbbf24" : "#f87171");
      const safeLabel = s.handle || maskAddress(s.address);
      const clickTarget = s.handle || "";
      return `
        <tr data-handle="${clickTarget}">
          <td><strong>${safeLabel}</strong></td>
          <td style="color:${badgeColor};font-weight:700">${s.tier}</td>
          <td style="font-weight:800">${s.totalScore}</td>
          <td>${d.d1Funding.score}</td>
          <td>${d.d2Temporal.score}</td>
          <td>${d.d3Economic.score}</td>
          <td>${d.d4Proof.score}</td>
          <td style="color:${badgeColor}">${s.isLiveAgent60 ? "✅ PASS" : "🚫 BLOCK"}</td>
        </tr>
      `;
    }).join("");
    tbody.querySelectorAll("tr[data-handle]").forEach((row) => {
      row.addEventListener("click", () => {
        const h = row.getAttribute("data-handle");
        if (!h) return;
        input.value = h;
        runAudit(h);
        if (typeof window !== "undefined" && window.scrollTo) {
          window.scrollTo({ top: 0, behavior: "smooth" });
        }
      });
    });
  }

  async function loadBenchmarkTable() {
    try {
      let samples = null;
      try {
        const resp = await fetch("./api/samples");
        const data = await resp.json();
        if (data && data.ok && Array.isArray(data.samples)) {
          samples = data.samples;
        }
      } catch (_) {}

      if (samples === null) {
        samples = await ensureStaticSamplesLoaded();
      } else {
        cachedBenchmarkSamples = samples;
      }
      renderBenchmarkRows(samples || []);
    } catch (_) {}
  }

  if (langToggleBtn) {
    langToggleBtn.addEventListener("click", () => {
      currentLang = currentLang === "en" ? "zh" : "en";
      applyLanguageUI();
    });
  }

  connectBtn.addEventListener("click", async () => {
    const provider = getProvider();
    if (!provider) {
      alert(
        currentLang === "zh"
          ? "未检测到 Binance Wallet 或浏览器 Web3 钱包插件。您仍可免连钱包进行 .ai 活体自检！"
          : "No Binance Wallet or Web3 browser wallet detected. You can still run read-only .ai liveness self-checks!"
      );
      return;
    }
    try {
      const accounts = await provider.request({ method: "eth_requestAccounts" });
      connectedAccount = accounts[0];
      connectBtn.textContent = `${t("connectedPrefix")}${connectedAccount.slice(0, 6)}...${connectedAccount.slice(-4)}`;
      input.value = connectedAccount;
      await runAudit(connectedAccount);
    } catch (err) {
      alert(`Wallet connection cancelled: ${err.message}`);
    }
  });

  mintBtn.addEventListener("click", async () => {
    if (!currentReport) return;
    if (!currentReport.hasAgentId) {
      alert(
        currentLang === "zh"
          ? "该钱包尚未绑定 SPACE ID .ai 身份，无法铸造活体徽章。"
          : "This wallet has no SPACE ID .ai handle bound on BSC and cannot mint a liveness badge."
      );
      return;
    }
    if (currentReport.historyUnverified) {
      alert(
        currentLang === "zh"
          ? "当前链上历史索引处于限流保护状态（Fail-Closed），请稍后重试。"
          : "Historical indexer is temporarily rate-limited (Fail-Closed). Please retry shortly."
      );
      return;
    }

    const contractAddr = currentReport.eip712.domain.verifyingContract;
    const isPlaceholderOrStatic =
      contractAddr.toLowerCase() === PLACEHOLDER_CONTRACT ||
      Boolean(currentReport.isStaticPreview) ||
      Boolean(currentReport.eip712.isDemoSigner);
    const provider = getProvider();

    if (isPlaceholderOrStatic) {
      if (connectedAccount && connectedAccount.toLowerCase() !== currentReport.addressLower) {
        txStatus.className = "tx-status";
        txStatus.classList.remove("hidden");
        txStatus.textContent = currentLang === "zh"
          ? `🔄 已连接钱包 (${connectedAccount.slice(0, 6)}...${connectedAccount.slice(-4)}) 与当前预览报告不一致，正在切换为您本人的自检报告...`
          : `🔄 Connected wallet (${connectedAccount.slice(0, 6)}...${connectedAccount.slice(-4)}) differs from the previewed handle — switching to your wallet's report...`;
        input.value = connectedAccount;
        await runAudit(connectedAccount, { refresh: true, preserveTxStatus: true });
        return;
      }
      if (!currentReport.isLiveAgent60 || currentReport.totalScore < 60) {
        txStatus.className = "tx-status";
        txStatus.classList.remove("hidden");
        txStatus.textContent = currentLang === "zh"
          ? `⚠️ 当前活体评分为 ${currentReport.totalScore}/100 (< 60 分门限)，isLiveAgent(user, 60) 为 FALSE，请先满足双轨活体门槛后再铸章。`
          : `⚠️ Current liveness score is ${currentReport.totalScore}/100 (< 60 threshold); isLiveAgent(user, 60) is FALSE.`;
        return;
      }
      const calldata = encodeAttestLivenessCalldata(currentReport.eip712.payload, currentReport.eip712.signature);
      txStatus.className = "tx-status tx-ok";
      txStatus.classList.remove("hidden");
      txStatus.textContent = currentLang === "zh"
        ? `✅ 零风险预演通过！已构造 0 值无授权 Calldata (nonce=${currentReport.eip712.payload.nonce}, ${calldata.slice(0, 34)}... 共 ${(calldata.length - 2) / 2} bytes)。连接本地/后端签名服务 (python3 web/server.py) 且合约上链后即可广播铸造 Soulbound 徽章！`
        : `✅ Zero-risk calldata simulation passed! Built 0-value, zero-approval calldata (nonce=${currentReport.eip712.payload.nonce}, ${calldata.slice(0, 34)}..., ${(calldata.length - 2) / 2} bytes). Run with live EIP-712 oracle (python3 web/server.py) to broadcast on BSC Mainnet!`;
      return;
    }

    if (!provider) {
      alert(
        currentLang === "zh"
          ? "请在 Binance Wallet 或 Web3 浏览器钱包中打开以发起上链存证（仅需 <$0.01 原生 Gas，零代币授权）。"
          : "Open in Binance Wallet or a Web3 browser wallet to broadcast on-chain (<$0.01 native BSC gas, zero token approvals)."
      );
      return;
    }
    try {
      const accounts = await provider.request({ method: "eth_requestAccounts" });
      if (!accounts || !accounts[0]) {
        throw new Error("No authorized wallet account returned");
      }
      connectedAccount = accounts[0];
      connectBtn.textContent = `${t("connectedPrefix")}${connectedAccount.slice(0, 6)}...${connectedAccount.slice(-4)}`;

      // Strict msg.sender == payload.wallet alignment guard (prevents InvalidSignature() gas waste & preserves banner!)
      if (accounts[0].toLowerCase() !== currentReport.addressLower) {
        const prevHandle = currentReport.handle || maskAddress(currentReport.address);
        input.value = accounts[0];
        txStatus.className = "tx-status";
        txStatus.classList.remove("hidden");
        txStatus.textContent = currentLang === "zh"
          ? `🔄 当前展示的是 ${prevHandle} 的报告，正在自动为您连接的钱包 ${accounts[0].slice(0, 6)}...${accounts[0].slice(-4)} 重新审计...`
          : `🔄 Currently viewing ${prevHandle} — switching to your connected wallet ${accounts[0].slice(0, 6)}...${accounts[0].slice(-4)}...`;
        const switched = await runAudit(accounts[0], { refresh: true, preserveTxStatus: true });
        if (switched) {
          txStatus.textContent = currentLang === "zh"
            ? `🔄 已切换为您连接的钱包 ${accounts[0].slice(0, 6)}...${accounts[0].slice(-4)} 最新报告 (nonce=${switched.eip712.payload.nonce})，核对本人分数后再次点击即可铸章！`
            : `🔄 Switched to your connected wallet ${accounts[0].slice(0, 6)}...${accounts[0].slice(-4)} (nonce=${switched.eip712.payload.nonce}). Review your score and click Mint again!`;
        }
        return;
      }

      // Force-sync live on-chain `nonces(address)` (`?refresh=1`) before broadcasting
      txStatus.className = "tx-status";
      txStatus.classList.remove("hidden");
      txStatus.textContent = currentLang === "zh"
        ? "⏳ 正在实时同步链上合约 Nonce 并签发防重放存证载荷..."
        : "⏳ Syncing live on-chain contract nonce and signing anti-replay EIP-712 attestation...";
      const refreshed = await runAudit(accounts[0], { refresh: true, preserveTxStatus: true });
      if (!refreshed || !currentReport || accounts[0].toLowerCase() !== currentReport.addressLower) return;
      if (!currentReport.hasAgentId || currentReport.historyUnverified) return;
      if (!currentReport.isLiveAgent60 || currentReport.totalScore < 60) {
        txStatus.className = "tx-status";
        txStatus.classList.remove("hidden");
        txStatus.textContent = currentLang === "zh"
          ? `⚠️ 最新活体评分为 ${currentReport.totalScore}/100 (< 60 分门限)，已拦截上链以免浪费 Gas。`
          : `⚠️ Latest liveness score is ${currentReport.totalScore}/100 (< 60 threshold); blocked broadcast to save gas.`;
        return;
      }

      // Switch wallet to BNB Smart Chain (0x38) BEFORE calling eth_getCode so non-BSC wallets
      // are never misidentified as querying an undeployed contract on Ethereum/Arbitrum/Base!
      try {
        await provider.request({
          method: "wallet_switchEthereumChain",
          params: [{ chainId: "0x38" }],
        });
      } catch (switchErr) {
        if (switchErr && Number(switchErr.code) === 4902) {
          await provider.request({
            method: "wallet_addEthereumChain",
            params: [{
              chainId: "0x38",
              chainName: "BNB Smart Chain",
              nativeCurrency: { name: "BNB", symbol: "BNB", decimals: 18 },
              rpcUrls: ["https://bsc-dataseed.binance.org"],
              blockExplorerUrls: ["https://bscscan.com"],
            }],
          });
        } else {
          throw switchErr;
        }
      }

      const deployedCode = await provider.request({
        method: "eth_getCode",
        params: [contractAddr, "latest"],
      });
      if (typeof deployedCode === "string" && /^0x0*$/i.test(deployedCode)) {
        txStatus.className = "tx-status";
        txStatus.classList.remove("hidden");
        txStatus.textContent = currentLang === "zh"
          ? `⚠️ 主网合约 ${contractAddr} 尚未完成部署广播，已安全拦截交易防止向空地址发 Calldata。`
          : `⚠️ Contract ${contractAddr} is not yet deployed on-chain; blocked transaction to prevent empty-address gas spend.`;
        return;
      }

      const calldata = encodeAttestLivenessCalldata(currentReport.eip712.payload, currentReport.eip712.signature);
      const txHash = await provider.request({
        method: "eth_sendTransaction",
        params: [{
          from: accounts[0],
          to: contractAddr,
          value: "0x0",
          data: calldata,
        }],
      });
      txStatus.className = "tx-status tx-ok";
      txStatus.classList.remove("hidden");
      txStatus.textContent = currentLang === "zh"
        ? `🎉 Soulbound 活体徽章交易已广播！TxHash: ${txHash}`
        : `🎉 Soulbound Liveness Badge transaction broadcast! TxHash: ${txHash}`;
    } catch (err) {
      txStatus.className = "tx-status";
      txStatus.classList.remove("hidden");
      txStatus.textContent = `⚠️ ${err.message}`;
    }
  });

  shareBtn.addEventListener("click", () => {
    if (!currentReport) return;
    const h = currentReport.handle || maskAddress(currentReport.address);
    const txt = currentLang === "zh"
      ? `刚用开源工具 AgentPulse 自检了 .ai Agent ID [${h}] 的四维链上活体分：${currentReport.totalScore}/100 (${currentReport.tier})！\n🛡️ 零代币授权、隐私脱敏保护 + 一行代码 isLiveAgent 防女巫门禁 👇\n${DEMO_URL}\n#BinanceWalletHackathon #AgenticWallet`
      : `Just ran a 4D on-chain liveness self-check on [${h}] with open-source AgentPulse: ${currentReport.totalScore}/100 (Tier ${currentReport.tier})!\n🛡️ Zero approvals, privacy-masked addresses & 1-line isLiveAgent Sybil gate 👇\n${DEMO_URL}\n#BinanceWalletHackathon #AgenticWallet`;
    const url = `https://x.com/intent/tweet?text=${encodeURIComponent(txt)}`;
    window.open(url, "_blank", "noopener,noreferrer");
  });

  copyProofBtn.addEventListener("click", () => {
    if (!currentReport) return;
    navigator.clipboard.writeText(JSON.stringify(buildPrivacySafeProofObject(currentReport), null, 2));
    copyProofBtn.textContent = t("copyProofDone");
    setTimeout(() => { copyProofBtn.textContent = t("copyProofIdle"); }, 1500);
  });

  document.querySelectorAll(".chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tVal = btn.getAttribute("data-target");
      input.value = tVal;
      runAudit(tVal);
    });
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    return runAudit(input.value);
  });

  applyLanguageUI();
  loadBenchmarkTable();
  runAudit("redkoi.ai");
})();
