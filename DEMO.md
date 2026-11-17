# MedMa — Démonstration

Jeu de données **100 % fictif** (patients, médecins, numéros, montants). Les tarifs sont des **valeurs d'exemple**,
pas les tarifs officiels (TNR/ANAM) : à remplacer par ceux du client avant toute facturation réelle.

## Charger la démo

```bash
bench --site <site> install-app medma_ma          # une seule fois
bench --site <site> execute medma_ma.demo.load_demo
```

Idempotent : relancé, il ne duplique rien. Les identifiants des 4 comptes de démonstration sont écrits dans
`sites/<site>/private/demo_users.txt` (mode 600), jamais dans le dépôt.

## Ce que contient la démo

| Domaine | Contenu |
|---|---|
| Établissement | 1 société (MAD, Africa/Casablanca), 4 cabinets, 3 chambres d'hospitalisation |
| Équipe | 4 praticiens (médecine générale, pédiatrie, cardiologie, gynécologie), horaires, tarifs de consultation |
| Patients | 16 patients fictifs avec **CIN**, groupe sanguin, ville |
| Couverture | CNSS, CNOPS, AMO Tadamon, assureurs privés (taux variables) et patients sans couverture |
| Activité | 30 rendez-vous clos + 8 à venir, constantes, 16 consultations avec ordonnances, 11 analyses validées |
| Pharmacie | 5 médicaments en stock (200 unités chacun), prix de vente et d'achat d'exemple |
| Facturation | 30 factures **partagées** (part organisme / part patient), paiements en espèces, 3 créances ouvertes |
| Remboursement | 4 dossiers : CNSS *payé*, CNOPS *payé partiellement*, AMO Tadamon *envoyé*, assureur privé *brouillon* |
| Hospitalisation | 2 patients hospitalisés (chambres occupées) |
| Comptes | médecin, réception, pharmacie, comptabilité (rôles distincts) |

## Parcours de présentation (≈ 20 min)

1. **Accueil / réception** — ouvrir un patient (CIN, couverture CNSS, 70 %), prendre un rendez-vous.
2. **Médecin** — constantes, consultation, ordonnance (marque + générique), prescription d'analyses.
3. **Laboratoire** — résultat validé, visible dans le dossier patient.
4. **Facturation partagée** — créer une facture : choisir la *couverture du patient* ; la part organisme et la
   part patient se calculent seules. Montrer qu'une couverture d'un autre patient est refusée.
5. **Encaissement** — payer la part patient, laisser la part organisme en attente.
6. **Dossier de remboursement** — « Charger les factures » d'un organisme sur une période, suivre le statut
   (brouillon → envoyé → payé / partiellement payé).
7. **Pharmacie** — niveaux de stock des médicaments.
8. **Hospitalisation** — chambres occupées / vacantes.
9. **Comptabilité** — créances (reste dû par les organismes), balance équilibrée.
10. **Langues** — basculer l'interface en arabe (RTL) / français depuis le profil utilisateur.

## Limites à annoncer honnêtement au client

- Le format du dossier de remboursement est **interne** : l'échange électronique avec les organismes
  (CNSS, CNOPS…) n'est pas intégré.
- Les paiements d'organismes sont enregistrés **sur la facture du patient** (comptabilité simplifiée) ;
  un compte client par organisme reste à mettre en place pour un suivi comptable fin.
- Tarifs officiels (TNR/ANAM) et base nationale des médicaments : **non fournis**, à importer.
- Conformité loi 09-08 / CNDP, sauvegardes et hébergement : à valider pour chaque déploiement réel.
- Rappels WhatsApp/SMS : non implémentés à ce stade.
