import { NextRequest } from "next/server";
import { POST } from "./route";

function call(headers: Record<string, string>) {
  const request = new NextRequest("http://localhost:3000/api/attestation-requests", {
    method: "POST",
    headers: { "content-type": "application/json", cookie: "session=secret", ...headers },
    body: JSON.stringify({ title: "Carrelage" }),
  });
  return POST(request, { params: Promise.resolve({ path: ["attestation-requests"] }) });
}

describe("API proxy", () => {
  afterEach(() => vi.restoreAllMocks());

  it("forwards the NIP-98 signature and the client IP, never cookies", async () => {
    const upstream = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 201 }));

    const response = await call({
      authorization: "Nostr abc",
      "x-forwarded-for": "198.51.100.7",
    });

    expect(response.status).toBe(201);
    const [url, init] = upstream.mock.calls[0]!;
    const sent = new Headers(init?.headers);
    expect(String(url)).toBe("http://localhost:8000/attestation-requests");
    expect(sent.get("authorization")).toBe("Nostr abc");
    expect(sent.get("x-forwarded-for")).toBe("198.51.100.7");
    expect(sent.get("cookie")).toBeNull();
  });

  it("passes Retry-After back to the browser on a rate limit", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response('{"detail":{"code":"rate_limited"}}', {
        status: 429,
        headers: { "content-type": "application/json", "retry-after": "42" },
      }),
    );

    const response = await call({});

    expect(response.status).toBe(429);
    expect(response.headers.get("retry-after")).toBe("42");
  });

  it("answers 502 with a stable code when the API is down", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("fetch failed"));

    const response = await call({});

    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({
      detail: { code: "api_unreachable", message: "API unreachable" },
    });
  });
});
