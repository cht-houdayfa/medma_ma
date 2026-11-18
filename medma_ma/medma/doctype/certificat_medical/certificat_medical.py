import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, getdate


class CertificatMedical(Document):
    def validate(self):
        a_periode = self.type_certificat in ("Arrêt de travail", "Dispense sportive")
        if not a_periode:
            self.debut = self.fin = None
            self.nombre_jours = 0
            return
        if not (self.debut and self.fin):
            frappe.throw(_("Renseignez les dates de début et de fin."))
        if getdate(self.fin) < getdate(self.debut):
            frappe.throw(_("La date de fin précède la date de début."))
        self.nombre_jours = date_diff(self.fin, self.debut) + 1
