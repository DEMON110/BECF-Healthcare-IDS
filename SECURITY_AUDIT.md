# Smart-Contract Security Verification

This repository includes the Solidity source for the BECF consent-management component. The commands below allow an independent reviewer to reproduce compilation, unit tests, and static analysis.

## 1. Compile and test

```bash
npm install
npx hardhat compile
npx hardhat test
```

The tests cover:
- patient consent grant;
- authorized access;
- patient revocation;
- separation of patient-owned consent records.

## 2. Slither

Install Slither in a Python environment and run:

```bash
pip install slither-analyzer
slither .
```

Review every warning in the generated report. Do not treat informational warnings as proof of security; use the report together with the source-code review.

## 3. Oyente

Oyente can be run against the compiled contract where a compatible installation is available. Because Oyente has an older toolchain, record the exact version and invocation in any reproduced audit report.

## 4. Manual checks

The contract was designed to make the following properties explicit:

1. A patient grants and revokes consent through `msg.sender`.
2. A requestor address cannot be zero.
3. Consent expiry must be in the future at grant time.
4. `accessData` succeeds only for `GRANTED` and non-expired consent.
5. Expired consent is transitioned to `EXPIRED`.
6. No patient medical data is stored or returned by the contract.
7. State transitions emit audit events.

## Important reproducibility note

Static-analysis output must be generated from the exact commit being reviewed. This repository therefore provides the Solidity source and test/audit commands rather than embedding an unverifiable claim of a particular analyzer result.
