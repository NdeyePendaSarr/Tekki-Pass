// Minimal service worker: makes the app installable and takes control immediately.
// Offline caching (3G-friendly) will be added with the first real pages.
self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});
