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
