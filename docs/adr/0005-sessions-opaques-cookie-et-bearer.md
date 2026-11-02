# ADR-0005 — Authentification : sessions opaques en base, cookie pour le web, Bearer pour le mobile

Statut : accepté · Date : 2026-10-26

## Contexte
Comptes étudiant et admin distincts, permissions vérifiées côté serveur, sessions sécurisées. Deux clients : navigateur (cookies naturels) et application native (stockage de jeton).

## Options
1. **Sessions opaques** : jeton aléatoire 32 octets, stocké haché dans `sessions(token_hash, user_id, expires_at)`, transporté en cookie `HttpOnly; Secure; SameSite=Lax` (web) ou `Authorization: Bearer` (mobile).
2. **JWT sans état** : pas de table, mais révocation impossible sans liste noire (donc un état quand même), rotation de clés, erreurs classiques d'implémentation.
3. **OAuth / fournisseur externe** : rien à y gagner pour des comptes fictifs.

## Décision
Option 1. Un seul mécanisme, deux transports. Déconnexion = suppression de la ligne. Expiration 7 jours glissants. Mots de passe en argon2id. Limitation de débit sur `/auth/login`.

## Même origine
Un cookie `SameSite=Lax` n'est pas envoyé vers une API hébergée sur un autre domaine que la SPA. Plutôt que `SameSite=None` (qui réintroduit le CSRF et une vérification d'`Origin` obligatoire), **l'API sert la SPA construite** (`/` → fichiers statiques, `/api/*` → routes) : même origine, pas de CORS en production, un seul déploiement, une seule URL dans le README. En développement, le serveur Vite proxifie `/api` vers l'API locale. Si l'équipe tient à un hébergement séparé de la SPA (Vercel, Netlify), ce choix devient : `SameSite=None; Secure` + `Origin` vérifié sur toute requête modifiante + CORS en liste blanche.

## Conséquences
- `+` Révocation immédiate ; aucun secret de signature à gérer ; code court.
- `+` CSRF couvert par `SameSite=Lax` et la même origine ; l'API n'accepte pas de formulaire HTML.
- `−` Une lecture en base par requête authentifiée (index sur `token_hash`, négligeable à cette échelle).
