/**
 * Same-origin proxy to the FastAPI service: the browser calls /api/..., this handler
 * forwards to API_URL (read at runtime, so the same image works in Docker and locally).
 * Avoids CORS and keeps the API address out of the client bundle.
 */
import type { NextRequest } from "next/server";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

async function forward(request: NextRequest, path: string[]): Promise<Response> {
  const target = new URL(`${API_URL}/${path.map(encodeURIComponent).join("/")}`);
  target.search = request.nextUrl.search;
  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers: { "content-type": request.headers.get("content-type") ?? "application/json" },
      body: hasBody ? await request.text() : undefined,
      cache: "no-store",
    });
    return new Response(upstream.body, {
      status: upstream.status,
      headers: { "content-type": upstream.headers.get("content-type") ?? "application/json" },
    });
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
