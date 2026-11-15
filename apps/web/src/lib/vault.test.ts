import {
  clearVault,
  isValidPin,
  savedPubkey,
  saveVault,
  unlockVault,
  WrongPinError,
} from "./vault";

const PHRASE = "leader monkey parrot ring guide accident before fence cannon height naive bean";

describe("vault", () => {
  afterEach(() => clearVault());

  it("stores the phrase encrypted and unlocks it with the PIN", async () => {
    await saveVault(PHRASE, "123456", "ab".repeat(32));

    expect(localStorage.getItem("tekki-pass.vault.v1")).not.toContain("leader");
    expect(savedPubkey()).toBe("ab".repeat(32));
    await expect(unlockVault("123456")).resolves.toBe(PHRASE);
  });

  it("rejects a wrong PIN", async () => {
    await saveVault(PHRASE, "123456", "ab".repeat(32));

    await expect(unlockVault("654321")).rejects.toBeInstanceOf(WrongPinError);
  });

  it("requires exactly 6 digits", () => {
    expect(isValidPin("123456")).toBe(true);
    expect(isValidPin("12345")).toBe(false);
    expect(isValidPin("12345a")).toBe(false);
  });

  it("has no profile until one is saved", () => {
    expect(savedPubkey()).toBeNull();
  });
});
