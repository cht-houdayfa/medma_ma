#!/usr/bin/env python3
"""Génère le guide utilisateur MedMa (Markdown + HTML autonome avec captures intégrées) à partir de captures/.

  python3 build_guide.py        → GUIDE_UTILISATEUR.md et GUIDE_UTILISATEUR.html
"""
import base64
import html
import os

ICI = os.path.dirname(os.path.abspath(__file__))
CAP = os.path.join(ICI, "captures")

# (titre de section, introduction, [(étape texte, [(fichier, légende), ...]), ...])
SECTIONS = [
    ("1. Se connecter", "Chaque personne de l'établissement a son compte. Selon son rôle, elle ne voit que les écrans qui la concernent.",
     [("Ouvrez l'adresse de MedMa dans le navigateur, saisissez votre identifiant (adresse e-mail) et votre mot de passe, puis cliquez sur **Login**.",
       [("00-connexion.jpg", "Écran de connexion")])]),

    ("2. Réception : accueillir le patient", "Rôle : **Réception**. La réception enregistre le patient, prend le rendez-vous et signale l'arrivée.",
     [("**Page d'accueil.** Les compteurs montrent la salle d'attente, les rendez-vous du jour, les rendez-vous à venir et les factures non soldées. Les *Actions rapides* ouvrent directement un nouveau patient, un nouveau rendez-vous ou une facture.",
       [("01-reception-accueil.jpg", "Page d'accueil de la réception")]),
      ("**Créer le patient.** Cliquez sur *Nouveau patient*. Renseignez au minimum le prénom, le nom, le sexe, la **CIN**, le mobile et la date de naissance. Décochez *Inviter en tant qu'Utilisateur* sauf si le patient doit avoir un accès au portail.",
       [("02-reception-nouveau-patient-vide.jpg", "Formulaire patient vide"),
        ("03-reception-patient-rempli.jpg", "Formulaire rempli")]),
      ("Enregistrez avec **Ctrl+S** (ou le bouton *Sauvegarder*). La fiche du patient est créée.",
       [("04-reception-patient-enregistre.jpg", "Patient enregistré")]),
      ("**Prendre le rendez-vous.** Cliquez sur *Nouveau rendez-vous*, choisissez le patient, le type de rendez-vous et le praticien.",
       [("05-reception-rdv-choix-patient.jpg", "Choix du patient")]),
      ("Cliquez sur **Vérifier la disponibilité**, indiquez la date : les créneaux libres du praticien s'affichent (un créneau grisé est déjà pris).",
       [("06-reception-rdv-disponibilites-vide.jpg", "Fenêtre de disponibilités"),
        ("07-reception-rdv-creneaux.jpg", "Créneaux disponibles")]),
      ("Choisissez le créneau puis cliquez sur **Réserver**. Le rendez-vous est créé avec le statut *Prévu*.",
       [("08-reception-rdv-enregistre.jpg", "Rendez-vous enregistré")]),
      ("**Le jour du rendez-vous**, à l'arrivée du patient, ouvrez son rendez-vous et cliquez sur **Patient arrivé**. Le statut passe à *Patient arrivé* et le patient apparaît dans la salle d'attente du médecin et de l'infirmier.",
       [("09-reception-rdv-bouton-patient-arrive.jpg", "Bouton « Patient arrivé »"),
        ("10-reception-patient-arrive-enregistre.jpg", "Arrivée enregistrée"),
        ("11-reception-accueil-patient-en-attente.jpg", "Le compteur « Patients en salle d'attente » passe à 1")])]),

    ("3. Infirmier : prendre les constantes", "Rôle : **Infirmier**.",
     [("**Page d'accueil.**", [("61-infirmier-accueil.jpg", "Espace Soins infirmiers")]),
      ("Ouvrez *Constantes* puis *Nouveau* : choisissez le patient, saisissez température, pouls, fréquence respiratoire, tension (systolique / diastolique), taille et poids.",
       [("12-infirmier-constantes-vide.jpg", "Nouvelles constantes"),
        ("13-infirmier-constantes-rempli.jpg", "Constantes saisies (la tension s'affiche automatiquement : 120/80)")]),
      ("Enregistrez (**Ctrl+S**) puis cliquez sur **Valider** et confirmez par **Oui**.",
       [("14-infirmier-constantes-enregistre.jpg", "Constantes enregistrées (brouillon)"),
        ("15-infirmier-constantes-validees.jpg", "Constantes validées")])]),

    ("4. Médecin : consulter et prescrire", "Rôle : **Médecin**. Le médecin dispose de listes prédéfinies de médicaments (liste officielle AMMPS) et d'analyses.",
     [("**Page d'accueil.** Le compteur *Patients en salle d'attente* indique les patients arrivés.",
       [("62-medecin-accueil.jpg", "Espace Cabinet médecin")]),
      ("Ouvrez le rendez-vous du patient arrivé. Le menu **Créer** propose *Consultation* et *Signes vitaux*.",
       [("16-medecin-rdv-patient-arrive.jpg", "Rendez-vous avec le bandeau « Patient arrivé »"),
        ("17-medecin-menu-creer-consultation.jpg", "Menu Créer → Consultation")]),
      ("Choisissez **Consultation** : le patient, le praticien et le rendez-vous sont repris automatiquement. Saisissez les symptômes et le diagnostic.",
       [("18-medecin-consultation-nouvelle.jpg", "Nouvelle consultation")]),
      ("**Prescrire un médicament.** Dans *Médicaments*, cliquez sur *Ajouter une ligne*. La liste des médicaments s'affiche ; tapez le début du nom pour filtrer, puis choisissez la **posologie** et la **durée** dans les listes. La forme (comprimé…) se remplit seule.",
       [("20-medecin-liste-medicaments.jpg", "Liste des médicaments"),
        ("21-medecin-recherche-medicament.jpg", "Recherche : PARACETAMOL 500"),
        ("22-medecin-posologie.jpg", "Posologie"),
        ("23-medecin-duree.jpg", "Durée")]),
      ("**Prescrire une analyse.** Dans *Examens complémentaires*, cliquez sur *Ajouter une ligne* et choisissez l'analyse dans la liste.",
       [("19-medecin-liste-analyses.jpg", "Liste des analyses"),
        ("24-medecin-ordonnance-remplie.jpg", "Médicament et analyse prescrits")]),
      ("Enregistrez (**Ctrl+S**), puis **Valider** et confirmez. La consultation passe à *Terminé*, le rendez-vous est clos et **l'analyse prescrite est envoyée automatiquement au laboratoire**.",
       [("25-medecin-consultation-enregistree.jpg", "Consultation enregistrée"),
        ("26-medecin-consultation-validee.jpg", "Consultation validée")]),
      ("**Imprimer l'ordonnance** : *Imprimer* → format **Ordonnance MedMa**. Le document porte l'en-tête du médecin, les médicaments, les analyses prescrites et la zone de signature.",
       [("27-medecin-ordonnance-imprimee.jpg", "Ordonnance imprimée")])]),

    ("5. Laboratoire : prélever et saisir le résultat", "Rôle : **Laboratoire**.",
     [("**Page d'accueil.** *Prélèvements à faire* compte les analyses dont l'échantillon n'est pas encore prélevé ; *Résultats en attente* compte celles dont l'échantillon est prélevé ; *Analyses à valider* compte les brouillons.",
       [("28-labo-accueil.jpg", "Espace Laboratoire")]),
      ("Cliquez sur *Prélèvements à faire* : la liste des analyses à prélever s'affiche. Ouvrez celle du patient.",
       [("29-labo-liste-prelevements.jpg", "Analyses à prélever"),
        ("30-labo-analyse-a-prelever.jpg", "Analyse « Échantillon à prélever »")]),
      ("Après le prélèvement, cliquez sur **Prélèvement effectué** et confirmez. L'état devient *Prélevé - en attente du résultat* ; l'heure et le nom de la personne sont enregistrés.",
       [("31-labo-confirmer-prelevement.jpg", "Confirmation"),
        ("32-labo-prelevement-enregistre.jpg", "Prélèvement enregistré")]),
      ("Quand le résultat est disponible, saisissez la valeur dans la colonne **Résultat** du tableau, enregistrez (**Ctrl+S**), puis cliquez sur **Valider**. Le statut passe à *Terminé* ; le résultat est visible du patient sur son portail.",
       [("33-labo-saisie-resultat.jpg", "Saisie du résultat"),
        ("34-labo-analyse-validee.jpg", "Analyse validée")])]),

    ("6. Réception : facturer et encaisser", "Rôle : **Réception** (ou Comptabilité). La facture est **partagée** : une part pour l'organisme (CNSS, CNOPS…) et une part pour le patient. Les actes médicaux sont **exonérés de TVA** par défaut.",
     [("**Enregistrer la couverture du patient** (une seule fois) : *Couverture patient* → *Nouveau*. Choisissez le patient, l'organisme et saisissez le numéro d'affiliation ; le taux de prise en charge (70 % pour la CNSS) est repris automatiquement.",
       [("35-reception-couverture-nouvelle.jpg", "Nouvelle couverture"),
        ("36-reception-couverture-remplie.jpg", "Couverture saisie"),
        ("37-reception-couverture-enregistree.jpg", "Couverture enregistrée")]),
      ("**Créer la facture** : *Nouvelle facture*, puis choisissez le **patient**. Le client se remplit seul.",
       [("38-reception-facture-nouvelle.jpg", "Nouvelle facture"),
        ("39-reception-facture-patient.jpg", "Patient choisi")]),
      ("Dans *Prise en charge*, choisissez la **couverture du patient** : la liste ne propose que les couvertures de ce patient.",
       [("40-reception-facture-choix-couverture.jpg", "Choix de la couverture (filtrée sur le patient)")]),
      ("Cliquez sur **Ajouter la consultation**, choisissez le praticien : l'article de consultation et son tarif sont ajoutés automatiquement.",
       [("41-reception-facture-ajouter-consultation.jpg", "Choix du praticien"),
        ("42-reception-facture-consultation-praticien.jpg", "Praticien sélectionné"),
        ("43-reception-facture-consultation-ajoutee.jpg", "Consultation ajoutée (200,00 MAD) et facture enregistrée")]),
      ("Les parts sont calculées. Ici, total 200,00 MAD, **part CNSS 140,00 MAD** et **part patient 60,00 MAD**. Cliquez sur **Valider** et confirmez : la facture est *Impayé*.",
       [("44-reception-facture-parts-organisme-patient.jpg", "Part organisme / part patient"),
        ("45-reception-facture-validee.jpg", "Facture validée (Impayé)")]),
      ("**Encaisser la part du patient** : menu **Créer → Paiement**.",
       [("46-reception-facture-menu-creer.jpg", "Menu Créer → Paiement"),
        ("47-reception-paiement-nouveau.jpg", "Écriture de paiement (montant total par défaut)")]),
      ("Choisissez le moyen de paiement (*Espèces*) et remplacez le montant par **la part du patient (60,00)**. Enregistrez puis validez. La part de l'organisme reste due.",
       [("48-reception-paiement-part-patient.jpg", "Paiement de la part patient"),
        ("49-reception-paiement-valide.jpg", "Paiement validé")]),
      ("**Imprimer la facture** : *Imprimer* → **Facture MedMa**. Elle indique le patient, la CIN, l'organisme, la part de l'organisme, la part à payer par le patient, le déjà réglé et le reste dû.",
       [("50-reception-facture-imprimee.jpg", "Facture imprimée")])]),

    ("7. Comptabilité : se faire rembourser par l'organisme", "Rôle : **Comptabilité**. Un dossier de remboursement regroupe les factures d'un organisme pour une période.",
     [("Ouvrez *Dossier de remboursement* → *Nouveau*. Choisissez l'**organisme**, la période (*Du* / *Au*), puis cliquez sur **Charger les factures**.",
       [("51-compta-dossier-nouveau.jpg", "Nouveau dossier : choix de l'organisme"),
        ("52-compta-dossier-organisme-periode.jpg", "Organisme et période saisis"),
        ("53-compta-dossier-factures-chargees.jpg", "Factures chargées")]),
      ("Enregistrez : la part de l'organisme est calculée (140,00 MAD). Puis **Actions → Marquer comme envoyé** : le statut devient *Envoyé*.",
       [("54-compta-dossier-enregistre.jpg", "Dossier enregistré (Brouillon)"),
        ("55-compta-dossier-menu-actions.jpg", "Menu Actions"),
        ("56-compta-dossier-envoye.jpg", "Dossier envoyé")]),
      ("À réception du virement : **Actions → Enregistrer un paiement**. Saisissez le montant reçu, la date et la **référence du virement**. Le paiement est réparti sur les factures, de la plus ancienne à la plus récente ; le statut passe à *Payé partiellement* puis *Payé*.",
       [("57-compta-dossier-paiement-organisme.jpg", "Paiement de l'organisme"),
        ("58-compta-dossier-paye.jpg", "Dossier payé")]),
      ("**Imprimer le bordereau** à joindre au dossier envoyé à l'organisme : *Imprimer* → **Bordereau MedMa**.",
       [("59-compta-bordereau-imprime.jpg", "Bordereau de remboursement")]),
      ("**Suivre les créances.** Le *Tableau de bord* donne le chiffre d'affaires, les créances ouvertes et la part des organismes. Le rapport *Créances par organisme* indique ce qui reste à recouvrer.",
       [("60-compta-tableau-de-bord.jpg", "Tableau de bord"),
        ("61-compta-creances-par-organisme.jpg", "Créances par organisme")])]),

    ("8. Pharmacie", "Rôle : **Pharmacie**. Suivi des médicaments et du stock.",
     [("La page d'accueil signale les médicaments en **stock bas**. *Niveaux de stock* liste les quantités par médicament.",
       [("63-pharmacie-accueil.jpg", "Espace Pharmacie"),
        ("64-pharmacie-niveaux-stock.jpg", "Médicaments en stock bas")])]),

    ("9. Direction", "Rôle : **Direction**. Vue d'ensemble de l'établissement.",
     [("Le *Tableau de bord* réunit chiffre d'affaires, créances, rendez-vous par praticien, part des organismes. La direction a aussi accès aux espaces Réception, Laboratoire, Soins infirmiers, Pharmacie et Comptabilité.",
       [("65-direction-tableau-de-bord.jpg", "Tableau de bord de la direction")])]),

    ("10. Patient : le portail", "Rôle : **Patient**. Le patient consulte ses propres informations, en lecture seule, sur le portail. Il n'a pas accès à l'espace de travail du personnel.",
     [("Après connexion, la page **Mon Compte** donne accès à *Mes informations*, *Mes analyses*, *Mes ordonnances* et *Mes rendez-vous*.",
       [("66-patient-mon-compte.jpg", "Mon Compte"),
        ("67-patient-mes-rendez-vous.jpg", "Mes rendez-vous"),
        ("68-patient-mes-analyses.jpg", "Mes analyses"),
        ("69-patient-mes-ordonnances.jpg", "Mes ordonnances")])]),
]

