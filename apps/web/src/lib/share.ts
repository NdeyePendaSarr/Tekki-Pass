/** Links the artisan sends to their client. */

/** Public URL of the client page for one request. */
export function clientLink(origin: string, token: string): string {
  return `${origin}/a/${token}`;
}

/** WhatsApp share link with a ready-to-send French message. */
export function whatsappLink(title: string, link: string): string {
  const message = `Bonjour, merci de confirmer le chantier « ${title} » sur Tekki-Pass : ${link}`;
  return `https://wa.me/?text=${encodeURIComponent(message)}`;
}
