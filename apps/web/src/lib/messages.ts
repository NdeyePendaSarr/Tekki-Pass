/**
 * Plain-French messages for API error codes. Each one says what to do next
 * (UX principle from the brief: "chaque message dit quoi faire").
 */
import { ApiError } from "./api";

const MESSAGES: Record<string, string> = {
  network: "Pas de connexion. Vérifie ton réseau puis réessaie.",
  api_unreachable: "Le service ne répond pas. Réessaie dans un instant.",
  not_found: "Ce lien n'existe pas ou n'est plus valable. Demande un nouveau lien à l'artisan.",
  invalid_state: "Ce chantier a déjà été confirmé.",
  client_cap_reached:
    "Ce numéro a déjà confirmé beaucoup de chantiers ce mois-ci. Réessaie plus tard.",
  invalid_phone: "Numéro invalide. Écris-le comme 77 123 45 67.",
  invalid_input: "Une information est incorrecte. Vérifie ce que tu as écrit.",
  publication_failed:
    "Paiement reçu. La preuve n'est pas encore publiée : réessaie dans un instant.",
  not_configured: "Le service n'est pas encore prêt. Préviens l'équipe Tekki-Pass.",
  invalid_proof: "La preuve de paiement est invalide. Préviens l'équipe Tekki-Pass.",
};

const FALLBACK = "Une erreur est survenue. Réessaie dans un instant.";

export function errorMessage(error: unknown): string {
  return error instanceof ApiError ? (MESSAGES[error.code] ?? FALLBACK) : FALLBACK;
}
