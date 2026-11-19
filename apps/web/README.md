# Tekki-Pass web (PWA)

Next.js app for artisans, clients and verifiers. See the root README to run it.

## 3G and offline (task F4)

Most users are on Android phones with slow or unstable 3G. Two rules:

1. **Every page loads only what it needs.** Client links (`/a/…`) never load the signing
   or recovery-phrase code; the public profile (`/p/…`) does not load the recovery-phrase
   code; the wallet module (Breez SDK, about 4 MB compressed) loads only when the artisan
   opens their wallet.
2. **The service worker** (`public/sw.js`) keeps the app usable offline:

   | What                                       | Strategy                                                       |
   | ------------------------------------------ | -------------------------------------------------------------- |
   | `/_next/static/*` (JS, CSS, wallet module) | Cache first: downloaded once                                   |
   | `/`, `/artisan`, `/offline`                | From the cache at once, refreshed in the background            |
   | Public profiles `/p/…`                     | Network first (4 s timeout), cached copy offline               |
   | Client links `/a/…`                        | Network only (the URL carries the token), offline page if down |
   | `/api/…`, `/wallet-config`                 | Never cached                                                   |

### Page weight (gzip, JS + CSS + HTML, production build, 18 Nov 2026)

| Page                    | Before F4 | After F4 | At 400 kbit/s (slow 3G) |
| ----------------------- | --------- | -------- | ----------------------- |
| `/`                     | 176 KiB   | 176 KiB  | 3.6 s                   |
| `/a/…` (client link)    | 231 KiB   | 187 KiB  | 3.8 s                   |
| `/p/…` (public profile) | 250 KiB   | 216 KiB  | 4.4 s                   |
| `/artisan`              | 239 KiB   | 217 KiB  | 4.5 s                   |

About 176 KiB is the shared Next.js and React runtime. After the first visit, the service
worker serves it from the phone: later visits only download the page itself.

### Test on a real phone

1. Open the deployed site in Chrome on an entry-level Android phone.
2. On a computer: `chrome://inspect` → the phone's tab → **Network**: throttling
   **Slow 3G**, and **Application → Service workers**: check `sw.js` is activated.
3. Measure: the first load of `/a/…` and `/p/…`, then a second load (from cache).
4. Turn on airplane mode: `/artisan` still opens, `/p/…` shows its last copy, and a
   client link shows the "Pas de connexion" page.
5. Lighthouse (Chrome DevTools, **Mobile**): note the Performance score and LCP.
6. Wallet: first opening on 3G (download of the module), then a second opening (cached).

Write the results in the table above and in docs/adr/0005 ("Still to check", point 3).
