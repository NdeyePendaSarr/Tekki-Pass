import { bytesToHex } from "@noble/hashes/utils.js";
import { sha256 } from "@noble/hashes/sha2.js";
import { finalizeEvent, generateSecretKey, getPublicKey } from "nostr-tools";
import fixture from "./__fixtures__/api-attestation.json";
import { BADGE_IDENTIFIER, verifyAttestation } from "./verify";

const hex = (data: Uint8Array) => bytesToHex(data);
const sha = (text: string) => hex(sha256(new TextEncoder().encode(text)));

/** Build an attestation like the API does, with optional tampering. */
function signed(overrides: { tags?: (tags: string[][]) => string[][]; artisan?: string } = {}) {
  const issuerKey = generateSecretKey();
  const issuer = getPublicKey(issuerKey);
  const artisan = overrides.artisan ?? getPublicKey(generateSecretKey());
  const preimage = crypto.getRandomValues(new Uint8Array(32));
  const paymentHash = hex(sha256(preimage));
  let tags = [
    ["a", `30009:${issuer}:${BADGE_IDENTIFIER}`],
    ["p", artisan],
    ["attestation", sha(`${paymentHash}:${artisan}`)],
    ["payment_hash", paymentHash],
    ["preimage", hex(preimage)],
    ["client", "c".repeat(64)],
    ["network", "testnet"],
    ["t", "tekki-pass"],
  ];
  if (overrides.tags) tags = overrides.tags(tags);
  const event = finalizeEvent(
    { kind: 8, created_at: 1_763_200_000, tags, content: "Peinture salon" },
    issuerKey,
  );
  return { issuer, json: JSON.stringify(event) };
}

describe("verifyAttestation", () => {
  it("accepts an attestation signed by the Python API (cross-implementation)", () => {
    const result = verifyAttestation(JSON.stringify(fixture.event), fixture.issuer);

    expect(result).toMatchObject({
      ok: true,
      title: "Carrelage cuisine, 9 m²",
      network: "testnet",
    });
  });

  it("accepts a valid attestation", () => {
    const { issuer, json } = signed();

    expect(verifyAttestation(json, issuer).ok).toBe(true);
  });

  it("rejects another issuer", () => {
    const { json } = signed();

    expect(verifyAttestation(json, "f".repeat(64))).toEqual({
      ok: false,
      reason: "Émetteur inconnu.",
    });
  });

  it("rejects a modified event", () => {
    const { issuer, json } = signed();
    const tampered = JSON.stringify({ ...JSON.parse(json), content: "Chantier inventé" });

    expect(verifyAttestation(tampered, issuer)).toEqual({
      ok: false,
      reason: "Signature invalide.",
    });
  });

  it("rejects a wrong proof of payment", () => {
    const { issuer, json } = signed({
      tags: (tags) => tags.map((t) => (t[0] === "preimage" ? ["preimage", "0".repeat(64)] : t)),
    });

    expect(verifyAttestation(json, issuer)).toEqual({
      ok: false,
      reason: "Preuve de paiement invalide.",
    });
  });

  it("rejects a proof replayed for another artisan", () => {
    const { issuer, json } = signed({
      tags: (tags) => tags.map((t) => (t[0] === "p" ? ["p", "e".repeat(64)] : t)),
    });

    expect(verifyAttestation(json, issuer)).toEqual({
      ok: false,
      reason: "Preuve réutilisée pour un autre artisan.",
    });
  });

  it("rejects garbage", () => {
    expect(verifyAttestation("{oops", "a".repeat(64)).ok).toBe(false);
  });
});
