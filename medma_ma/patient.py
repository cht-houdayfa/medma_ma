import frappe
from frappe import _


def verifier_cin(doc, methode=None):
    """Le CIN identifie une personne : on le normalise (majuscules, sans espaces) et on refuse un doublon.

    Deux patients peuvent porter le même nom ; ils ne peuvent pas avoir le même CIN. Le champ reste facultatif
    (enfants, étrangers), mais s'il est renseigné il est unique."""
    cin = "".join((doc.get("cin") or "").split()).upper()
    doc.cin = cin
    if not cin:
        return
    autre = frappe.db.get_value("Patient", {"cin": cin, "name": ["!=", doc.name]}, ["name", "patient_name"], as_dict=True)
    if autre:
        frappe.throw(
            _("Le CIN {0} est déjà enregistré pour le patient {1} ({2}).").format(cin, autre.patient_name, autre.name),
            title=_("CIN déjà utilisé"),
        )
