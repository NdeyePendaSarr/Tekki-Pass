/** Display helpers for Nostr public keys. Kept apart from identity.ts so that pages which
 * only show a key (the public profile) do not load the recovery-phrase code. */

/** Short display form, e.g. "npub1abcd…wxyz". */
export function shortNpub(npub: string): string {
  return `${npub.slice(0, 10)}…${npub.slice(-4)}`;
}
