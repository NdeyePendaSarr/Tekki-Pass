/**
 * Same-origin proxy to the FastAPI service: the browser calls /api/..., this handler
 * forwards to API_URL (read at runtime, so the same image works in Docker and locally).
 * Avoids CORS and keeps the API address out of the client bundle.
 */
import type { NextRequest } from "next/server";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

/**
 * Headers passed to the API. Only what the API needs, never cookies:
 * - Authorization: the artisan's NIP-98 signature (Nostr event);
 * - X-Forwarded-For: the client IP chain set by the hosting platform, so the API can
 *   rate-limit per client and not per proxy. The API trusts it only from known proxies.
 */
function upstreamHeaders(request: NextRequest): Headers {
  const headers = new Headers({
    "content-type": request.headers.get("content-type") ?? "application/json",
  });
  const authorization = request.headers.get("authorization");
  if (authorization) headers.set("authorization", authorization);
  const forwardedFor = request.headers.get("x-forwarded-for");
  if (forwardedFor) headers.set("x-forwarded-for", forwardedFor);
  return headers;
}

async function forward(request: NextRequest, path: string[]): Promise<Response> {
  const target = new URL(`${API_URL}/${path.map(encodeURIComponent).join("/")}`);
  target.search = request.nextUrl.search;
  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers: upstreamHeaders(request),
      body: hasBody ? await request.text() : undefined,
      cache: "no-store",
    });
    const headers = new Headers({
      "content-type": upstream.headers.get("content-type") ?? "application/json",
    });
    // Tell the browser when it may retry after a rate limit (429).
    const retryAfter = upstream.headers.get("retry-after");
    if (retryAfter) headers.set("retry-after", retryAfter);
    return new Response(upstream.body, { status: upstream.status, headers });
  } catch {
    return Response.json(
      { detail: { code: "api_unreachable", message: "API unreachable" } },
      { status: 502 },
    );
  }
}

type Context = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, { params }: Context) {
  return forward(request, (await params).path);
}

export async function POST(request: NextRequest, { params }: Context) {
  return forward(request, (await params).path);
}
