"use client";

import { useEffect } from "react";

/**
 * Registers the service worker in production builds only, so local development
 * never serves stale cached pages. Renders nothing.
 */
export function ServiceWorkerRegistration() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production" || !("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js").catch((error: unknown) => {
      // Offline support is a progressive enhancement: the app works without it.
      console.warn("Service worker registration failed", error);
    });
  }, []);

  return null;
}
