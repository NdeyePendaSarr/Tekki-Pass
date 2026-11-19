import { GET } from "./route";

describe("/wallet-config", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("keeps the wallet off without a Breez API key", async () => {
    vi.stubEnv("BREEZ_API_KEY", "");
    const response = GET();
    expect(await response.json()).toEqual({ enabled: false, network: "regtest" });
    expect(response.headers.get("cache-control")).toBe("no-store");
  });

  it("turns the wallet on at runtime once the key is set", async () => {
    vi.stubEnv("BREEZ_API_KEY", "test-key");
    vi.stubEnv("NETWORK", "mainnet");
    expect(await GET().json()).toEqual({ enabled: true, network: "mainnet", apiKey: "test-key" });
  });
});
