# Tekki-Pass — Fiche projet finale

Nov 14, 2026 · @Ndeye Penda SARR

## Identité du projet

**Tekki-Pass transforme chaque chantier payé en Lightning en une preuve de travail vérifiable par n'importe qui, même sans nous.**

| Élément | Valeur |
| --- | --- |
| Nom | Tekki-Pass (« tekki » = réussir, en wolof) |
| Hackathon | [Dakar Bitcoin Hack 2026 by BTrust](https://dakar-bitcoin-hack-2026.devpost.com/), 100 % en ligne |
| Période | 26 octobre – 20 novembre 2026 |
| Deadline de soumission | 20 novembre 2026, 20h00 UTC |
| Pitch final | Date à confirmer (après la soumission) |
| Équipe | 3 personnes : Front & UX, Backend & crypto, Lightning & DevOps |
| Thème couvert | Bitcoin, Lightning, Nostr, IA |
| Obligation minimale | Un wallet Bitcoin ou Lightning fonctionnel |
| Jury | Mouhamadou Kouta (Banxaas), Kelvin Isievwore (BTrust), Peter Tyonum (grantee BTrust), Yogen Ghodke (Hexaware) |

## Problème et utilisateur principal

Dans l'économie informelle sénégalaise, un artisan peut avoir 10 ans de métier sans aucune preuve vérifiable de son travail. Les recommandations sont orales, les papiers se perdent, et les institutions ne croient pas une liste modifiable sur un serveur privé.

**Utilisateur principal : l'artisan du BTP** (carreleur, maçon, électricien, plombier). Il trouve ses clients par le bouche-à-oreille et WhatsApp, et se fait payer en Wave, Orange Money ou espèces.

**Utilisateurs secondaires :** le client qui atteste le chantier, et le vérificateur (recruteur, banque, microfinance, assurance) qui consulte l'historique.

**Persona de démo (fictif) :** Moussa, carreleur à Dakar, veut décrocher de plus gros chantiers et un microcrédit pour s'équiper. Sans preuve de son expérience, il est refusé.

| Aujourd'hui | Avec Tekki-Pass |
| --- | --- |
| Réputation orale, limitée au quartier | Historique public consultable par QR code |
| Preuves papier perdues ou contestées | Attestations signées, publiées sur Nostr |
| Aucune trace des paiements | Chaque attestation liée à un paiement Lightning prouvé |
| Dépendance à une plateforme | Les preuves survivent même si Tekki-Pass disparaît |

À valider sur le terrain : le nombre de chantiers par mois, les moyens de paiement réels et l'acceptation d'un micro-frais. Aucun chiffre d'impact n'est avancé avant les entretiens.

## Solution et parcours de démo

Le client paie un micro-frais en Lightning pour attester un chantier ; l'attestation est signée, publiée sur Nostr et vérifiable par QR code.

**Le parcours unique à démontrer :**

1. **Moussa crée son profil.** Son wallet Lightning self-custodial et sa clé Nostr sont générés. Il sauvegarde sa phrase de récupération.
2. **Il décrit son chantier**, par écrit ou par note vocale (option IA).
3. **Il envoie un lien au client** par WhatsApp.
4. **Le client ouvre le lien**, confirme le chantier et paie le micro-frais en Lightning.
5. **L'attestation est signée et publiée sur Nostr.** Les sats arrivent dans le wallet de Moussa.
6. **Un vérificateur scanne le QR code** et voit les chantiers attestés, chacun avec sa preuve de paiement.

**Pourquoi Bitcoin, Lightning et Nostr :**

| Brique | Rôle | Ce que ça prouve |
| --- | --- | --- |
| Lightning | Micro-paiement du client | Chaque attestation a un coût réel : en fabriquer 100 fausses coûte cher |
| Preimage de la facture | Preuve cryptographique du paiement | Le paiement a bien eu lieu |
| Signature Nostr (secp256k1) | Signature de l'attestation | Qui a émis l'attestation |
| Relais Nostr publics | Publication | Les preuves restent accessibles sans Tekki-Pass |

Phrase clé du pitch : *« Tekki-Pass ne garde ni l'argent ni les preuves : les deux appartiennent à l'artisan. »*

## Choix structurants retenus

L'équipe a validé les quatre recommandations le 14 novembre 2026.

| Décision | Choix retenu | Pourquoi | Ce qu'on dit au jury |
| --- | --- | --- | --- |
| 1. Ce que paie le client | Un micro-frais d'attestation en sats ; le chantier reste payé en Wave, Orange Money ou espèces | Adoption réaliste, pas de changement d'habitude de paiement | Version cible : acompte ou chantier entier en Lightning |
| 2. Wallet | Wallet Lightning self-custodial intégré à l'appli ; NWC en bonus | Remplit l'obligation minimale et la promesse de souveraineté | « Tekki-Pass ne touche jamais l'argent » |
| 3. Attestations | Événements Nostr signés (badges NIP-58) sur relais publics ; OpenTimestamps en bonus | Dans le thème, vérifiable sans nous | « Les preuves survivent à Tekki-Pass » |
| 4. IA | Note vocale wolof ou français → fiche chantier structurée | Lève le frein de l'écrit | Optionnelle avant soumission, prévue avant le pitch final |

**Émetteur de l'attestation dans le MVP :** Tekki-Pass signe en tant qu'émetteur, avec le hash du paiement et le hash du numéro du client. On l'assume au pitch : la Chambre des Métiers ou des maîtres d'œuvre agréés deviendront émetteurs ensuite.

**À vérifier avant de coder :** un SDK Lightning self-custodial compatible avec la stack (PWA Next.js + FastAPI).

## Périmètre MVP

Un seul parcours qui marche de bout en bout vaut mieux que cinq fonctions à moitié faites.

| Priorité | Fonctionnalité | Échéance |
| --- | --- | --- |
| Indispensable | Profil artisan, wallet Lightning, clé Nostr, sauvegarde de récupération | Soumission (20 nov.) |
| Indispensable | Création d'une demande d'attestation + lien partageable | Soumission |
| Indispensable | Page client : confirmation + paiement du micro-frais | Soumission |
| Indispensable | Attestation signée et publiée sur Nostr | Soumission |
| Indispensable | Page publique de l'artisan + QR code + vérification | Soumission |
| Indispensable | Installation en une commande, données de démo, README | Soumission |
| Si le temps | Note vocale → fiche chantier (IA) | Avant pitch final |
| Si le temps | Interface en wolof | Avant pitch final |
| Si le temps | Signaux anti-collusion (un client qui atteste tout le monde) | Avant pitch final |
| Si le temps | Connexion d'un wallet existant via NWC | Avant pitch final |
| Plus tard | Horodatage OpenTimestamps | Feuille de route |
| Plus tard | Émetteurs accrédités (Chambre des Métiers) | Feuille de route |
| Plus tard | Divulgation sélective, score microfinance, API B2B | Feuille de route |
| Plus tard | Paiement de l'acompte ou du chantier en Lightning | Feuille de route |

## Architecture fonctionnelle

Les sats vont directement dans le wallet de l'artisan, et les attestations sur des relais Nostr publics : l'API ne garde ni l'un ni l'autre.

&#91;embedded content: architecture fonctionnelle · 6 briques\]

L'API sert seulement à orchestrer : elle reçoit la confirmation du client et la preuve de paiement, puis signe et publie l'attestation. Le vérificateur lit directement sur Nostr.

## Sécurité dès la conception

Le principe : Tekki-Pass ne détient pas les fonds de l'artisan et ne stocke aucune donnée personnelle en clair sur Nostr.

| Menace | Exemple | Parade dans le MVP | Plus tard |
| --- | --- | --- | --- |
| Fausses attestations (collusion) | Un complice paie et atteste des chantiers fictifs | Micro-frais obligatoire, plafond d'attestations par client | Signaux de graphe, émetteurs accrédités |
| Perte ou vol du téléphone | Moussa perd son wallet et ses clés | Phrase de récupération sauvegardée dès l'inscription, code PIN local | Récupération sociale |
| Usurpation d'émetteur | Quelqu'un publie une attestation au nom de Tekki-Pass | Vérification de la clé publique de l'émetteur sur la page de vérification | Registre public des émetteurs |
| Rejeu d'une attestation | Une même preuve réutilisée pour un autre artisan | Identifiant unique lié au hash du paiement et à la clé de l'artisan | — |
| Fuite de données personnelles | Numéro du client visible sur un relais public | Seul un hash du numéro est publié ; aucun nom ni numéro dans les logs | Divulgation sélective |
| Vol de secrets serveur | Clé émetteur ou clés d'API exposées | Secrets en variables d'environnement, jamais commités ; moindre privilège | Coffre à secrets |
| Entrées malveillantes | Injection dans la description du chantier | Validation stricte de toutes les entrées, limitation de débit | — |

**Règles d'équipe :** pas de cryptographie maison, uniquement des bibliothèques Bitcoin, Lightning et Nostr reconnues ; dépendances épinglées ; le modèle de menaces figure dans le README.

## Principes UX/UI

L'appli doit être utilisable par un artisan peu à l'aise avec l'écrit, sur un Android d'entrée de gamme en 3G.

- **Légèreté :** PWA mobile d'abord, peu de JavaScript, images compressées, page publique lisible sans compte.
- **Mots simples :** « paiement » plutôt que « facture Lightning », « preuve » plutôt que « credential », zéro jargon crypto côté client.
- **Langues :** français d'abord, wolof prévu avant le pitch final.
- **Erreurs utiles :** chaque message dit quoi faire (« Paiement non reçu. Vérifie ta connexion puis réessaie. »).
- **Lisibilité :** contraste conforme WCAG AA, texte de 16 px minimum, boutons larges et faciles à toucher.
- **Sauvegarde guidée :** un écran dédié pour la phrase de récupération, avec une vérification avant de continuer.
- **Partage naturel :** le lien d'attestation part par WhatsApp en un geste.
- **Test réel :** chaque parcours est testé sur un vrai téléphone avec le réseau bridé en 3G avant la soumission.

## Indicateurs à suivre

Les valeurs cibles seront fixées après les entretiens terrain ; aucune n'est inventée ici.

| Indicateur | Ce qu'il mesure | Source |
| --- | --- | --- |
| Artisans actifs par semaine | Adoption côté offre | Base Tekki-Pass |
| Attestations publiées par semaine | Usage réel | Relais Nostr + base |
| Part des demandes d'attestation payées | Friction côté client | Wallet + base |
| Temps du lien envoyé à l'attestation publiée | Fluidité du parcours | Logs anonymisés |
| Nombre de vérifications par QR code | Intérêt des vérificateurs | Page publique |
| Part des comptes ayant sauvegardé leur récupération | Sécurité des fonds | Appli |
| Attestations signalées comme suspectes | Fraude détectée | Signaux anti-collusion |

**Entretiens terrain (5 artisans minimum) :** comment trouves-tu tes clients ? As-tu perdu un chantier faute de preuve ? Combien de chantiers par mois ? Comment te paie-t-on ? Accepterais-tu qu'un client paie quelques centaines de FCFA pour t'attester ?

## Modèle économique

Les attestations restent gratuites à vérifier sur Nostr ; on vend le service autour, pas l'accès aux preuves.

| Source de revenu | Payeur | Statut |
| --- | --- | --- |
| Petite commission sur le micro-frais d'attestation | Client de l'artisan | Possible dès le MVP, à valider |
| Score et tableau de bord agrégé d'un artisan | Microfinance, banques | Hypothèse à tester |
| Intégration (API, vérification en masse) | Assurances, grands donneurs d'ordre | Hypothèse à tester |
| Profil artisan premium (mise en avant) | Artisan | Hypothèse à tester |

Ce qui a été retiré du pitch initial : la « barrière infranchissable » (le code sera open source) et la vente d'accès à la vérification (incompatible avec des preuves publiques). L'avantage réel, c'est le réseau d'artisans et d'émetteurs.

## Risques et objections du jury

La question la plus probable vient de Banxaas : comment l'artisan transforme ses sats en francs CFA.

| Objection ou risque | Réponse préparée |
| --- | --- |
| Volatilité et conversion en CFA | Les montants sont faibles ; la conversion passerait par une passerelle locale. Ne pas annoncer de partenariat qui n'existe pas. |
| Cadre légal des crypto-actifs dans l'UEMOA | À vérifier avant la vidéo. Le chantier lui-même reste payé en CFA. |
| « Un complice peut quand même payer le micro-frais » | Oui, mais c'est coûteux à grande échelle ; les signaux de graphe et les émetteurs accrédités réduisent le risque ensuite. |
| « L'artisan va perdre ses clés » | Sauvegarde guidée à l'inscription ; la récupération est un chantier assumé de la feuille de route. |
| « Pourquoi pas une simple base de données ? » | Parce que les preuves doivent survivre à Tekki-Pass et être vérifiables sans nous faire confiance. |
| Le client n'a pas de wallet Lightning | Prévoir un wallet de démo prêt ; à terme, paiement depuis une passerelle mobile money. |
| Risque projet : SDK wallet difficile à intégrer en 6 jours | Décider le SDK le 15 novembre au plus tard ; plan B = vidéo de démo, acceptée par le règlement. |
| Risque projet : réseau mainnet ou testnet non précisé | Poser la question aux organisateurs sur Devpost dès aujourd'hui. |

## Pitch 3 minutes et slides

La démo en direct occupe la moitié du temps : le jury veut voir le parcours marcher.

| Temps | Partie | Contenu |
| --- | --- | --- |
| 0:00–0:30 | Problème | « Moussa, carreleur, 10 ans de métier, zéro preuve. » Refus de chantier ou de crédit. |
| 0:30–2:00 | Démo | Lien WhatsApp → le client confirme et paie → attestation publiée sur Nostr → un vérificateur scanne le QR code. |
| 2:00–2:30 | Impact | Chiffres issus des entretiens terrain uniquement. |
| 2:30–3:00 | Prochaines étapes | IA vocale en wolof, émetteurs accrédités, score microfinance. |

**Les 5 slides :**

1. **Problème :** des compétences réelles, aucune preuve vérifiable.
2. **Solution :** chaque chantier attesté devient une preuve de travail, payée en Lightning et publiée sur Nostr.
3. **Pourquoi Bitcoin :** le paiement rend la fraude coûteuse ; les preuves survivent à Tekki-Pass.
4. **Impact et indicateurs :** les résultats des entretiens et les indicateurs suivis.
5. **Prochaines étapes :** feuille de route et besoins (émetteurs partenaires, passerelle CFA).

**À bannir du pitch :** Zero-Knowledge, « infalsifiable », « sécurité absolue », « < 0,1 % de fraude », « standard national », « barrière infranchissable », « blockchain » sans préciser Bitcoin.

## Livrables et planning

Soumission le 20 novembre avant midi UTC, pour garder une marge sur la deadline de 20h00.

**Livrables exigés par le règlement :**

- [ ] Présentation écrite ou vidéo
- [ ] Dépôt GitHub public
- [ ] MVP accessible en ligne ou vidéo de démo
- [ ] Wallet Bitcoin ou Lightning fonctionnel
- [ ] README : installation, schéma d'architecture, contraintes, indicateurs, prochaine itération
- [ ] Démo de 3 minutes : problème, solution, impact, suites
- [ ] Posts « build in public » (un par jour)

**Avant la soumission :**

- [ ] Idéation finalisée, entretiens terrain, question aux organisateurs, choix du SDK wallet — Nov 15, 2026
- [ ] Parcours principal construit et déployé — Nov 18, 2026
- [ ] Gel des fonctionnalités, tests sur téléphone en 3G, README — Nov 19, 2026
- [ ] Vidéo de 3 minutes et soumission sur Devpost — Nov 20, 2026

**Après la soumission, avant le pitch final (date à confirmer) :**

- [ ] IA : note vocale wolof ou français → fiche chantier
- [ ] Interface en wolof
- [ ] Signaux anti-collusion et connexion NWC
- [ ] Nouveaux entretiens avec des artisans et des vérificateurs (microfinance)
- [ ] Pitch en direct répété trois fois, avec la vidéo en secours

**Répartition :** Front & UX (PWA, textes, tests mobiles) · Backend & crypto (API, signatures, Nostr, modèle de menaces) · Lightning & DevOps (wallet, Docker, déploiement, README). Chacun porte une partie du pitch.

## Questions ouvertes

- [ ] Le réseau attendu : mainnet obligatoire ou testnet accepté ?
- [ ] La taille maximale d'une équipe et la licence open source exigée
- [ ] La date et le format du pitch final
- [ ] Le montant des prix : l'accueil et le règlement ne concordent pas (dollars en BTC ou sats)
- [ ] Le SDK wallet Lightning self-custodial retenu
- [ ] Le montant du micro-frais d'attestation, à fixer après les entretiens
- [ ] Le cadre réglementaire BCEAO/UEMOA sur les crypto-actifs

## Sources

- [Dakar Bitcoin Hack 2026 — page d'accueil Devpost](https://dakar-bitcoin-hack-2026.devpost.com/)
- [Dakar Bitcoin Hack 2026 — règlement](https://dakar-bitcoin-hack-2026.devpost.com/rules)
