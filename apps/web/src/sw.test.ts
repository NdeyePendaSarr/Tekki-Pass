/**
 * Runs the real public/sw.js against fake service worker APIs (caches, fetch, events):
 * checks what is cached, what never is, and what is shown offline.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

const ORIGIN = "https://tekki.example";
const SOURCE = readFileSync(join(__dirname, "..", "public", "sw.js"), "utf8");

type Listener = (event: FakeEvent) => void;
interface FakeEvent {
  request?: Request;
  respondWith?: (response: Promise<Response>) => void;
  waitUntil: (promise: Promise<unknown>) => void;
}

/** Minimal Cache Storage keyed by URL (path + query). */
class FakeCaches {
  stores = new Map<string, Map<string, Response>>();
  async open(name: string) {
    const store = this.stores.get(name) ?? new Map<string, Response>();
    this.stores.set(name, store);
    return {
      add: async (url: string) => {
        store.set(new URL(url, ORIGIN).href, await network(new Request(new URL(url, ORIGIN))));
      },
      put: async (request: Request, response: Response) => {
        store.set(request.url, response);
      },
    };
  }
  async match(request: Request | string, options?: { ignoreSearch?: boolean }) {
    const url = new URL(typeof request === "string" ? request : request.url, ORIGIN);
    if (options?.ignoreSearch) url.search = "";
    for (const store of this.stores.values()) {
      const hit = store.get(url.href);
      if (hit) return hit.clone();
    }
    return undefined;
  }
  async keys() {
    return [...this.stores.keys()];
  }
  async delete(name: string) {
    return this.stores.delete(name);
  }
  cachedUrls() {
    return [...this.stores.values()].flatMap((store) => [...store.keys()]);
  }
}

let online = true;
const served: string[] = [];
async function network(request: Request): Promise<Response> {
  if (!online) throw new TypeError("Failed to fetch");
  served.push(new URL(request.url).pathname);
  return new Response(`network ${new URL(request.url).pathname}`, { status: 200 });
}

function loadWorker() {
  const listeners = new Map<string, Listener>();
  const caches = new FakeCaches();
  const self = {
    location: new URL(ORIGIN),
    addEventListener: (type: string, listener: Listener) => listeners.set(type, listener),
    skipWaiting: async () => undefined,
    clients: { claim: async () => undefined },
  };
  new Function("self", "caches", "fetch", SOURCE)(self, caches, network);

  async function lifecycle(type: "install" | "activate") {
    const pending: Promise<unknown>[] = [];
    listeners.get(type)!({ waitUntil: (p) => pending.push(p) });
    await Promise.all(pending);
  }

  /** Dispatch a fetch: the response, or null when the worker lets the browser handle it. */
  async function get(path: string, init?: RequestInit & { navigate?: boolean }) {
    const request = new Request(new URL(path, ORIGIN), init);
    if (init?.navigate) Object.defineProperty(request, "mode", { value: "navigate" });
    const answer: { response?: Promise<Response> } = {};
    const background: Promise<unknown>[] = [];
    listeners.get("fetch")!({
      request,
      respondWith: (r) => (answer.response = r),
      waitUntil: (p) => background.push(p),
    });
    const response = answer.response ? await answer.response : null;
    await Promise.all(background);
    return response;
  }

  return { caches, lifecycle, get };
}

describe("service worker", () => {
  beforeEach(() => {
    online = true;
    served.length = 0;
  });

  it("precaches the app pages and the offline page", async () => {
    const sw = loadWorker();
    await sw.lifecycle("install");
    expect(sw.caches.cachedUrls()).toEqual(
      expect.arrayContaining([`${ORIGIN}/`, `${ORIGIN}/artisan`, `${ORIGIN}/offline`]),
    );
  });

  it("downloads hashed static files (the wallet module) only once", async () => {
    const sw = loadWorker();
    const wasm = "/_next/static/media/breez_sdk_spark_wasm_bg.abc123.wasm";
    await sw.get(wasm);
    online = false;
    expect(await (await sw.get(wasm))!.text()).toBe(`network ${wasm}`);
    expect(served.filter((p) => p === wasm)).toHaveLength(1);
  });

  it("opens the artisan space offline from the cache", async () => {
    const sw = loadWorker();
    await sw.lifecycle("install");
    online = false;
    expect(await (await sw.get("/artisan", { navigate: true }))!.text()).toBe("network /artisan");
  });

  it("shows the cached public profile when the network is down", async () => {
    const sw = loadWorker();
    await sw.lifecycle("install");
    await sw.get("/p/abc", { navigate: true });
    online = false;
    expect(await (await sw.get("/p/abc", { navigate: true }))!.text()).toBe("network /p/abc");
  });

  it("never caches client links (they carry the token)", async () => {
    const sw = loadWorker();
    await sw.lifecycle("install");
    await sw.get("/a/secret-token", { navigate: true });
    expect(sw.caches.cachedUrls().some((url) => url.includes("secret-token"))).toBe(false);

    online = false;
    const response = await sw.get("/a/secret-token", { navigate: true });
    expect(await response!.text()).toBe("network /offline"); // the offline page
  });

  it.each([
    ["/api/attestation-requests/t", undefined],
    ["/wallet-config", undefined],
    ["/sw.js", undefined],
    ["/artisan?_rsc=1", undefined],
    ["/artisan", { headers: { RSC: "1" } }],
    ["/api/attestation-requests", { method: "POST", body: "{}" }],
  ])("leaves %s to the network, uncached", async (path, init) => {
    const sw = loadWorker();
    expect(await sw.get(path, init)).toBeNull();
  });

  it("removes caches of older versions on activation", async () => {
    const sw = loadWorker();
    await sw.caches.open("tekki-static-v1");
    await sw.caches.open("other-app");
    await sw.lifecycle("activate");
    expect(await sw.caches.keys()).toEqual(["other-app"]);
  });
});
