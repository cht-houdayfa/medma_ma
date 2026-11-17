import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class CouverturePatient(Document):
    def validate(self):
        if self.taux_prise_en_charge is None or self.taux_prise_en_charge == "":
            # Taux non fourni (ex. création par API) : on applique celui de l'organisme. Un 0 saisi explicitement est conservé.
            self.taux_prise_en_charge = frappe.db.get_value("Organisme Payeur", self.organisme, "taux_defaut") or 0
        if not 0 <= (self.taux_prise_en_charge or 0) <= 100:
            frappe.throw(_("Le taux de prise en charge doit être compris entre 0 et 100."))
        if self.valide_du and self.valide_au and getdate(self.valide_au) < getdate(self.valide_du):
            frappe.throw(_("La date de fin de validité précède la date de début."))
        if not (self.taux_prise_en_charge or 0):
            frappe.msgprint(
                _("Taux de prise en charge à 0 % : le patient paiera la totalité de ses factures. Renseignez le taux prévu par le contrat."),
                title=_("Vérifiez le taux"),
                indicator="orange",
                alert=True,
            )
