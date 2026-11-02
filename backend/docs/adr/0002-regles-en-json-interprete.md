# ADR-0002 — Moteur de règles : configuration JSON interprétée, pas de DSL ni de plugins

Statut : accepté · Date : 2026-10-26

## Contexte
L'administration doit régler pondérations, seuils éliminatoires, bonus et départage, et **ajouter un critère sans développeur**. Les configurations doivent être versionnées et rejouables.

## Options
1. **JSON déclaratif interprété** : listes `criteria`, `eliminatory`, `bonuses`, `tie_break` avec opérateurs en liste blanche ; les nouveaux critères lisent `Student.attributes`.
2. **Mini-langage d'expressions** (ex. `gpa * 0.5 + (english > 800 ? 10 : 0)`) : plus expressif, mais un parseur à écrire, tester, sécuriser et documenter.
3. **Plugins Python** chargés dynamiquement : « sans modifier le code » devient faux, et c'est une exécution de code arbitraire.

## Décision
Option 1. Un critère = une entrée JSON ; la normalisation `(valeur − min)/(max − min)` rend les poids comparables ; `default` gère les attributs absents ; `validate` renvoie toutes les erreurs d'un coup.

## Conséquences
- `+` Aucun `eval`, surface d'attaque nulle (A03) ; formulaire admin trivial à générer depuis le schéma ; empreinte de contenu = identifiant de version.
- `+` Prouvé : le banc ajoute un bonus et un malus par configuration seule et obtient une affectation différente et toujours stable.
- `−` Pas de combinaisons arbitraires (produit de critères, conditions imbriquées). Si un besoin réel apparaît, ajouter un opérateur ou un type de règle, pas un langage.
- `overrides` par université (criteria et/ou bonuses) : prévu dès le départ, sans changement d'algorithme ; les seuils peuvent viser un attribut ajouté côté université (`University.attributes`).
- `validate` reçoit les clés réellement présentes dans les données : une clé inconnue (faute de frappe, attribut jamais renseigné) est refusée avant le run.
