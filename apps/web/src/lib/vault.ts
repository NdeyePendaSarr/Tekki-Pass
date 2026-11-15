/**
 * Local vault: the recovery phrase is stored in the browser only, encrypted with a key
 * derived from the artisan's PIN (WebCrypto PBKDF2-SHA-256 + AES-GCM, standard primitives).
 *
 * Limits, stated honestly: a short PIN can be brute-forced by someone who copies the
 * browser's storage. The PIN protects against casual access to the phone; the real
 * safety net is the written backup of the 12 words. The phrase never leaves the device.
 */

const VAULT_ITEM_NAME = "tekki-pass.vault.v1";
const PBKDF2_ITERATIONS = 310_000;

interface StoredVault {
  v: 1;
  salt: string;
  iv: string;
  data: string;
  /** Public key, readable without the PIN (to show the profile while locked). */
  pubkey: string;
}

export class WrongPinError extends Error {}

const toB64 = (bytes: Uint8Array) => btoa(String.fromCharCode(...bytes));
const fromB64 = (text: string) => Uint8Array.from(atob(text), (c) => c.charCodeAt(0));

async function deriveKey(pin: string, salt: Uint8Array): Promise<CryptoKey> {
  const material = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(pin),
    "PBKDF2",
    false,
    ["deriveKey"],
  );
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", salt: salt as BufferSource, iterations: PBKDF2_ITERATIONS, hash: "SHA-256" },
    material,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"],
  );
}

export function isValidPin(pin: string): boolean {
  return /^\d{6}$/.test(pin);
}

export async function saveVault(phrase: string, pin: string, pubkey: string): Promise<void> {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const key = await deriveKey(pin, salt);
  const data = new Uint8Array(
    await crypto.subtle.encrypt(
      { name: "AES-GCM", iv: iv as BufferSource },
      key,
      new TextEncoder().encode(phrase),
    ),
  );
  const vault: StoredVault = { v: 1, salt: toB64(salt), iv: toB64(iv), data: toB64(data), pubkey };
  localStorage.setItem(VAULT_ITEM_NAME, JSON.stringify(vault));
}

function readVault(): StoredVault | null {
  try {
    const raw = localStorage.getItem(VAULT_ITEM_NAME);
    return raw ? (JSON.parse(raw) as StoredVault) : null;
  } catch {
    return null;
  }
}

/** Public key of the saved profile, or null if there is none. */
export function savedPubkey(): string | null {
  return readVault()?.pubkey ?? null;
}

/** Decrypt the recovery phrase. Throws WrongPinError on a wrong PIN. */
export async function unlockVault(pin: string): Promise<string> {
  const vault = readVault();
  if (!vault) throw new Error("no vault");
  try {
    const key = await deriveKey(pin, fromB64(vault.salt));
    const plain = await crypto.subtle.decrypt(
      { name: "AES-GCM", iv: fromB64(vault.iv) as BufferSource },
      key,
      fromB64(vault.data) as BufferSource,
    );
    return new TextDecoder().decode(plain);
  } catch {
    throw new WrongPinError("wrong PIN");
  }
}

export function clearVault(): void {
  localStorage.removeItem(VAULT_ITEM_NAME);
}
