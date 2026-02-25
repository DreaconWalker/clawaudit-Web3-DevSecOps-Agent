# ClawAuditRegistry (optional on-chain proof)

Deploy this contract on **Base** or **Base Sepolia** to record audit attestations on-chain. Then anyone can verify via the chain that a given `codeHash` was audited by ClawAudit.

## Deploy (e.g. Remix + MetaMask)

1. Open [Remix](https://remix.ethereum.org), paste `ClawAuditRegistry.sol`, compile.
2. Connect MetaMask to Base (or Base Sepolia), deploy.
3. Set in `.env`: `CLAWAUDIT_REGISTRY_ADDRESS=<deployed>`, `BASE_RPC_URL=https://sepolia.base.org`, `BASE_PRIVATE_KEY=<wallet with testnet ETH>` (optional; only if backend should submit attestations on-chain).

## Backend integration (optional)

Once deployed, you can call `attest(codeHash, reportHash)` from the FastAPI backend using `web3.py` and a funded wallet. The current app already stores attestations in `data/audit_registry.json` and exposes `GET /audit-proof`; on-chain is an extra layer of verifiability.
