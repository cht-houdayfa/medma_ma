import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


class DossierRemboursement(Document):
    def validate(self):
        if getdate(self.date_fin) < getdate(self.date_debut):
            frappe.throw(_("La date de fin précède la date de début."))
        seen = set()
        for row in self.factures:
            if row.sales_invoice in seen:
                frappe.throw(_("Facture en double : {0}").format(row.sales_invoice))
            seen.add(row.sales_invoice)
        self.total_reclame = sum(flt(r.part_organisme) for r in self.factures)
        if flt(self.total_paye) > flt(self.total_reclame):
            frappe.throw(_("Le total payé dépasse le total réclamé."))

    @frappe.whitelist()
    def charger_factures(self):
        """Ajoute les factures validées de l'organisme sur la période, non encore présentes dans un autre dossier."""
        self.check_permission("write")
        deja = {
            r[0]
            for r in frappe.db.sql(
                "select sales_invoice from `tabDossier Remboursement Facture` where parent != %s",
                (self.name or "",),
            )
        }
        courantes = {r.sales_invoice for r in self.factures}
        factures = frappe.get_all(
            "Sales Invoice",
            filters={
                "docstatus": 1,
                "organisme_payeur": self.organisme,
                "posting_date": ["between", [self.date_debut, self.date_fin]],
                "part_organisme": [">", 0],
            },
            fields=["name"],
            order_by="posting_date asc",
        )
        ajoutees = 0
        for fa in factures:
            if fa.name in deja or fa.name in courantes:
                continue
            self.append("factures", {"sales_invoice": fa.name})
            ajoutees += 1
        return ajoutees
