import type { Payment } from "@breeztech/breez-sdk-spark/ssr";
import {
  fetchWalletConfig,
  lightningUsername,
  saveLightningAddress,
  savedLightningAddress,
  toReceivedPayment,
} from "./wallet";

const PUBKEY = "a".repeat(64);

describe("wallet helpers", () => {
  afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("derives a stable, anonymous Lightning user name from the public key", () => {
    expect(lightningUsername("0123456789abcdef" + "0".repeat(48))).toBe("tekki0123456789");
  });

  it("remembers the Lightning address per profile", () => {
    expect(savedLightningAddress(PUBKEY)).toBeNull();
    saveLightningAddress(PUBKEY, "tekkiaaaa@breez.tips");
    expect(savedLightningAddress(PUBKEY)).toBe("tekkiaaaa@breez.tips");
    expect(savedLightningAddress("b".repeat(64))).toBeNull();
  });

  it("keeps the wallet off when the server has no configuration", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("", { status: 500 }));
    expect(await fetchWalletConfig()).toEqual({ enabled: false, network: "mainnet" });
  });

  it("summarizes a received Lightning payment", () => {
    const payment = {
      id: "p1",
      paymentType: "receive",
      status: "completed",
      amount: 210n,
      fees: 0n,
      timestamp: 1_763_400_000,
      method: "lightning",
      details: { type: "lightning", description: "Tekki-Pass: Carrelage" },
    } as unknown as Payment;
    expect(toReceivedPayment(payment)).toEqual({
      id: "p1",
      amountSats: 210,
      timestamp: 1_763_400_000,
      description: "Tekki-Pass: Carrelage",
    });
  });
});
