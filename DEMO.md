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
| Journée en cours | 6 rendez-vous aujourd'hui, 3 analyses en attente de validation, 2 médicaments en stock bas (alertes visibles dès la connexion) |
| Guide | Espace **Guide démo** : parcours par rôle (médecin, réception, pharmacie, comptabilité) |
| Comptes | médecin, infirmier, laboratoire, réception, pharmacie, comptabilité, direction (rôles distincts, menus et page d'accueil adaptés) |
| Documents imprimables | **Ordonnance**, **Facture** (part organisme / part patient, ICE-IF-RC-Patente) et **Bordereau de remboursement**, en français avec titres arabes |
| Pilotage | Espace **Tableau de bord** : chiffre d'affaires, créances, rendez-vous par praticien, part des organismes, rapport **Créances par organisme** |
| Rappel patient | Bouton **Rappel WhatsApp** sur le rendez-vous (message FR + AR prêt à envoyer) |

## Parcours de présentation (≈ 20 min)

1. **Accueil / réception** — ouvrir un patient (CIN, couverture CNSS, 70 %), prendre un rendez-vous.
2. **Médecin** — constantes, consultation, ordonnance (marque + générique), prescription d'analyses.
3. **Laboratoire** — résultat validé, visible dans le dossier patient.
4. **Facturation partagée** — créer une facture : choisir la *couverture du patient* ; la part organisme et la
   part patient se calculent seules. Montrer qu'une couverture d'un autre patient est refusée.
5. **Encaissement** — payer la part patient, laisser la part organisme en attente.
6. **Dossier de remboursement** — créer un dossier (organisme + période), bouton **Charger les factures**, puis
   *Actions → Marquer comme envoyé*, puis *Actions → Enregistrer un paiement* (montant, date, référence du virement) :
   le paiement est réparti sur les factures de la plus ancienne à la plus récente, les écritures sont créées et le
   statut passe à *payé partiellement* puis *payé*.
7. **Pharmacie** — niveaux de stock des médicaments.
8. **Hospitalisation** — chambres occupées / vacantes.
9. **Comptabilité** — créances (reste dû par les organismes), balance équilibrée.
10. **Impression** — depuis une consultation : *Imprimer → Ordonnance MedMa* ; depuis une facture : *Facture MedMa* ;
    depuis un dossier : *Bordereau MedMa* (PDF prêt à remettre au patient / à l'organisme).
11. **Rappel** — sur un rendez-vous à venir : *Actions → Rappel WhatsApp* ouvre WhatsApp avec le message prérempli.
12. **Pilotage** — compte comptabilité : espace *Tableau de bord* et rapport *Créances par organisme*.
13. **Langues** — basculer l'interface en arabe (RTL) / français depuis le profil utilisateur. Les écrans MedMa
    (organismes, couvertures, remboursements, espaces de travail) sont traduits en arabe ; les écrans natifs de
    Healthcare/ERPNext dépendent des traductions de ces projets.

## Qualité et exploitation

- 18 tests automatisés de la logique métier (`bench --site <site> execute medma_ma.tests.run_all`), exécutés dans
  une transaction annulée, avec contrôle qu'aucune donnée n'est laissée dans la base.
- Sauvegarde et **restauration vérifiée** : voir `deploy/BACKUP.md`.

## Limites à annoncer honnêtement au client

- **Portail patient** (rôle Patient : voir ses rendez-vous, analyses, ordonnances) : non finalisé. Les formulaires web standards de Healthcare
  s'ouvrent mais leurs listes restent vides ; à développer avant de le proposer.
- Le format du dossier de remboursement est **interne** : l'échange électronique avec les organismes
  (CNSS, CNOPS…) n'est pas intégré.
- Les paiements d'organismes sont enregistrés **sur la facture du patient** (comptabilité simplifiée) ;
  un compte client par organisme reste à mettre en place pour un suivi comptable fin.
- Tarifs officiels (TNR/ANAM) et base nationale des médicaments : **non fournis**, à importer.
- Conformité loi 09-08 / CNDP, sauvegardes et hébergement : à valider pour chaque déploiement réel.
- Le rappel WhatsApp est un **lien de partage manuel** (wa.me) : le message est prérempli mais c'est le réceptionniste
  qui l'envoie. L'envoi automatique via l'API WhatsApp Business n'est pas implémenté (il exige un compte et des
  modèles de message validés par Meta).
- Identifiants légaux de la société (ICE, IF, RC, Patente) : valeurs **fictives** dans la démo, à saisir pour chaque client.
- Les médicaments portent des noms de marque courants avec des prix d'exemple : à remplacer avant tout usage réel.
