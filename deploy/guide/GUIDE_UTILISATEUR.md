# MedMa — Guide utilisateur

Parcours complet d'une visite, de l'accueil du patient jusqu'au remboursement par l'organisme, avec les captures d'écran de chaque rôle. Patient fictif utilisé : *Yassine Guide-Test*.

## 1. Se connecter

Chaque personne de l'établissement a son compte. Selon son rôle, elle ne voit que les écrans qui la concernent.

1. Ouvrez l'adresse de MedMa dans le navigateur, saisissez votre identifiant (adresse e-mail) et votre mot de passe, puis cliquez sur **Login**.

![Écran de connexion](captures/00-connexion.jpg)

*Écran de connexion*

## 2. Réception : accueillir le patient

Rôle : **Réception**. La réception enregistre le patient, prend le rendez-vous et signale l'arrivée.

1. **Page d'accueil.** Les compteurs montrent la salle d'attente, les rendez-vous du jour, les rendez-vous à venir et les factures non soldées. Les *Actions rapides* ouvrent directement un nouveau patient, un nouveau rendez-vous ou une facture.

![Page d'accueil de la réception](captures/01-reception-accueil.jpg)

*Page d'accueil de la réception*

2. **Créer le patient.** Cliquez sur *Nouveau patient*. Renseignez au minimum le prénom, le nom, le sexe, la **CIN**, le mobile et la date de naissance. Décochez *Inviter en tant qu'Utilisateur* sauf si le patient doit avoir un accès au portail.

![Formulaire patient vide](captures/02-reception-nouveau-patient-vide.jpg)

*Formulaire patient vide*

![Formulaire rempli](captures/03-reception-patient-rempli.jpg)

*Formulaire rempli*

3. Enregistrez avec **Ctrl+S** (ou le bouton *Sauvegarder*). La fiche du patient est créée.

![Patient enregistré](captures/04-reception-patient-enregistre.jpg)

*Patient enregistré*

4. **Prendre le rendez-vous.** Cliquez sur *Nouveau rendez-vous*, choisissez le patient, le type de rendez-vous et le praticien.

![Choix du patient](captures/05-reception-rdv-choix-patient.jpg)

*Choix du patient*

5. Cliquez sur **Check Availability**, indiquez la date : les créneaux libres du praticien s'affichent (un créneau grisé est déjà pris).

![Fenêtre de disponibilités](captures/06-reception-rdv-disponibilites-vide.jpg)

*Fenêtre de disponibilités*

![Créneaux disponibles](captures/07-reception-rdv-creneaux.jpg)

*Créneaux disponibles*

6. Choisissez le créneau puis cliquez sur **Book**. Le rendez-vous est créé avec le statut *Prévu*.

![Rendez-vous enregistré](captures/08-reception-rdv-enregistre.jpg)

*Rendez-vous enregistré*

7. **Le jour du rendez-vous**, à l'arrivée du patient, ouvrez son rendez-vous et cliquez sur **Patient arrivé**. Le statut passe à *Checked In* et le patient apparaît dans la salle d'attente du médecin et de l'infirmier.

![Bouton « Patient arrivé »](captures/09-reception-rdv-bouton-patient-arrive.jpg)

*Bouton « Patient arrivé »*

![Arrivée enregistrée](captures/10-reception-patient-arrive-enregistre.jpg)

*Arrivée enregistrée*

![Le compteur « Patients en salle d'attente » passe à 1](captures/11-reception-accueil-patient-en-attente.jpg)

*Le compteur « Patients en salle d'attente » passe à 1*

## 3. Infirmier : prendre les constantes

Rôle : **Infirmier**.

1. **Page d'accueil.**

![Espace Soins infirmiers](captures/61-infirmier-accueil.jpg)

*Espace Soins infirmiers*

2. Ouvrez *Constantes* puis *Nouveau* : choisissez le patient, saisissez température, pouls, fréquence respiratoire, tension (systolique / diastolique), taille et poids.

![Nouvelles constantes](captures/12-infirmier-constantes-vide.jpg)

*Nouvelles constantes*

![Constantes saisies (la tension s'affiche automatiquement : 120/80)](captures/13-infirmier-constantes-rempli.jpg)

*Constantes saisies (la tension s'affiche automatiquement : 120/80)*

3. Enregistrez (**Ctrl+S**) puis cliquez sur **Valider** et confirmez par **Oui**.

![Constantes enregistrées (brouillon)](captures/14-infirmier-constantes-enregistre.jpg)

*Constantes enregistrées (brouillon)*

![Constantes validées](captures/15-infirmier-constantes-validees.jpg)

*Constantes validées*

## 4. Médecin : consulter et prescrire

Rôle : **Médecin**. Le médecin dispose de listes prédéfinies de médicaments (liste officielle AMMPS) et d'analyses.

1. **Page d'accueil.** Le compteur *Patients en salle d'attente* indique les patients arrivés.

![Espace Cabinet médecin](captures/62-medecin-accueil.jpg)

*Espace Cabinet médecin*

2. Ouvrez le rendez-vous du patient arrivé. Le menu **Créer** propose *Consultation* et *Vital Signs*.

![Rendez-vous avec le bandeau « Patient arrivé »](captures/16-medecin-rdv-patient-arrive.jpg)

*Rendez-vous avec le bandeau « Patient arrivé »*

![Menu Créer → Consultation](captures/17-medecin-menu-creer-consultation.jpg)

*Menu Créer → Consultation*

3. Choisissez **Consultation** : le patient, le praticien et le rendez-vous sont repris automatiquement. Saisissez les symptômes et le diagnostic.

![Nouvelle consultation](captures/18-medecin-consultation-nouvelle.jpg)

*Nouvelle consultation*

4. **Prescrire un médicament.** Dans *Medications*, cliquez sur *Ajouter une ligne*. La liste des médicaments s'affiche ; tapez le début du nom pour filtrer, puis choisissez la **posologie** et la **durée** dans les listes. La forme (comprimé…) se remplit seule.

![Liste des médicaments](captures/20-medecin-liste-medicaments.jpg)

*Liste des médicaments*

![Recherche : PARACETAMOL 500](captures/21-medecin-recherche-medicament.jpg)

*Recherche : PARACETAMOL 500*

![Posologie](captures/22-medecin-posologie.jpg)

*Posologie*

![Durée](captures/23-medecin-duree.jpg)

*Durée*

5. **Prescrire une analyse.** Dans *Investigations*, cliquez sur *Ajouter une ligne* et choisissez l'analyse dans la liste.

![Liste des analyses](captures/19-medecin-liste-analyses.jpg)

*Liste des analyses*

![Médicament et analyse prescrits](captures/24-medecin-ordonnance-remplie.jpg)

*Médicament et analyse prescrits*

6. Enregistrez (**Ctrl+S**), puis **Valider** et confirmez. La consultation passe à *Terminé*, le rendez-vous est clos et **l'analyse prescrite est envoyée automatiquement au laboratoire**.

![Consultation enregistrée](captures/25-medecin-consultation-enregistree.jpg)

*Consultation enregistrée*

![Consultation validée](captures/26-medecin-consultation-validee.jpg)

*Consultation validée*

7. **Imprimer l'ordonnance** : *Imprimer* → format **Ordonnance MedMa**. Le document porte l'en-tête du médecin, les médicaments, les analyses prescrites et la zone de signature.

![Ordonnance imprimée](captures/27-medecin-ordonnance-imprimee.jpg)

*Ordonnance imprimée*

## 5. Laboratoire : prélever et saisir le résultat

Rôle : **Laboratoire**.

1. **Page d'accueil.** *Prélèvements à faire* compte les analyses dont l'échantillon n'est pas encore prélevé ; *Résultats en attente* compte celles dont l'échantillon est prélevé ; *Analyses à valider* compte les brouillons.

![Espace Laboratoire](captures/28-labo-accueil.jpg)

*Espace Laboratoire*

2. Cliquez sur *Prélèvements à faire* : la liste des analyses à prélever s'affiche. Ouvrez celle du patient.

![Analyses à prélever](captures/29-labo-liste-prelevements.jpg)

*Analyses à prélever*

![Analyse « Échantillon à prélever »](captures/30-labo-analyse-a-prelever.jpg)

*Analyse « Échantillon à prélever »*

3. Après le prélèvement, cliquez sur **Prélèvement effectué** et confirmez. L'état devient *Prélevé - en attente du résultat* ; l'heure et le nom de la personne sont enregistrés.

![Confirmation](captures/31-labo-confirmer-prelevement.jpg)

*Confirmation*

![Prélèvement enregistré](captures/32-labo-prelevement-enregistre.jpg)

*Prélèvement enregistré*

4. Quand le résultat est disponible, saisissez la valeur dans la colonne **Résultat** du tableau, enregistrez (**Ctrl+S**), puis cliquez sur **Valider**. Le statut passe à *Terminé* ; le résultat est visible du patient sur son portail.

![Saisie du résultat](captures/33-labo-saisie-resultat.jpg)

*Saisie du résultat*

![Analyse validée](captures/34-labo-analyse-validee.jpg)

*Analyse validée*

## 6. Réception : facturer et encaisser

Rôle : **Réception** (ou Comptabilité). La facture est **partagée** : une part pour l'organisme (CNSS, CNOPS…) et une part pour le patient. Les actes médicaux sont **exonérés de TVA** par défaut.

1. **Enregistrer la couverture du patient** (une seule fois) : *Couverture patient* → *Nouveau*. Choisissez le patient, l'organisme et saisissez le numéro d'affiliation ; le taux de prise en charge (70 % pour la CNSS) est repris automatiquement.

![Nouvelle couverture](captures/35-reception-couverture-nouvelle.jpg)

*Nouvelle couverture*

![Couverture saisie](captures/36-reception-couverture-remplie.jpg)

*Couverture saisie*

![Couverture enregistrée](captures/37-reception-couverture-enregistree.jpg)

*Couverture enregistrée*

2. **Créer la facture** : *Nouvelle facture*, puis choisissez le **patient**. Le client se remplit seul.

![Nouvelle facture](captures/38-reception-facture-nouvelle.jpg)

*Nouvelle facture*

![Patient choisi](captures/39-reception-facture-patient.jpg)

*Patient choisi*

3. Dans *Prise en charge*, choisissez la **couverture du patient** : la liste ne propose que les couvertures de ce patient.

![Choix de la couverture (filtrée sur le patient)](captures/40-reception-facture-choix-couverture.jpg)

*Choix de la couverture (filtrée sur le patient)*

4. Cliquez sur **Ajouter la consultation**, choisissez le praticien : l'article de consultation et son tarif sont ajoutés automatiquement.

![Choix du praticien](captures/41-reception-facture-ajouter-consultation.jpg)

*Choix du praticien*

![Praticien sélectionné](captures/42-reception-facture-consultation-praticien.jpg)

*Praticien sélectionné*

![Consultation ajoutée (200,00 MAD) et facture enregistrée](captures/43-reception-facture-consultation-ajoutee.jpg)

*Consultation ajoutée (200,00 MAD) et facture enregistrée*

5. Les parts sont calculées. Ici, total 200,00 MAD, **part CNSS 140,00 MAD** et **part patient 60,00 MAD**. Cliquez sur **Valider** et confirmez : la facture est *Impayée*.

![Part organisme / part patient](captures/44-reception-facture-parts-organisme-patient.jpg)

*Part organisme / part patient*

![Facture validée (Impayé)](captures/45-reception-facture-validee.jpg)

*Facture validée (Impayé)*

6. **Encaisser la part du patient** : menu **Créer → Paiement**.

![Menu Créer → Paiement](captures/46-reception-facture-menu-creer.jpg)

*Menu Créer → Paiement*

![Écriture de paiement (montant total par défaut)](captures/47-reception-paiement-nouveau.jpg)

*Écriture de paiement (montant total par défaut)*

7. Choisissez le moyen de paiement (*Espèces*) et remplacez le montant par **la part du patient (60,00)**. Enregistrez puis validez. La part de l'organisme reste due.

![Paiement de la part patient](captures/48-reception-paiement-part-patient.jpg)

*Paiement de la part patient*

![Paiement validé](captures/49-reception-paiement-valide.jpg)

*Paiement validé*

8. **Imprimer la facture** : *Imprimer* → **Facture MedMa**. Elle indique le patient, la CIN, l'organisme, la part de l'organisme, la part à payer par le patient, le déjà réglé et le reste dû.

![Facture imprimée](captures/50-reception-facture-imprimee.jpg)

*Facture imprimée*

## 7. Comptabilité : se faire rembourser par l'organisme

Rôle : **Comptabilité**. Un dossier de remboursement regroupe les factures d'un organisme pour une période.

1. Ouvrez *Dossier Remboursement* → *Nouveau*. Choisissez l'**organisme**, la période (*Du* / *Au*), puis cliquez sur **Charger les factures**.

![Nouveau dossier : choix de l'organisme](captures/51-compta-dossier-nouveau.jpg)

*Nouveau dossier : choix de l'organisme*

![Organisme et période saisis](captures/52-compta-dossier-organisme-periode.jpg)

*Organisme et période saisis*

![Factures chargées](captures/53-compta-dossier-factures-chargees.jpg)

*Factures chargées*

2. Enregistrez : la part de l'organisme est calculée (140,00 MAD). Puis **Actions → Marquer comme envoyé** : le statut devient *Envoyé*.

![Dossier enregistré (Brouillon)](captures/54-compta-dossier-enregistre.jpg)

*Dossier enregistré (Brouillon)*

![Menu Actions](captures/55-compta-dossier-menu-actions.jpg)

*Menu Actions*

![Dossier envoyé](captures/56-compta-dossier-envoye.jpg)

*Dossier envoyé*

3. À réception du virement : **Actions → Enregistrer un paiement**. Saisissez le montant reçu, la date et la **référence du virement**. Le paiement est réparti sur les factures, de la plus ancienne à la plus récente ; le statut passe à *Payé partiellement* puis *Payé*.

![Paiement de l'organisme](captures/57-compta-dossier-paiement-organisme.jpg)

*Paiement de l'organisme*

![Dossier payé](captures/58-compta-dossier-paye.jpg)

*Dossier payé*

4. **Imprimer le bordereau** à joindre au dossier envoyé à l'organisme : *Imprimer* → **Bordereau MedMa**.

![Bordereau de remboursement](captures/59-compta-bordereau-imprime.jpg)

*Bordereau de remboursement*

5. **Suivre les créances.** Le *Tableau de bord* donne le chiffre d'affaires, les créances ouvertes et la part des organismes. Le rapport *Créances par organisme* indique ce qui reste à recouvrer.

![Tableau de bord](captures/60-compta-tableau-de-bord.jpg)

*Tableau de bord*

![Créances par organisme](captures/61-compta-creances-par-organisme.jpg)

*Créances par organisme*

## 8. Pharmacie

Rôle : **Pharmacie**. Suivi des médicaments et du stock.

1. La page d'accueil signale les médicaments en **stock bas**. *Niveaux de stock* liste les quantités par médicament.

![Espace Pharmacie](captures/63-pharmacie-accueil.jpg)

*Espace Pharmacie*

![Médicaments en stock bas](captures/64-pharmacie-niveaux-stock.jpg)

*Médicaments en stock bas*

## 9. Direction

Rôle : **Direction**. Vue d'ensemble de l'établissement.

1. Le *Tableau de bord* réunit chiffre d'affaires, créances, rendez-vous par praticien, part des organismes. La direction a aussi accès aux espaces Réception, Laboratoire, Soins infirmiers, Pharmacie et Comptabilité.

![Tableau de bord de la direction](captures/65-direction-tableau-de-bord.jpg)

*Tableau de bord de la direction*

## 10. Patient : le portail

Rôle : **Patient**. Le patient consulte ses propres informations, en lecture seule, sur le portail. Il n'a pas accès à l'espace de travail du personnel.

1. Après connexion, la page **Mon Compte** donne accès à *Mes informations*, *Mes analyses*, *Mes ordonnances* et *Mes rendez-vous*.

![Mon Compte](captures/66-patient-mon-compte.jpg)

*Mon Compte*

![Mes rendez-vous](captures/67-patient-mes-rendez-vous.jpg)

*Mes rendez-vous*

![Mes analyses](captures/68-patient-mes-analyses.jpg)

*Mes analyses*

![Mes ordonnances](captures/69-patient-mes-ordonnances.jpg)

*Mes ordonnances*

## Limites actuelles

- La prise de rendez-vous en ligne n'est pas disponible : elle se fait à la réception.
- Le rappel de rendez-vous par WhatsApp est un lien à envoyer manuellement (bouton *Actions → Rappel WhatsApp* sur le rendez-vous).
- Les tarifs, taux de prise en charge et la liste des analyses sont des **valeurs d'exemple** à remplacer par ceux de l'établissement avant usage réel.
- La liste des médicaments provient de la liste officielle AMMPS (prix au jour de l'import).
- Les actes médicaux sont facturés **sans TVA** par défaut (modèle « Actes médicaux (exonéré de TVA) ») : à faire valider par le comptable de l'établissement ; les modèles TVA 20 % et 10 % restent disponibles.
- Certains libellés de l'interface restent en anglais (Check Availability, Book, Checked In, Medications…) : ils proviennent du module santé d'origine.
