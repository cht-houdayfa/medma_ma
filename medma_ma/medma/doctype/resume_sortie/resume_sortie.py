import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class ResumeSortie(Document):
    def validate(self):
        self.date_sortie = self.date_sortie or now_datetime()
        # préremplissage depuis le passage aux urgences : le médecin n'a rien à ressaisir
        if self.passage_urgences:
            p = frappe.db.get_value(
                "Passage Urgences", self.passage_urgences,
                ["patient", "motif", "diagnostic", "traitement", "orientation", "dossier_hospitalisation"], as_dict=True)
            if p:
                if p.patient != self.patient:
                    frappe.throw(frappe._("Ce passage aux urgences concerne un autre patient."))
                self.motif = self.motif or p.motif
                self.diagnostic = self.diagnostic or p.diagnostic
                self.traitement_sortie = self.traitement_sortie or p.traitement
                self.orientation = self.orientation or p.orientation
                self.inpatient_record = self.inpatient_record or p.dossier_hospitalisation
