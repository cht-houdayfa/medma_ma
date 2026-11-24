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
