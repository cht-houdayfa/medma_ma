import frappe
from frappe import _
from frappe.model.document import Document


class OrganismePayeur(Document):
    def validate(self):
        if not 0 <= (self.taux_defaut or 0) <= 100:
            frappe.throw(_("Le taux par défaut doit être compris entre 0 et 100."))
