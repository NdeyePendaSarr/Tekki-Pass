import { fireEvent, render, screen } from "@testing-library/react";
import type { BreezSdk } from "@breeztech/breez-sdk-spark/ssr";
import type { Identity } from "@/lib/identity";
import * as wallet from "@/lib/wallet";
import { Wallet } from "./Wallet";

const identity: Identity = {
  pubkey: "c".repeat(64),
  npub: "npub1test",
  secretKey: new Uint8Array(32),
};
const PHRASE = "abandon ".repeat(11) + "about";

describe("Wallet", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("says payments are simulated until the Breez key is set", async () => {
    vi.spyOn(wallet, "fetchWalletConfig").mockResolvedValue({ enabled: false, network: "mainnet" });
    const connect = vi.spyOn(wallet, "connectWallet");

    render(<Wallet identity={identity} phrase={PHRASE} onAddress={() => {}} />);

    expect(await screen.findByText(/paiements de démonstration sont simulés/)).toBeInTheDocument();
    expect(connect).not.toHaveBeenCalled();
  });

  it("opens on demand, registers the address and shows the balance", async () => {
    const config = { enabled: true, network: "mainnet" as const, apiKey: "k" };
    vi.spyOn(wallet, "fetchWalletConfig").mockResolvedValue(config);
    const sdk = {
      addEventListener: vi.fn().mockResolvedValue("listener"),
      disconnect: vi.fn().mockResolvedValue(undefined),
    } as unknown as BreezSdk;
    const connect = vi.spyOn(wallet, "connectWallet").mockResolvedValue(sdk);
    vi.spyOn(wallet, "walletSummary").mockResolvedValue({
      lightningAddress: "tekkicccccccccc@breez.tips",
      balanceSats: 630,
      payments: [{ id: "p1", amountSats: 210, timestamp: 1_763_400_000, description: "Carrelage" }],
    });
    const onAddress = vi.fn();

    render(<Wallet identity={identity} phrase={PHRASE} onAddress={onAddress} />);
    // Nothing heavy is loaded until the artisan asks for it.
    expect(connect).not.toHaveBeenCalled();
    fireEvent.click(await screen.findByRole("button", { name: "Ouvrir mon portefeuille" }));

    expect(await screen.findByText("630 sats")).toBeInTheDocument();
    expect(screen.getByText("tekkicccccccccc@breez.tips")).toBeInTheDocument();
    expect(screen.getByText("+210 sats")).toBeInTheDocument();
    expect(connect).toHaveBeenCalledWith(PHRASE, config);
    expect(onAddress).toHaveBeenCalledWith("tekkicccccccccc@breez.tips");
  });

  it("asks to retry when the wallet cannot open", async () => {
    vi.spyOn(wallet, "fetchWalletConfig").mockResolvedValue({
      enabled: true,
      network: "mainnet",
      apiKey: "k",
    });
    vi.spyOn(wallet, "connectWallet").mockRejectedValue(new Error("offline"));

    render(<Wallet identity={identity} phrase={PHRASE} onAddress={() => {}} />);
    fireEvent.click(await screen.findByRole("button", { name: "Ouvrir mon portefeuille" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Vérifie ta connexion");
  });
});
