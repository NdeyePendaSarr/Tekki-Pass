import { fireEvent, render, screen } from "@testing-library/react";
import { api, ApiError, type AttestationRequest } from "@/lib/api";
import { ClientAttestation } from "./ClientAttestation";

const base: AttestationRequest = {
  token: "tok",
  status: "awaiting_client",
  title: "Carrelage cuisine",
  artisan_pubkey: "a".repeat(64),
  amount_sat: 210,
  network: "testnet",
  bolt11: null,
  payment_hash: null,
  invoice_expires_at: null,
  event_id: null,
};

describe("ClientAttestation", () => {
  afterEach(() => vi.restoreAllMocks());

  it("asks the client to confirm, then shows the payment", async () => {
    vi.spyOn(api, "getRequest").mockResolvedValue(base);
    const confirm = vi.spyOn(api, "confirm").mockResolvedValue({
      ...base,
      status: "awaiting_payment",
      bolt11: "lnfake210n1abc",
    });
    render(<ClientAttestation token="tok" />);

    expect(await screen.findByRole("heading", { name: "Carrelage cuisine" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/numéro de téléphone/i), {
      target: { value: "77 123 45 67" },
    });
    fireEvent.click(screen.getByRole("button", { name: /je confirme/i }));

    expect(await screen.findByText(/paiement de la preuve/i)).toBeInTheDocument();
    expect(confirm).toHaveBeenCalledWith("tok", "77 123 45 67");
    expect(screen.getByRole("button", { name: /simuler le paiement/i })).toBeInTheDocument();
  });

  it("explains errors in plain French", async () => {
    vi.spyOn(api, "getRequest").mockRejectedValue(new ApiError("not_found", "", 404));
    render(<ClientAttestation token="nope" />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/demande un nouveau lien/i);
  });

  it("celebrates a published proof", async () => {
    vi.spyOn(api, "getRequest").mockResolvedValue({ ...base, status: "published" });
    render(<ClientAttestation token="tok" />);

    expect(await screen.findByText(/la preuve est publiée/i)).toBeInTheDocument();
  });
});

describe("invoiceQrValue", () => {
  it("writes the invoice in upper case, the compact form that scans easily", async () => {
    const { invoiceQrValue } = await import("./ClientAttestation");
    expect(invoiceQrValue("lnbc2100n1pabc")).toBe("LIGHTNING:LNBC2100N1PABC");
  });
});
