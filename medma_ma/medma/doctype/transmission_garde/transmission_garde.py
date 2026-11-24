import frappe
from frappe.model.document import Document


class TransmissionGarde(Document):
    def validate(self):
        self.infirmier_sortant = self.infirmier_sortant or frappe.session.user
        self.libelle = f"{self.service} — {self.equipe} du {frappe.utils.formatdate(self.date_garde)}"
