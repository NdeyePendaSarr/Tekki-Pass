/**
 * Wallet settings for the artisan's browser, read from the server environment at
 * request time (not at build time): setting BREEZ_API_KEY and restarting the web
 * container turns the wallet on, without rebuilding the image.
 *
 * The Breez API key identifies the app to Breez's services and ends up in every
 * browser that runs the SDK (Breez's documented model for web apps): it is not a
 * secret like the issuer key. It is still kept out of Git and of the image.
 */
import { NextResponse } from "next/server";
import type { WalletConfig } from "@/lib/wallet";

export const dynamic = "force-dynamic";

export function GET(): NextResponse<WalletConfig> {
  const apiKey = process.env.BREEZ_API_KEY?.trim() || undefined;
  // Breez Lightning only exists on mainnet (Spark's regtest has no Lightning, ADR 0005).
  const network = process.env.NETWORK === "mainnet" ? "mainnet" : "regtest";
  const config: WalletConfig = apiKey
    ? { enabled: true, network, apiKey }
    : { enabled: false, network };
  return NextResponse.json(config, { headers: { "Cache-Control": "no-store" } });
}
