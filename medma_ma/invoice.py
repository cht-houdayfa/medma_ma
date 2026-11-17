import frappe
from frappe import _
from frappe.utils import flt, getdate


def calculer_prise_en_charge(doc, method=None):
    """Partage la facture entre part organisme et part patient selon la couverture choisie."""
    precision = doc.precision("grand_total") or 2
    base = flt(doc.rounded_total or doc.grand_total)

    if not doc.get("couverture_patient"):
        doc.part_organisme = 0
        doc.part_patient = base
        return

    cov = frappe.db.get_value(
        "Couverture Patient",
        doc.couverture_patient,
        ["patient", "organisme", "taux_prise_en_charge", "valide_du", "valide_au", "actif"],
        as_dict=True,
    )
    if not cov:
        frappe.throw(_("Couverture introuvable : {0}").format(doc.couverture_patient))
    if not cov.actif:
        frappe.throw(_("La couverture {0} est inactive.").format(doc.couverture_patient))
    if doc.get("patient") and doc.patient != cov.patient:
        frappe.throw(_("La couverture {0} n'appartient pas au patient {1}.").format(doc.couverture_patient, doc.patient))
    jour = getdate(doc.posting_date)
    if (cov.valide_du and jour < getdate(cov.valide_du)) or (cov.valide_au and jour > getdate(cov.valide_au)):
        frappe.throw(_("La couverture {0} n'est pas valide à la date de facturation.").format(doc.couverture_patient))

    doc.organisme_payeur = cov.organisme
    doc.taux_prise_en_charge = cov.taux_prise_en_charge
    doc.part_organisme = flt(base * flt(cov.taux_prise_en_charge) / 100, precision)
    doc.part_patient = flt(base - doc.part_organisme, precision)
