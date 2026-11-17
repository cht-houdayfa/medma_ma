# Sauvegarde et restauration

## Sauvegarder

```bash
deploy/backup.sh <site> [jours_de_rétention]     # défaut : 14 jours
```

Produit base de données + fichiers publics/privés et les copie hors du volume Docker
(`/home/deploy/medma/backups/<site>/`, dossier 700, fichiers 600). Le fichier `*-site_config_backup.json`
contient le mot de passe de la base : ne jamais le copier hors d'un emplacement protégé.

> Les sauvegardes restent **sur le même serveur** : elles protègent d'une erreur de manipulation, pas de la
> perte du serveur. Pour la production, ajouter une copie chiffrée vers un stockage externe.

## Planifier (à installer explicitement)

```cron
30 2 * * * /home/deploy/medma/backup.sh dev.chtmed.ma 14 >> /home/deploy/medma/backups/backup.log 2>&1
```

## Restaurer — toujours d'abord sur un site de test

```bash
bench new-site restauration.localhost --mariadb-root-password <mot de passe root> --admin-password <temporaire>
bench --site restauration.localhost --force restore <fichier>-database.sql.gz --mariadb-root-password <mot de passe root>
```

Comparer ensuite les effectifs (patients, factures, paiements, grand livre) avec le site d'origine, puis supprimer le
site de test (`bench drop-site`). Cette procédure a été exécutée avec succès : résultat identique sur patients,
factures, paiements, dossiers, couvertures, grand livre et applications installées.
