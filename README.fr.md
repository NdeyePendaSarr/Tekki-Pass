# Tekki-Pass

> Chaque chantier payé en Lightning devient une preuve de travail vérifiable par n'importe qui, même sans nous.

🇬🇧 [English version](README.md)

**Tekki-Pass** (« tekki » = réussir, en wolof) donne aux artisans du BTP sénégalais (carreleurs, maçons, électriciens, plombiers) un historique de travail public et vérifiable. Le client confirme un chantier terminé et paie un micro-frais en Lightning. Tekki-Pass signe alors une attestation et la publie sur Nostr, et n'importe qui peut la vérifier en scannant un QR code.

Projet du [Dakar Bitcoin Hack 2026](https://dakar-bitcoin-hack-2026.devpost.com/) (BTrust).

**État (16 nov. 2026) :** tout le parcours de démo fonctionne de bout en bout avec un paiement simulé. Le vrai paiement Lightning (Breez SDK - Spark) est en cours d'intégration.

---

## Parcours pour le jury

> TODO : lien vers la démo en ligne et la vidéo de 3 minutes une fois déployées.

Persona de démo (fictif) : **Moussa**, carreleur à Dakar.

| # | Étape | Où (démo locale) | État |
| --- | --- | --- | --- |
| 1 | Moussa crée son profil : 12 mots de récupération, vérification de 3 mots, code à 6 chiffres. Sa clé Nostr est dérivée de ces mots (NIP-06). | `/artisan` | ✅ |
| 2 | Il décrit un chantier terminé et envoie le lien à son client par WhatsApp. La demande est signée avec sa clé (NIP-98). | `/artisan` | ✅ (signature depuis l'appli web : en cours) |
| 3 | Le client ouvre le lien, confirme le chantier avec son numéro et voit le QR code de paiement. | `/a/<token>` | ✅ |
| 4 | Le client paie le micro-frais en Lightning. Les sats arrivent dans le wallet de Moussa. | Wallet Lightning | 🟡 paiement simulé (« Simuler le paiement ») ; wallet Breez en cours |
| 5 | Tekki-Pass vérifie la preuve de paiement, signe l'attestation (badge NIP-58) et la publie sur les relais Nostr. | API | ✅ |
| 6 | Un vérificateur scanne le QR code de Moussa et voit chaque chantier « ✓ Vérifié », contrôlé dans son propre navigateur. | `/p/<pubkey>` | ✅ |

## Démarrage rapide

Prérequis : Docker avec Compose v2.

```bash
cp .env.example .env        # facultatif : les valeurs par défaut suffisent en local
docker compose up --build
```

- Appli web : http://localhost:3000 (commencer par « Je suis artisan »)
- Documentation de l'API : http://localhost:8000/docs
- Relais Nostr local : ws://localhost:7777

Ports déjà utilisés ? Définis `WEB_PORT`, `API_PORT` et `RELAY_PORT` dans `.env`.

La démo locale est sans risque : paiements simulés, relais local uniquement (rien n'est publié sur les relais publics), clés jetables générées au démarrage.

Développement sans Docker : voir [CONTRIBUTING.md](CONTRIBUTING.md#local-development).

## Architecture

Les sats vont directement dans le wallet de l'artisan, et les attestations sur des relais Nostr publics. L'API ne garde ni l'un ni l'autre.

```mermaid
flowchart LR
  A[PWA artisan<br/>wallet self-custodial + clé Nostr] -- chantier + lien, signé NIP-98 --> API[API Tekki-Pass<br/>FastAPI]
  A -- lien WhatsApp --> C[Page client]
  C -- paie le micro-frais --> A
  C -- confirmation --> API
  API -- vérifie la preuve de paiement<br/>LNURL-pay + LUD-21 --> A
  API -- badge NIP-58 signé --> R[(Relais Nostr publics)]
  V[Vérificateur<br/>QR code] -- vérifie dans le navigateur --> R
  API --- DB[(PostgreSQL<br/>demandes uniquement)]
```

| Dossier    | Contenu                                                                     |
| ---------- | --------------------------------------------------------------------------- |
| `apps/web` | PWA Next.js + TypeScript (mobile d'abord, français d'abord, wolof prévu)    |
| `apps/api` | FastAPI, Python 3.12, entièrement typé. Orchestration seulement : ne détient jamais de fonds |
| `docs/adr` | Décisions d'architecture (ADR)                                              |
| `.github`  | CI, modèles d'issue et de PR                                                |

Comment fonctionne la confiance :

- **Preuve de paiement :** une facture Lightning payée révèle une preimage dont le SHA-256 est le hash du paiement. L'attestation contient les deux.
- **Preuve de l'émetteur :** l'attestation est un événement Nostr signé par la clé de Tekki-Pass, publié avec la définition de son badge (kind 30009).
- **Vérifiable par tous :** la page publique revérifie la signature, la clé de l'émetteur et la preuve de paiement dans le navigateur du visiteur, sans faire confiance à notre serveur.

Décisions clés : voir les [ADR](docs/adr/) (wallet self-custodial, attestations Nostr NIP-58, micro-frais Lightning, environnements testnet et mainnet, SDK Lightning Breez Spark).

## Contraintes

- **Utilisateurs :** des artisans parfois peu à l'aise avec l'écrit, sur des Android d'entrée de gamme en 3G. L'interface utilise des mots simples (« paiement », « preuve »), un texte de 16 px minimum et un contraste WCAG AA.
- **Souveraineté :** Tekki-Pass ne détient ni l'argent ni les preuves de l'artisan.
- **Vie privée :** ni nom ni numéro sur Nostr, seulement un hash protégé par une clé secrète (HMAC) du numéro du client. Aucune donnée personnelle dans les logs.
- **Sécurité :** pas de cryptographie maison, dépendances épinglées, secrets uniquement en variables d'environnement. Voir [SECURITY.md](SECURITY.md).
- **Réseau :** testnet par défaut. Mainnet seulement pour une démo explicite, en attendant la réponse des organisateurs (ADR 0004).
- **Délai :** soumission le 20 novembre 2026, 20h00 UTC.

Le modèle de menaces complet, avec l'état de chaque protection, figure dans le [README anglais](README.md#threat-model-mvp).

## Indicateurs

Ce que nous mesurerons. Les valeurs cibles seront fixées après les entretiens terrain : aucun chiffre n'est inventé ici.

| Indicateur | Ce qu'il mesure | Source |
| --- | --- | --- |
| Artisans actifs par semaine | Adoption côté offre | Base de données |
| Attestations publiées par semaine | Usage réel | Relais Nostr + base |
| Part des demandes d'attestation payées | Friction côté client | Wallet + base |
| Temps du lien envoyé à l'attestation publiée | Fluidité du parcours | Logs anonymisés |
| Vérifications par QR code | Intérêt des vérificateurs | Page publique |
| Part des comptes avec une sauvegarde vérifiée | Sécurité des fonds | Appli |
| Attestations signalées comme suspectes | Fraude détectée | Signaux anti-collusion |

## Prochaine itération

- **Avant le pitch final :** note vocale → fiche chantier (IA, wolof ou français), interface en wolof, signaux anti-collusion (un client qui atteste tout le monde), connexion d'un wallet existant via NWC.
- **Plus tard :** horodatage OpenTimestamps, émetteurs accrédités (Chambre des Métiers, maîtres d'œuvre agréés), divulgation sélective, score microfinance, API B2B de vérification, paiement de l'acompte ou du chantier en Lightning.

## Questions ouvertes

- TODO : montant du micro-frais (après les entretiens ; 210 sats est une valeur provisoire)
- TODO : mainnet obligatoire ou testnet accepté (question posée aux organisateurs)
- TODO : cadre réglementaire BCEAO / UEMOA sur les crypto-actifs

## Contribuer et licence

Voir [CONTRIBUTING.md](CONTRIBUTING.md) et le [Code de conduite](CODE_OF_CONDUCT.md). Publié sous [licence MIT](LICENSE).
