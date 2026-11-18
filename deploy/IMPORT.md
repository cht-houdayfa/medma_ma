# Import des catalogues officiels (médicaments, analyses)

Aucune liste officielle n'est embarquée : la démo contient seulement des exemples. Pour un client réel, importer les
fichiers issus de la source réglementaire (liste des médicaments du Ministère de la Santé ; NABM / tarifs ANAM pour les analyses).

Modèles d'en-têtes : `deploy/import/medicaments.modele.csv` et `deploy/import/analyses.modele.csv` (UTF-8, séparateur `;` ou `,`).

| Fichier | Colonnes (obligatoires en gras) |
|---|---|
| Médicaments | **nom_commercial**, **dci**, **dosage**, **unite**, forme, classe, **ppv**, prix_achat, code |
| Analyses | **code**, **nom**, departement, **tarif** |

```bash
# copier le fichier dans le conteneur, simuler, puis importer
bench --site <site> execute medma_ma.importer.importer_medicaments --kwargs "{'fichier': '/tmp/medicaments.csv', 'dry_run': 1}"
bench --site <site> execute medma_ma.importer.importer_medicaments --kwargs "{'fichier': '/tmp/medicaments.csv'}"
bench --site <site> execute medma_ma.importer.importer_analyses   --kwargs "{'fichier': '/tmp/analyses.csv'}"
```

- Idempotent : relancer met à jour les prix, sans doublon. Plusieurs marques d'une même DCI et d'un même dosage sont
  rattachées au même médicament.
- Les lignes invalides sont ignorées et listées avec leur numéro ; `dry_run: 1` n'écrit rien.
- Le médecin choisit ensuite médicaments et analyses dans ces listes lors de la consultation.
- La conformité au catalogue officiel dépend du fichier fourni, pas du logiciel : à faire valider par le client.

## Listes à compléter

`deploy/import/medicaments.a-completer.csv` et `analyses.a-completer.csv` contiennent des molécules (DCI) et analyses courantes
**sans noms commerciaux, prix ni codes** : ces colonnes sont volontairement vides car elles doivent venir de la source officielle
ou du client. L'import refuse les lignes incomplètes et les liste, donc rien d'inventé n'entre dans la base.

## Liste officielle AMMPS (médicaments)

Source publique : <https://ammps.gov.ma/recherche-medicaments> (robots.txt l'autorise). `deploy/import/ammps_scraper.py <page_debut> <page_fin>`
(1 requête/seconde, ~830 pages, ~14 min) produit `ammps_raw.csv` (nom, dosage, substance, présentation, forme, PPV, PH, statut, laboratoire).
On convertit ensuite vers le modèle ci-dessus en ne gardant que les médicaments **commercialisés avec PPV** (les retirés, suspendus,
non commercialisés ou « AMM sans prix » sont écartés), puis on lance `importer_medicaments`. Chargement du 09/11/2026 : 5 090 spécialités
(2 256 fiches médicament). Les prix sont ceux du site à la date du chargement ; la classe thérapeutique n'y figure pas (« Non classé »).
À relancer périodiquement ; vérifier les conditions de réutilisation des données AMMPS avant diffusion commerciale.
