// Tekki-Pass service worker: fast on 3G, usable offline (task F4).
//
// What is cached, and how:
// - /_next/static/* (JS, CSS, the wallet's WASM module): content-hashed, never changes.
//   Cache first: downloaded once, then served from the phone. The wallet module
//   (about 4 MB compressed, docs/adr/0005) is only fetched the first time.
// - App pages ("/", "/artisan", "/offline"): served from the cache at once, refreshed
//   in the background (stale-while-revalidate).
// - Public profiles (/p/...): network first with a timeout, cached copy if offline.
//   They are public by design.
// - Never cached: the API (/api/...), the wallet settings (/wallet-config), client links
//   (/a/...: the URL carries the request token), and Next.js data requests (RSC).
// - No network and nothing cached: the /offline page.

const VERSION = "v2";
const STATIC_CACHE = `tekki-static-${VERSION}`;
const PAGES_CACHE = `tekki-pages-${VERSION}`;
const OFFLINE_URL = "/offline";
const APP_PAGES = ["/", "/artisan", OFFLINE_URL];
const PRECACHE = [...APP_PAGES, "/manifest.webmanifest", "/icon.svg"];
/** On slow 3G, wait this long for a public profile before showing the cached copy. */
const NETWORK_TIMEOUT_MS = 4000;

/** Which strategy serves a request; "network" means the service worker stays out of it. */
function routeFor(request) {
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return "network";
  if (request.headers.get("RSC") || url.searchParams.has("_rsc")) return "network";
  const path = url.pathname;
  if (path.startsWith("/api/") || path === "/wallet-config" || path === "/sw.js") {
    return "network";
  }
  if (path.startsWith("/_next/static/")) return "cache-first";
  if (path.startsWith("/a/")) return "network-or-offline";
  if (path.startsWith("/p/")) return "network-first";
  if (PRECACHE.includes(path)) return "stale-while-revalidate";
  if (request.mode === "navigate") return "network-or-offline";
  return "network";
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(PAGES_CACHE)
      // One by one: a page that fails (e.g. offline during install) must not block the rest.
      .then((cache) => Promise.all(PRECACHE.map((url) => cache.add(url).catch(() => undefined))))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  const current = [STATIC_CACHE, PAGES_CACHE];
  event.waitUntil(
    caches
      .keys()
      .then((names) =>
        Promise.all(
          names
            .filter((name) => name.startsWith("tekki-") && !current.includes(name))
            .map((name) => caches.delete(name)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const route = routeFor(event.request);
  if (route === "network") return;
  event.respondWith(STRATEGIES[route](event));
});

const STRATEGIES = {
  "cache-first": async ({ request }) => {
    const cached = await caches.match(request);
    if (cached) return cached;
    const response = await fetch(request);
    if (response.ok) await put(STATIC_CACHE, request, response.clone());
    return response;
  },

  "stale-while-revalidate": async (event) => {
    const { request } = event;
    const cached = await caches.match(request, { ignoreSearch: true });
    const refresh = fetch(request)
      .then(async (response) => {
        if (response.ok) await put(PAGES_CACHE, request, response.clone());
        return response;
      })
      .catch(() => undefined);
    if (cached) {
      event.waitUntil(refresh);
      return cached;
    }
    return (await refresh) ?? offline();
  },

  "network-first": async ({ request }) => {
    try {
      const response = await withTimeout(fetch(request), NETWORK_TIMEOUT_MS);
      if (response.ok) await put(PAGES_CACHE, request, response.clone());
      return response;
    } catch {
      return (await caches.match(request)) ?? offline();
    }
  },

  "network-or-offline": async ({ request }) => {
    try {
      return await fetch(request);
    } catch {
      return offline();
    }
  },
};

async function put(cacheName, request, response) {
  try {
    const cache = await caches.open(cacheName);
    await cache.put(request, response);
  } catch {
    // Storage full or unavailable: serving still works, only caching is skipped.
  }
}

async function offline() {
  return (
    (await caches.match(OFFLINE_URL)) ??
    new Response("Pas de connexion.", {
      status: 503,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    })
  );
}

function withTimeout(promise, ms) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("timeout")), ms);
    promise.then(
      (value) => {
        clearTimeout(timer);
        resolve(value);
      },
      (error) => {
        clearTimeout(timer);
        reject(error);
      },
    );
  });
}