LIMITES = [
    "La prise de rendez-vous en ligne n'est pas disponible : elle se fait à la réception.",
    "Le rappel de rendez-vous par WhatsApp est un lien à envoyer manuellement (bouton *Actions → Rappel WhatsApp* sur le rendez-vous).",
    "Les tarifs, taux de prise en charge et la liste des analyses sont des **valeurs d'exemple** à remplacer par ceux de l'établissement avant usage réel.",
    "La liste des médicaments provient de la liste officielle AMMPS (prix au jour de l'import).",
    "Les actes médicaux sont facturés **sans TVA** par défaut (modèle « Actes médicaux (exonéré de TVA) ») : à faire valider par le comptable de l'établissement ; les modèles TVA 20 % et 10 % restent disponibles.",
    "Quelques libellés secondaires du module santé d'origine peuvent encore apparaître en anglais : ils sont traduits au fur et à mesure dans le fichier de traductions de MedMa.",
]


def md_img(nom, legende):
    return f"![{legende}](captures/{nom})\n\n*{legende}*\n"


def construire_md():
    out = ["# MedMa — Guide utilisateur", "",
           "Parcours complet d'une visite, de l'accueil du patient jusqu'au remboursement par l'organisme, "
           "avec les captures d'écran de chaque rôle. Patient fictif utilisé : *Yassine Guide-Test*.", ""]
    for titre, intro, etapes in SECTIONS:
        out += [f"## {titre}", "", intro, ""]
        for i, (texte, imgs) in enumerate(etapes, 1):
            out += [f"{i}. {texte}", ""]
            for nom, leg in imgs:
                out.append(md_img(nom, leg))
    out += ["## Limites actuelles", ""] + [f"- {l}" for l in LIMITES] + [""]
    return "\n".join(out)


