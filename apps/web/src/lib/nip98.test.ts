import { sha256 } from "@noble/hashes/sha2.js";
import { bytesToHex } from "@noble/hashes/utils.js";
import { type Event, generateSecretKey, getPublicKey, verifyEvent } from "nostr-tools";
import { api } from "./api";
import { HTTP_AUTH_KIND, nip98Header } from "./nip98";

const URL_ = "http://localhost:3000/api/attestation-requests";

function decode(header: string): Event {
  expect(header.startsWith("Nostr ")).toBe(true);
  const bytes = Uint8Array.from(atob(header.slice("Nostr ".length)), (c) => c.charCodeAt(0));
  return JSON.parse(new TextDecoder().decode(bytes)) as Event;
}

const tag = (event: Event, name: string) => event.tags.find((t) => t[0] === name)?.[1];

describe("nip98Header", () => {
  it("signs a kind 27235 event bound to the URL, the method and the body", () => {
    const key = generateSecretKey();
    const body = JSON.stringify({ title: "Carrelage salle de bain, 12 m²" });

    const event = decode(nip98Header(key, URL_, "post", body));

    expect(verifyEvent(event)).toBe(true);
    expect(event.kind).toBe(HTTP_AUTH_KIND);
    expect(event.pubkey).toBe(getPublicKey(key));
    expect(tag(event, "u")).toBe(URL_);
    expect(tag(event, "method")).toBe("POST");
    expect(tag(event, "payload")).toBe(bytesToHex(sha256(new TextEncoder().encode(body))));
  });

  it("has no payload tag without a body, and uses the given time", () => {
    const event = decode(
      nip98Header(generateSecretKey(), URL_, "GET", undefined, new Date(1_763_200_000_000)),
    );

    expect(tag(event, "payload")).toBeUndefined();
    expect(event.created_at).toBe(1_763_200_000);
  });

  it("produces a different event each time (the API refuses replays)", () => {
    const key = generateSecretKey();
    const first = decode(nip98Header(key, URL_, "POST", "{}"));
    const second = decode(nip98Header(key, URL_, "POST", "{}", new Date(Date.now() + 1000)));

    expect(first.id).not.toBe(second.id);
  });
});

describe("api.createRequest", () => {
  afterEach(() => vi.restoreAllMocks());

  it("sends the signature over the exact body it posts", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response('{"token":"t"}', { status: 201 }));
    const key = generateSecretKey();

    await api.createRequest(getPublicKey(key), "Peinture salon", key);

    const [path, init] = fetchMock.mock.calls[0]!;
    const headers = new Headers(init?.headers);
    const event = decode(headers.get("authorization")!);
    expect(path).toBe("/api/attestation-requests");
    expect(tag(event, "u")).toBe(`${window.location.origin}/api/attestation-requests`);
    expect(tag(event, "payload")).toBe(
      bytesToHex(sha256(new TextEncoder().encode(init?.body as string))),
    );
    expect(event.pubkey).toBe(getPublicKey(key));
  });

  it("does not sign requests that do not need it", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));

    await api.getRequest("tok");

    expect(new Headers(fetchMock.mock.calls[0]![1]?.headers).get("authorization")).toBeNull();
  });
});
