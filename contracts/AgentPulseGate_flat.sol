// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title ISpaceIdAiRegistry
 * @notice Official BNB Smart Chain SPACE ID .ai Agent ID Registry (0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F)
 */
interface ISpaceIdAiRegistry {
    function handleOf(address account) external view returns (string memory);
}

/**
 * @title AgentPulseGate (Proof-of-Live-Agent)
 * @author RedKoi Research
 * @notice Zero-asset-risk, non-custodial Soulbound Liveness Attestation & B2B Anti-Sybil Gate for .ai Agents on BSC.
 *         - 100% Zero Financial Risk: NO payable functions, NO token approvals, NO fee collection, NO asset custody.
 *         - Native On-Chain Identity Check: Calls SPACE ID .ai Registry handleOf(msg.sender) directly.
 *         - Deterministic 4D Score Proof: Verifies EIP-712 digest via ecrecover and mints/updates Soulbound badge.
 *         - One-Line B2B Gate: Exposes isLiveAgent(address user, uint8 minScore) for airdrops, launchpads, and dApps.
 */
contract AgentPulseGate {
    // =========================================================================
    // Constants & Immutables
    // =========================================================================

    /// @notice Official BSC SPACE ID .ai HandleRegistry
    address public constant DEFAULT_SPACE_ID_REGISTRY = 0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F;

    /// @notice EIP-712 Typehashes
    bytes32 public constant EIP712_DOMAIN_TYPEHASH = keccak256(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    );
    bytes32 public constant ATTESTATION_TYPEHASH = keccak256(
        "LivenessAttestation(address wallet,bytes32 handleHash,uint8 totalScore,uint8 d1Funding,uint8 d2Temporal,uint8 d3Economic,uint8 d4Proof,uint64 issuedAt,uint64 expiresAt,uint256 nonce)"
    );
    bytes32 public constant NAME_HASH = keccak256("AgentPulse");
    bytes32 public constant VERSION_HASH = keccak256("1");

    /// @notice secp256k1 half curve order for EIP-2 signature malleability protection
    uint256 private constant SECP256K1N_HALF = 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0;

    /// @notice Registry address (defaults to 0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F on BSC mainnet)
    address public immutable spaceIdRegistry;
    uint256 private immutable _cachedChainId;
    bytes32 private immutable _cachedDomainSeparator;

    // =========================================================================
    // Structs & Storage
    // =========================================================================

    string public constant name = "AgentPulse Soulbound Badge";
    string public constant symbol = "PULSE-SBT";

    address public owner;
    address public verifierSigner;

    uint256 public uniqueAttestedAgents;
    uint256 public totalAttestations;

    struct AttestationPayload {
        uint8 totalScore;
        uint8 d1Funding;
        uint8 d2Temporal;
        uint8 d3Economic;
        uint8 d4Proof;
        uint64 issuedAt;
        uint64 expiresAt;
    }

    struct PulseRecord {
        uint256 badgeId;
        bytes32 handleHash;
        uint8 totalScore;
        uint8 d1Funding;
        uint8 d2Temporal;
        uint8 d3Economic;
        uint8 d4Proof;
        uint64 issuedAt;
        uint64 expiresAt;
        uint64 updatedAt;
        uint32 updateCount;
        string handle;
    }

    mapping(address => PulseRecord) private _records;
    mapping(uint256 => address) private _ownerOfBadge;
    mapping(address => uint256) public nonces;

    // =========================================================================
    // Events & Custom Errors
    // =========================================================================

    event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);
    event Locked(uint256 tokenId);

    event LivenessAttested(
        address indexed agent,
        uint256 indexed badgeId,
        string handle,
        uint8 totalScore,
        uint8 d1Funding,
        uint8 d2Temporal,
        uint8 d3Economic,
        uint8 d4Proof,
        uint64 expiresAt,
        bool isFirstAttestation
    );
    event VerifierSignerUpdated(address indexed previousSigner, address indexed newSigner);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    error ZeroAddress();
    error ZeroValueOnly();
    error Unauthorized();
    error NoAgentIdBound(address caller);
    error InvalidScoreBreakdown(uint8 total, uint16 sumOfDimensions);
    error AttestationExpired(uint64 expiresAt, uint256 currentTimestamp);
    error InvalidSignature();
    error SoulboundNonTransferable();
    error BadgeDoesNotExist(uint256 tokenId);

    // =========================================================================
    // Constructor & Anti-Custody Guards
    // =========================================================================

    constructor(address initialVerifierSigner, address registryOverride) {
        if (initialVerifierSigner == address(0)) revert ZeroAddress();
        owner = msg.sender;
        verifierSigner = initialVerifierSigner;
        spaceIdRegistry = registryOverride == address(0) ? DEFAULT_SPACE_ID_REGISTRY : registryOverride;

        _cachedChainId = block.chainid;
        _cachedDomainSeparator = _buildDomainSeparator();

        emit OwnershipTransferred(address(0), msg.sender);
        emit VerifierSignerUpdated(address(0), initialVerifierSigner);
    }

    /// @notice Hard-reject accidental BNB transfers: 100% zero fund custody
    receive() external payable {
        revert ZeroValueOnly();
    }

    fallback() external payable {
        revert ZeroValueOnly();
    }

    // =========================================================================
    // Core Attestation Logic (Non-Payable, Zero Token Approval)
    // =========================================================================

    /**
     * @notice Verify caller's live .ai handle on SPACE ID + EIP-712 4D score proof, then mint/update Soulbound badge.
     */
    function attestLiveness(
        AttestationPayload calldata p,
        bytes calldata signature
    ) external returns (uint256 badgeId) {
        if (block.timestamp > p.expiresAt) {
            revert AttestationExpired(p.expiresAt, block.timestamp);
        }

        uint16 dimSum = uint16(p.d1Funding) + uint16(p.d2Temporal) + uint16(p.d3Economic) + uint16(p.d4Proof);
        if (
            p.totalScore > 100 ||
            p.d1Funding > 30 ||
            p.d2Temporal > 25 ||
            p.d3Economic > 30 ||
            p.d4Proof > 15 ||
            dimSum != uint16(p.totalScore)
        ) {
            revert InvalidScoreBreakdown(p.totalScore, dimSum);
        }

        // 1. Native on-chain check against SPACE ID .ai Registry (0x60B9...022F)
        string memory rawHandle = ISpaceIdAiRegistry(spaceIdRegistry).handleOf(msg.sender);
        if (bytes(rawHandle).length == 0) {
            revert NoAgentIdBound(msg.sender);
        }
        string memory normalizedHandle = _normalizeHandle(rawHandle);
        bytes32 handleHash = keccak256(bytes(normalizedHandle));

        // 2. Consume anti-replay nonce & verify EIP-712 signature via ecrecover
        uint256 currentNonce = nonces[msg.sender]++;
        bytes32 structHash = _buildStructHash(msg.sender, handleHash, p, currentNonce);
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", domainSeparator(), structHash));
        if (_recoverSigner(digest, signature) != verifierSigner) {
            revert InvalidSignature();
        }

        // 3. Mint or update Soulbound Liveness Record
        badgeId = _upsertRecord(msg.sender, normalizedHandle, handleHash, p);
    }

    // =========================================================================
    // One-Line B2B Anti-Sybil Gate & Read Views
    // =========================================================================

    /**
     * @notice One-line B2B Sybil-resistance gate for airdrops, Launchpads, and Agentic dApps.
     */
    function isLiveAgent(address user, uint8 minScore) external view returns (bool) {
        PulseRecord storage rec = _records[user];
        if (rec.badgeId == 0) return false;
        if (block.timestamp > rec.expiresAt) return false;
        if (rec.totalScore < minScore) return false;

        string memory currentHandle = ISpaceIdAiRegistry(spaceIdRegistry).handleOf(user);
        if (bytes(currentHandle).length == 0) return false;
        return keccak256(bytes(_normalizeHandle(currentHandle))) == rec.handleHash;
    }

    function getPulseRecord(address user) external view returns (PulseRecord memory) {
        return _records[user];
    }

    function computeAttestationDigest(
        address wallet,
        string calldata handle,
        AttestationPayload calldata p,
        uint256 nonce
    ) external view returns (bytes32) {
        bytes32 handleHash = keccak256(bytes(_normalizeHandle(handle)));
        bytes32 structHash = _buildStructHash(wallet, handleHash, p, nonce);
        return keccak256(abi.encodePacked("\x19\x01", domainSeparator(), structHash));
    }

    function domainSeparator() public view returns (bytes32) {
        return block.chainid == _cachedChainId ? _cachedDomainSeparator : _buildDomainSeparator();
    }

    // =========================================================================
    // Minimal ERC-721 + ERC-5192 Soulbound Interface
    // =========================================================================

    function balanceOf(address account) external view returns (uint256) {
        if (account == address(0)) revert ZeroAddress();
        return _records[account].badgeId == 0 ? 0 : 1;
    }

    function ownerOf(uint256 tokenId) external view returns (address) {
        address holder = _ownerOfBadge[tokenId];
        if (holder == address(0)) revert BadgeDoesNotExist(tokenId);
        return holder;
    }

    function locked(uint256 tokenId) external view returns (bool) {
        if (_ownerOfBadge[tokenId] == address(0)) revert BadgeDoesNotExist(tokenId);
        return true;
    }

    function supportsInterface(bytes4 interfaceId) external pure returns (bool) {
        return
            interfaceId == 0x01ffc9a7 || // ERC-165
            interfaceId == 0x80ac58cd || // ERC-721
            interfaceId == 0xb45a3c0e;   // ERC-5192 Minimal Soulbound
    }

    function transferFrom(address, address, uint256) external pure {
        revert SoulboundNonTransferable();
    }

    function safeTransferFrom(address, address, uint256) external pure {
        revert SoulboundNonTransferable();
    }

    function safeTransferFrom(address, address, uint256, bytes calldata) external pure {
        revert SoulboundNonTransferable();
    }

    function approve(address, uint256) external pure {
        revert SoulboundNonTransferable();
    }

    function setApprovalForAll(address, bool) external pure {
        revert SoulboundNonTransferable();
    }

    // =========================================================================
    // Governance (Signer Rotation Only - Zero Access to User Funds)
    // =========================================================================

    function setVerifierSigner(address newSigner) external {
        if (msg.sender != owner) revert Unauthorized();
        if (newSigner == address(0)) revert ZeroAddress();
        address prev = verifierSigner;
        verifierSigner = newSigner;
        emit VerifierSignerUpdated(prev, newSigner);
    }

    function transferOwnership(address newOwner) external {
        if (msg.sender != owner) revert Unauthorized();
        if (newOwner == address(0)) revert ZeroAddress();
        address prev = owner;
        owner = newOwner;
        emit OwnershipTransferred(prev, newOwner);
    }

    // =========================================================================
    // Internal Helpers
    // =========================================================================

    function _buildStructHash(
        address wallet,
        bytes32 handleHash,
        AttestationPayload calldata p,
        uint256 nonce
    ) private pure returns (bytes32) {
        return keccak256(
            abi.encode(
                ATTESTATION_TYPEHASH,
                wallet,
                handleHash,
                p.totalScore,
                p.d1Funding,
                p.d2Temporal,
                p.d3Economic,
                p.d4Proof,
                p.issuedAt,
                p.expiresAt,
                nonce
            )
        );
    }

    function _upsertRecord(
        address agent,
        string memory normalizedHandle,
        bytes32 handleHash,
        AttestationPayload calldata p
    ) private returns (uint256 badgeId) {
        PulseRecord storage rec = _records[agent];
        bool isFirst = (rec.badgeId == 0);
        if (isFirst) {
            unchecked {
                badgeId = ++uniqueAttestedAgents;
            }
            rec.badgeId = badgeId;
            _ownerOfBadge[badgeId] = agent;
            emit Transfer(address(0), agent, badgeId);
            emit Locked(badgeId);
        } else {
            badgeId = rec.badgeId;
        }

        unchecked {
            ++totalAttestations;
            ++rec.updateCount;
        }

        rec.handleHash = handleHash;
        rec.totalScore = p.totalScore;
        rec.d1Funding = p.d1Funding;
        rec.d2Temporal = p.d2Temporal;
        rec.d3Economic = p.d3Economic;
        rec.d4Proof = p.d4Proof;
        rec.issuedAt = p.issuedAt;
        rec.expiresAt = p.expiresAt;
        rec.updatedAt = uint64(block.timestamp);
        rec.handle = normalizedHandle;

        emit LivenessAttested(
            agent,
            badgeId,
            normalizedHandle,
            p.totalScore,
            p.d1Funding,
            p.d2Temporal,
            p.d3Economic,
            p.d4Proof,
            p.expiresAt,
            isFirst
        );
    }

    function _buildDomainSeparator() private view returns (bytes32) {
        return keccak256(
            abi.encode(
                EIP712_DOMAIN_TYPEHASH,
                NAME_HASH,
                VERSION_HASH,
                block.chainid,
                address(this)
            )
        );
    }

    function _recoverSigner(bytes32 digest, bytes calldata sig) private pure returns (address) {
        if (sig.length != 65) revert InvalidSignature();
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := calldataload(sig.offset)
            s := calldataload(add(sig.offset, 32))
            v := byte(0, calldataload(add(sig.offset, 64)))
        }
        if (v < 27) {
            v += 27;
        }
        if ((v != 27 && v != 28) || uint256(s) > SECP256K1N_HALF) {
            revert InvalidSignature();
        }
        address signer = ecrecover(digest, v, r, s);
        if (signer == address(0)) revert InvalidSignature();
        return signer;
    }

    function _normalizeHandle(string memory input) private pure returns (string memory) {
        bytes memory raw = bytes(input);
        uint256 len = raw.length;
        bytes memory lowered = new bytes(len);
        for (uint256 i = 0; i < len; ) {
            bytes1 c = raw[i];
            if (c >= 0x41 && c <= 0x5A) {
                lowered[i] = bytes1(uint8(c) + 32);
            } else {
                lowered[i] = c;
            }
            unchecked {
                ++i;
            }
        }
        if (
            len >= 3 &&
            lowered[len - 3] == 0x2e &&
            lowered[len - 2] == 0x61 &&
            lowered[len - 1] == 0x69
        ) {
            return string(lowered);
        }
        return string(abi.encodePacked(lowered, ".ai"));
    }
}
