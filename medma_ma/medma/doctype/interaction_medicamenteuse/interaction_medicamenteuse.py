from frappe.model.document import Document


class InteractionMedicamenteuse(Document):
    def validate(self):
        self.substance_a = (self.substance_a or "").strip()
        self.substance_b = (self.substance_b or "").strip()
        self.libelle = f"{self.substance_a} + {self.substance_b}"
