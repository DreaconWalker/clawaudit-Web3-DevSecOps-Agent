// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * ClawAuditRegistry — optional on-chain proof for audit attestations.
 * Deploy on Base (or Base Sepolia for testnet). Backend submits attestations here
 * so anyone can verify on-chain that a contract was audited by ClawAudit.
 *
 * Usage: backend calls attest(codeHash, reportHash) after each audit.
 * Query: getAttestation(codeHash) or listen for Attested event.
 */
contract ClawAuditRegistry {
    event Attested(bytes32 indexed codeHash, bytes32 reportHash, uint256 timestamp, string auditor);

    struct Proof {
        bytes32 reportHash;
        uint256 timestamp;
        string auditor;
    }

    mapping(bytes32 => Proof) public attestations;

    function attest(bytes32 codeHash, bytes32 reportHash) external {
        require(attestations[codeHash].timestamp == 0, "Already attested");
        attestations[codeHash] = Proof({
            reportHash: reportHash,
            timestamp: block.timestamp,
            auditor: "ClawAudit"
        });
        emit Attested(codeHash, reportHash, block.timestamp, "ClawAudit");
    }

    function getAttestation(bytes32 codeHash) external view returns (bytes32 reportHash, uint256 timestamp, string memory auditor) {
        Proof memory p = attestations[codeHash];
        require(p.timestamp != 0, "No attestation");
        return (p.reportHash, p.timestamp, p.auditor);
    }
}
