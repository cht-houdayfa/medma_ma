"""Surcharges minimales du comportement Healthcare."""

from healthcare.healthcare.doctype.patient_encounter.patient_encounter import PatientEncounter


class PatientEncounterMedMa(PatientEncounter):
    def validate_medications(self):
        """Healthcare exige le code article (marque) sur chaque ligne. Au Maroc on prescrit souvent par DCI et le
        pharmacien choisit la marque : le médicament suffit, le code article reste facultatif."""
        for ligne in self.drug_prescription or []:
            if ligne.drug_code and not ligne.medication:
                import frappe

                parent = frappe.db.get_value("Medication Linked Item", {"item": ligne.drug_code}, "parent")
                if parent:
                    ligne.medication = parent
