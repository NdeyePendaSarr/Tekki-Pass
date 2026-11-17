import { render, screen } from "@testing-library/react";
import { sha256 } from "@noble/hashes/sha2.js";
import { bytesToHex } from "@noble/hashes/utils.js";
import { type Event, finalizeEvent, generateSecretKey, getPublicKey } from "nostr-tools";
import { api, ApiError, type PublishedAttestation } from "@/lib/api";
import * as relays from "@/lib/relays";
import { mergeAttestations } from "@/lib/relays";
import { BADGE_IDENTIFIER } from "@/lib/verify";
import { PublicProfile } from "./PublicProfile";

const issuerKey = generateSecretKey();
const ISSUER = getPublicKey(issuerKey);
const ARTISAN = getPublicKey(generateSecretKey());
const sha = (data: Uint8Array) => bytesToHex(sha256(data));

/** A valid award, signed like the API does. */
function award(title: string): Event {
  const preimage = crypto.getRandomValues(new Uint8Array(32));
  const paymentHash = sha(preimage);
  return finalizeEvent(
    {
      kind: 8,
      created_at: 1_763_200_000,
      content: title,
      tags: [
        ["a", `30009:${ISSUER}:${BADGE_IDENTIFIER}`],
        ["p", ARTISAN],
        ["attestation", sha(new TextEncoder().encode(`${paymentHash}:${ARTISAN}`))],
        ["payment_hash", paymentHash],
        ["preimage", bytesToHex(preimage)],
        ["client", "c".repeat(64)],
        ["network", "testnet"],
        ["t", "tekki-pass"],
      ],
    },
    issuerKey,
  );
}

const asApi = (event: Event): PublishedAttestation => ({
  event_id: event.id,
  title: event.content,
  payment_hash: "",
  published_at: "2026-11-15T10:00:00Z",
  event_json: JSON.stringify(event),
});

describe("mergeAttestations", () => {
  it("keeps one entry per event and records where it was found", () => {
    const both = award("Carrelage");
    const relayOnly = award("Peinture");
    const apiOnly = award("Plomberie");

    const merged = mergeAttestations([both, relayOnly], [asApi(both), asApi(apiOnly)]);

    expect(merged.map((m) => [m.eventId, m.source])).toEqual([
      [both.id, "both"],
      [relayOnly.id, "relays"],
      [apiOnly.id, "api"],
    ]);
  });
});

describe("PublicProfile", () => {
  beforeEach(() => {
    vi.spyOn(api, "issuer").mockResolvedValue({
      pubkey: ISSUER,
      network: "testnet",
      relays: ["ws://localhost:7777"],
    });
  });
  afterEach(() => vi.restoreAllMocks());

  it("shows proofs read from the relays even when the API knows nothing", async () => {
    vi.spyOn(relays, "fetchAwardsFromRelays").mockResolvedValue([award("Pose de faïence")]);
    vi.spyOn(api, "attestations").mockResolvedValue([]);

    render(<PublicProfile pubkey={ARTISAN} />);

    expect(await screen.findByRole("heading", { name: "Pose de faïence" })).toBeInTheDocument();
    expect(screen.getByText(/lues directement sur le réseau Nostr/i)).toBeInTheDocument();
    expect(screen.getByText(/✓ Vérifié/)).toBeInTheDocument();
  });

  it("falls back to the API when relays are unreachable, still verifying locally", async () => {
    vi.spyOn(relays, "fetchAwardsFromRelays").mockRejectedValue(new Error("offline"));
    vi.spyOn(api, "attestations").mockResolvedValue([asApi(award("Maçonnerie"))]);

    render(<PublicProfile pubkey={ARTISAN} />);

    expect(await screen.findByRole("heading", { name: "Maçonnerie" })).toBeInTheDocument();
    expect(screen.getByText(/Réseau Nostr injoignable/i)).toBeInTheDocument();
  });

  it("flags a forged event instead of trusting it", async () => {
    const forged = { ...award("Chantier inventé"), content: "Chantier modifié" };
    vi.spyOn(relays, "fetchAwardsFromRelays").mockResolvedValue([forged]);
    vi.spyOn(api, "attestations").mockResolvedValue([]);

    render(<PublicProfile pubkey={ARTISAN} />);

    expect(await screen.findByText(/Non vérifié : Signature invalide/)).toBeInTheDocument();
    expect(screen.getByText(/^0$/)).toBeInTheDocument();
  });

  it("explains the error when nothing can be loaded", async () => {
    vi.spyOn(relays, "fetchAwardsFromRelays").mockRejectedValue(new Error("offline"));
    vi.spyOn(api, "attestations").mockRejectedValue(new ApiError("network", "", 0));

    render(<PublicProfile pubkey={ARTISAN} />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/Vérifie ton réseau/);
  });
});