def inline(texte):
    t = html.escape(texte)
    import re

    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    return t


def b64(nom):
    with open(os.path.join(CAP, nom), "rb") as f:
        return base64.b64encode(f.read()).decode()


def construire_html():
    corps = []
    toc = []
    for n, (titre, intro, etapes) in enumerate(SECTIONS):
        ancre = f"s{n}"
        toc.append(f'<li><a href="#{ancre}">{html.escape(titre)}</a></li>')
        corps.append(f'<section id="{ancre}"><h2>{html.escape(titre)}</h2><p class="intro">{inline(intro)}</p><ol>')
        for texte, imgs in etapes:
            corps.append(f"<li><p>{inline(texte)}</p>")
            for nom, leg in imgs:
                corps.append(
                    f'<figure><img src="data:image/jpeg;base64,{b64(nom)}" alt="{html.escape(leg)}">'
                    f"<figcaption>{html.escape(leg)}</figcaption></figure>"
                )
            corps.append("</li>")
        corps.append("</ol></section>")
    lim = "".join(f"<li>{inline(l)}</li>" for l in LIMITES)
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MedMa — Guide utilisateur</title>
<style>
:root{{--vert:#0f766e;--texte:#1f2937;--fond:#fff;--gris:#f3f4f6}}
@media (prefers-color-scheme:dark){{:root{{--texte:#e5e7eb;--fond:#111827;--gris:#1f2937}}}}
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--texte);background:var(--fond);margin:0;line-height:1.55}}
main{{max-width:900px;margin:0 auto;padding:24px 16px 64px}}
h1{{color:var(--vert);margin:.2em 0}} h2{{color:var(--vert);border-bottom:2px solid var(--vert);padding-bottom:.2em;margin-top:2.2em}}
.intro{{background:var(--gris);padding:10px 14px;border-radius:8px}}
figure{{margin:12px 0 22px}} img{{max-width:100%;height:auto;border:1px solid #d1d5db;border-radius:8px}}
figcaption{{font-size:.85rem;color:#6b7280;margin-top:4px}}
nav{{background:var(--gris);padding:8px 18px;border-radius:8px}}
li{{margin-bottom:10px}}
@media print{{section{{break-inside:avoid-page}} figure{{break-inside:avoid}} nav{{display:none}}}}
</style></head><body><main>
<h1>MedMa — Guide utilisateur</h1>
<p>Parcours complet d'une visite, de l'accueil du patient jusqu'au remboursement par l'organisme, avec les captures d'écran de chaque rôle. Patient fictif utilisé : <em>Yassine Guide-Test</em>.</p>
<nav><strong>Sommaire</strong><ul>{"".join(toc)}<li><a href="#limites">Limites actuelles</a></li></ul></nav>
{"".join(corps)}
<section id="limites"><h2>Limites actuelles</h2><ul>{lim}</ul></section>
</main></body></html>"""


if __name__ == "__main__":
    for nom, contenu in (("GUIDE_UTILISATEUR.md", construire_md()), ("GUIDE_UTILISATEUR.html", construire_html())):
        with open(os.path.join(ICI, nom), "w", encoding="utf-8") as f:
            f.write(contenu)
        print(nom, len(contenu) // 1024, "Ko")
