import {
  identityFromPhrase,
  isValidRecoveryPhrase,
  newRecoveryPhrase,
  normalizePhrase,
  pickCheckPositions,
} from "./identity";

// Official NIP-06 test vector: https://github.com/nostr-protocol/nips/blob/master/06.md
const NIP06_PHRASE =
  "leader monkey parrot ring guide accident before fence cannon height naive bean";
const NIP06_PUBKEY = "17162c921dc4d2518f9a101db33695df1afb56ab82f5ff3e5da6eec3ca5cd917";

describe("identity", () => {
  it("derives the Nostr key from the recovery phrase as NIP-06 specifies", () => {
    expect(identityFromPhrase(NIP06_PHRASE).pubkey).toBe(NIP06_PUBKEY);
    expect(identityFromPhrase(`  ${NIP06_PHRASE.toUpperCase()} `).pubkey).toBe(NIP06_PUBKEY);
  });

  it("generates valid 12-word phrases", () => {
    const phrase = newRecoveryPhrase();

    expect(phrase.split(" ")).toHaveLength(12);
    expect(isValidRecoveryPhrase(phrase)).toBe(true);
    expect(isValidRecoveryPhrase("not a real recovery phrase")).toBe(false);
  });

  it("normalizes spacing and case", () => {
    expect(normalizePhrase("  Leader   MONKEY\nparrot ")).toBe("leader monkey parrot");
  });

  it("picks distinct sorted positions for the backup check", () => {
    const positions = pickCheckPositions(12);

    expect(positions).toHaveLength(3);
    expect(new Set(positions).size).toBe(3);
    expect([...positions].sort((a, b) => a - b)).toEqual(positions);
    expect(positions.every((p) => p >= 0 && p < 12)).toBe(true);
  });
});
