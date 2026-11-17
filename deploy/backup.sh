#!/usr/bin/env bash
# Sauvegarde MedMa : base + fichiers du site, copiés hors du volume Docker, avec rétention.
# Usage : backup.sh [site] [jours_de_rétention]
set -euo pipefail
SITE="${1:-dev.chtmed.ma}"
RETENTION_DAYS="${2:-14}"
DEST="/home/deploy/medma/backups/${SITE}"
COMPOSE_DIR="/home/deploy/medma/frappe_docker"

umask 077
mkdir -p "$DEST"
cd "$COMPOSE_DIR"

docker compose -p medma exec -T backend bench --site "$SITE" backup --with-files >/dev/null

# Copie uniquement des fichiers produits dans la dernière heure.
SRC="/home/frappe/frappe-bench/sites/${SITE}/private/backups"
RECENTS=$(docker compose -p medma exec -T backend find "$SRC" -type f -mmin -60 | tr -d '\r')
[ -n "$RECENTS" ] || { echo "ERREUR : aucun fichier de sauvegarde récent" >&2; exit 1; }
while IFS= read -r f; do
  docker compose -p medma cp "backend:${f}" "$DEST/" >/dev/null
done <<< "$RECENTS"

# Rétention sur le dossier hôte
find "$DEST" -type f -mtime +"$RETENTION_DAYS" -delete
chmod 700 "$DEST"; chmod 600 "$DEST"/* 2>/dev/null || true
echo "OK : $(ls -1 "$DEST" | wc -l) fichier(s) dans $DEST"
ls -lh "$DEST" | tail -n +2
