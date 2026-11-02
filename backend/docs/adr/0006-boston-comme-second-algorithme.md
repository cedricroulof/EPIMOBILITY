# ADR-0006 — Second algorithme : mécanisme de Boston (acceptation immédiate)

Statut : accepté · Date : 2026-10-26

## Contexte
« Au moins 2 algorithmes, dont un mariage stable (Gale-Shapley). Comparatif chiffré : % de premiers vœux, % de non-affectés, rang moyen, stabilité. » Le second doit rendre le comparatif instructif.

## Options
1. **Boston (acceptation immédiate)** : vœu 1 pour tous, admissions définitives, puis vœu 2 sur les places restantes, etc. C'est l'algorithme « intuitif » que beaucoup d'écoles appliquent à la main.
2. **Dictature sérielle par score** : les étudiants servis par score décroissant, chacun prend son meilleur vœu disponible. Sans pondération par université, le score est commun à toutes et cet algorithme donne exactement le même résultat que Gale-Shapley : comparatif vide. (Avec `overrides`, les classements diffèrent et Gale-Shapley redevient distinct ; la stabilité est alors une propriété non triviale, montrée par la ligne « nominal + overrides » du banc.)
3. **Gale-Shapley côté universités** : même résultat que côté étudiants quand les priorités sont communes ; différent avec `overrides`, mais optimal pour les universités, ce qui n'est pas le but.

## Décision
Option 1. Boston maximise mécaniquement le nombre de premiers vœux (optimum atteint université par université) mais produit des paires bloquantes et incite à mentir sur son premier vœu. Le comparatif montre l'arbitrage réel : +6 points de premiers vœux contre 116 paires bloquantes sur le scénario nominal, +9 points contre 250 paires sur le scénario à capacité réduite.

## Conséquences
- `+` Le vérificateur de stabilité a quelque chose à détecter (le banc exige qu'il trouve des paires sur Boston : test du test).
- `+` Les deux algorithmes partagent le même prétraitement (`Problem`) : comparaison à conditions égales.
- Gale-Shapley reste l'algorithme de publication ; Boston est présenté dans le mode « et si » avec son avertissement, et `POST /admin/runs/{id}/publish` refuse un run Boston (`409`).
