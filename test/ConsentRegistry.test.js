const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("ConsentRegistry", function () {
  async function fixture() {
    const [patient, requestor, attacker] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("ConsentRegistry");
    const registry = await Factory.deploy();
    await registry.waitForDeployment();
    const scope = ethers.encodeBytes32String("vitals");
    return { registry, patient, requestor, attacker, scope };
  }

  it("allows a patient to grant and requestor to access consented data", async function () {
    const { registry, patient, requestor, scope } = await fixture();
    const latest = await ethers.provider.getBlock("latest");
    const expiry = latest.timestamp + 3600;
    await expect(registry.connect(patient).grantConsent(requestor.address, scope, expiry))
      .to.emit(registry, "ConsentGranted");
    await expect(registry.connect(requestor).accessData(patient.address, scope))
      .to.emit(registry, "DataAccessed");
  });

  it("prevents a non-patient from changing another patient's consent", async function () {
    const { registry, patient, attacker, scope } = await fixture();
    const latest = await ethers.provider.getBlock("latest");
    const expiry = latest.timestamp + 3600;
    await expect(registry.connect(attacker).grantConsent(attacker.address, scope, expiry)).not.to.be.reverted;
    const state = await registry.getConsent(attacker.address, attacker.address, scope);
    expect(state[0]).to.equal(1); // GRANTED for the attacker's own record
    // The contract keys state by msg.sender for grant/revoke; an attacker cannot grant for patient.
    const patientState = await registry.getConsent(patient.address, attacker.address, scope);
    expect(patientState[0]).to.equal(0); // NONE
  });

  it("supports patient revocation", async function () {
    const { registry, patient, requestor, scope } = await fixture();
    const latest = await ethers.provider.getBlock("latest");
    const expiry = latest.timestamp + 3600;
    await registry.connect(patient).grantConsent(requestor.address, scope, expiry);
    await expect(registry.connect(patient).revokeConsent(requestor.address, scope))
      .to.emit(registry, "ConsentRevoked");
    const state = await registry.getConsent(patient.address, requestor.address, scope);
    expect(state[0]).to.equal(2); // REVOKED
  });
});
