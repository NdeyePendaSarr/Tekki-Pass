/**
 * The artisan's self-custodial Lightning wallet: Breez SDK - Spark, in the browser
 * (docs/adr/0005).
 *
 * - Seeded by the artisan's 12-word recovery phrase, the same one as their profile:
 *   a single backup. The phrase never leaves the phone; wallet data lives in IndexedDB.
 * - Registers a Lightning address. The API asks it for invoices and checks payments
 *   (LNURL-pay + LUD-21), so the phone does not need to be online when the client pays.
 * - The SDK (WASM, about 4 MB compressed) is loaded only when the wallet screen opens.
 *
 * The Breez API key is read at runtime from the web server (`/wallet-config`): setting
 * BREEZ_API_KEY on the server and restarting turns the wallet on, without a rebuild.
 */
import type { BreezSdk, Payment } from "@breeztech/breez-sdk-spark/ssr";

export type WalletNetwork = "mainnet" | "regtest";

export interface WalletConfig {
  /** False until the Breez API key is set on the server: payments stay simulated. */
  enabled: boolean;
  network: WalletNetwork;
  apiKey?: string;
}

export interface WalletSummary {
  lightningAddress: string;
  balanceSats: number;
  payments: ReceivedPayment[];
}

export interface ReceivedPayment {
  id: string;
  amountSats: number;
  /** Seconds since the epoch. */
  timestamp: number;
  description?: string;
}

/** IndexedDB database of the SDK. */
const STORAGE_DIR = "tekki-pass-wallet";
const ADDRESS_ITEM_PREFIX = "tekki-pass.lightning-address.v1.";
const RECENT_PAYMENTS = 10;

export async function fetchWalletConfig(): Promise<WalletConfig> {
  const response = await fetch("/wallet-config", { cache: "no-store" });
  if (!response.ok) return { enabled: false, network: "mainnet" };
  return (await response.json()) as WalletConfig;
}

/**
 * Lightning address user name for an artisan, from their public key: stable (the
 * same phone or a restored phone gets the same name) and reveals nothing personal.
 */
export function lightningUsername(pubkey: string): string {
  return `tekki${pubkey.slice(0, 10)}`;
}

/**
 * The artisan's Lightning address, remembered on the phone so that creating a request
 * does not need to load the wallet SDK. Not secret: it is public by design.
 */
export function savedLightningAddress(pubkey: string): string | null {
  try {
    return localStorage.getItem(ADDRESS_ITEM_PREFIX + pubkey);
  } catch {
    return null;
  }
}

export function saveLightningAddress(pubkey: string, address: string): void {
  try {
    localStorage.setItem(ADDRESS_ITEM_PREFIX + pubkey, address);
  } catch {
    // Private mode or full storage: the address is fetched again next time.
  }
}

/** Load the SDK (first time: downloads the WASM module) and open the wallet. */
export async function connectWallet(phrase: string, config: WalletConfig): Promise<BreezSdk> {
  if (!config.enabled || !config.apiKey) throw new Error("wallet not configured");
  const { default: init, connect, defaultConfig } = await import("@breeztech/breez-sdk-spark/ssr");
  await init();
  const sdkConfig = defaultConfig(config.network);
  sdkConfig.apiKey = config.apiKey;
  return connect({
    config: sdkConfig,
    seed: { type: "mnemonic", mnemonic: phrase },
    storageDir: STORAGE_DIR,
  });
}

/** The wallet's Lightning address, registered on first use. */
export async function ensureLightningAddress(sdk: BreezSdk, pubkey: string): Promise<string> {
  const existing = await sdk.getLightningAddress();
  if (existing) return existing.lightningAddress;
  const registered = await sdk.registerLightningAddress({
    username: lightningUsername(pubkey),
    description: "Tekki-Pass",
  });
  return registered.lightningAddress;
}

export async function walletSummary(sdk: BreezSdk, pubkey: string): Promise<WalletSummary> {
  const lightningAddress = await ensureLightningAddress(sdk, pubkey);
  saveLightningAddress(pubkey, lightningAddress);
  const info = await sdk.getInfo({ ensureSynced: false });
  const { payments } = await sdk.listPayments({
    typeFilter: ["receive"],
    statusFilter: ["completed"],
    limit: RECENT_PAYMENTS,
  });
  return {
    lightningAddress,
    balanceSats: info.balanceSats,
    payments: payments.map(toReceivedPayment),
  };
}

export function toReceivedPayment(payment: Payment): ReceivedPayment {
  const details = payment.details;
  return {
    id: payment.id,
    amountSats: Number(payment.amount),
    timestamp: payment.timestamp,
    description: details?.type === "lightning" ? details.description : undefined,
  };
}
