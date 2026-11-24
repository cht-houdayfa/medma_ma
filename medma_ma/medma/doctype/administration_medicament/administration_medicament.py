import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class AdministrationMedicament(Document):
    def validate(self):
        self.heure_prevue = self.heure_prevue or now_datetime()
        if self.statut in ("Refusé par le patient", "Reporté") and not self.motif:
            frappe.throw(_("Indiquez le motif du refus ou du report."))
        if self.statut == "Donné":
            from medma_ma.allergies import conflit_allergie

            conflit = conflit_allergie(self.patient, self.medication, None)
            if conflit:
                frappe.throw(_("Le patient est allergique à « {0} » : ne pas administrer {1}.").format(conflit, self.medication),
                             title=_("Allergie médicamenteuse"))
            self.heure_administration = self.heure_administration or now_datetime()
            self.infirmier = self.infirmier or frappe.session.user
        else:
            self.heure_administration = None
            self.infirmier = None
