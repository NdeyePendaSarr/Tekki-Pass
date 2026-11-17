import { fireEvent, render, screen } from "@testing-library/react";
import { generateSecretKey, getPublicKey } from "nostr-tools";
import { api, ApiError, type AttestationRequest } from "@/lib/api";
import type { Identity } from "@/lib/identity";
import { MyRequests } from "./MyRequests";

const secretKey = generateSecretKey();
const identity: Identity = { pubkey: getPublicKey(secretKey), npub: "npub1test", secretKey };

function request(token: string, status: AttestationRequest["status"]): AttestationRequest {
  return {
    token,
    status,
    title: `Chantier ${token}`,
    artisan_pubkey: identity.pubkey,
    amount_sat: 210,
    network: "testnet",
    bolt11: null,
    payment_hash: null,
    invoice_expires_at: null,
    event_id: null,
  };
}

describe("MyRequests", () => {
  afterEach(() => vi.restoreAllMocks());

  it("lists each request with a plain-French status, signed with the artisan key", async () => {
    const myRequests = vi
      .spyOn(api, "myRequests")
      .mockResolvedValue([request("a", "awaiting_client"), request("b", "published")]);

    render(<MyRequests identity={identity} version={0} />);

    expect(await screen.findByText("Chantier a")).toBeInTheDocument();
    expect(screen.getByText("En attente de confirmation du client")).toBeInTheDocument();
    expect(screen.getByText("✓ Preuve publiée")).toBeInTheDocument();
    expect(myRequests).toHaveBeenCalledWith(identity.pubkey, secretKey);
  });

  it("offers to resend the link only while the client has something to do", async () => {
    vi.spyOn(api, "myRequests").mockResolvedValue([
      request("a", "awaiting_client"),
      request("b", "awaiting_payment"),
      request("c", "published"),
      request("d", "expired"),
    ]);

    render(<MyRequests identity={identity} version={0} />);

    const resend = await screen.findAllByRole("link", { name: /Renvoyer le lien/ });
    expect(resend).toHaveLength(2);
    expect(resend[0]).toHaveAttribute(
      "href",
      expect.stringContaining(encodeURIComponent(`${window.location.origin}/a/a`)),
    );
  });

  it("shows an empty state and reloads on demand", async () => {
    const myRequests = vi.spyOn(api, "myRequests").mockResolvedValue([]);

    render(<MyRequests identity={identity} version={0} />);

    expect(await screen.findByText(/Aucune demande/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Actualiser" }));
    await screen.findByRole("button", { name: "Actualiser" });
    expect(myRequests).toHaveBeenCalledTimes(2);
  });

  it("explains errors in plain French", async () => {
    vi.spyOn(api, "myRequests").mockRejectedValue(new ApiError("invalid_auth", "", 401));

    render(<MyRequests identity={identity} version={0} />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/date et l'heure/);
  });
});
