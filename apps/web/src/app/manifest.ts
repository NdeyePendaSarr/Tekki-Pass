import type { MetadataRoute } from "next";

/** Web app manifest served at /manifest.webmanifest (makes the PWA installable). */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Tekki-Pass",
    short_name: "Tekki-Pass",
    description: "Preuves de travail vérifiables pour les artisans.",
    lang: "fr",
    start_url: "/",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#0f5132",
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" }],
  };
}
