"""Allergies connues du patient et alerte à la prescription."""

import frappe
from frappe import _


def allergies_patient(patient):
    return frappe.get_all(
        "Allergie Patient", filters={"parent": patient, "parenttype": "Patient"},
        fields=["categorie", "substance", "gravite", "reaction"], order_by="idx")


@frappe.whitelist()
def resume(patient):
    """Texte d'alerte affiché en tête des formulaires (patient, consultation, urgences)."""
    if not patient or not frappe.has_permission("Patient", "read", patient):
        return ""
    return " ; ".join(
        f"{a.substance} ({a.gravite})" if a.gravite else a.substance for a in allergies_patient(patient))


def _noms_du_medicament(ligne):
    noms = {(ligne.get("drug_name") or ""), (ligne.get("medication") or "")}
    if ligne.get("medication") and frappe.db.exists("Medication", ligne.medication):
        meta = frappe.get_meta("Medication")
        champs = [c for c in ("generic_name", "medication_class") if meta.has_field(c)]
        if champs:
            valeurs = frappe.db.get_value("Medication", ligne.medication, champs, as_dict=True)
            noms.update((valeurs.get(c) or "") for c in champs)
    return [n.strip().lower() for n in noms if n and n.strip()]


def verifier_prescription(doc, methode=None):
    """Bloque l'ordonnance qui contient une substance à laquelle le patient est allergique, sauf confirmation explicite."""
    allergies = [a for a in allergies_patient(doc.patient) if a.categorie == "Médicament"]
    if not allergies:
        return
    conflits = []
    for ligne in doc.get("drug_prescription") or []:
        noms = _noms_du_medicament(ligne)
        for a in allergies:
            sub = a.substance.strip().lower()
            if sub and any(sub in n or n in sub for n in noms):
                conflits.append(f"{ligne.get('drug_name') or ligne.get('medication')} ↔ {a.substance}")
    if not conflits:
        return
    texte = "<br>".join(conflits)
    if doc.get("allergie_confirmee"):
        frappe.msgprint(_("Prescription malgré une allergie signalée :") + "<br>" + texte, indicator="orange", title=_("Allergie"))
        return
    frappe.throw(
        _("Allergie connue : le patient est allergique à une substance prescrite.") + "<br>" + texte + "<br><br>"
        + _("Retirez le médicament, ou cochez « Prescrire malgré l'allergie » après avoir pesé le risque."),
        title=_("Allergie médicamenteuse"))


def conflit_allergie(patient, medication, drug_name):
    """Renvoie la substance en conflit (ou None) pour un médicament donné."""
    noms = _noms_du_medicament(frappe._dict(medication=medication, drug_name=drug_name))
    for a in allergies_patient(patient):
        if a.categorie != "Médicament":
            continue
        sub = (a.substance or "").strip().lower()
        if sub and any(sub in n or n in sub for n in noms):
            return a.substance
    return None


def interactions_de(lignes):
    """Interactions connues entre les médicaments d'une même ordonnance : liste de (gravité, libellé, conseil)."""
    jeux = [_noms_du_medicament(ligne) for ligne in lignes]
    trouvees = []
    for i in range(len(jeux)):
        for j in range(i + 1, len(jeux)):
            for it in frappe.get_all("Interaction Medicamenteuse", fields=["substance_a", "substance_b", "gravite", "conseil"]):
                a, b = it.substance_a.lower(), it.substance_b.lower()
                directe = any(a in n or n in a for n in jeux[i]) and any(b in n or n in b for n in jeux[j])
                inverse = any(b in n or n in b for n in jeux[i]) and any(a in n or n in a for n in jeux[j])
                if directe or inverse:
                    trouvees.append((it.gravite, f"{it.substance_a} + {it.substance_b}", it.conseil or ""))
    return trouvees


def verifier_interactions(doc, methode=None):
    trouvees = interactions_de(doc.get("drug_prescription") or [])
    if not trouvees:
        return
    texte = "<br>".join(f"<b>{g}</b> : {lib}" + (f" — {c}" if c else "") for g, lib, c in trouvees)
    if any(g == "Majeure" for g, _l, _c in trouvees) and not doc.get("interaction_confirmee"):
        frappe.throw(
            _("Interaction médicamenteuse majeure dans cette ordonnance :") + "<br>" + texte + "<br><br>"
            + _("Modifiez l'ordonnance, ou cochez « Prescrire malgré l'interaction » après avoir pesé le risque."),
            title=_("Interaction médicamenteuse"))
    frappe.msgprint(_("Interaction médicamenteuse à vérifier :") + "<br>" + texte, indicator="orange", title=_("Interaction"))
