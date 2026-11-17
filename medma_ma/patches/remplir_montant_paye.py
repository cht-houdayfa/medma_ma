import frappe
from frappe.utils import flt


def execute():
	"""Renseigne montant_paye des dossiers existants à partir des virements déjà enregistrés sur les factures."""
	for ligne in frappe.get_all("Dossier Remboursement Facture", fields=["name", "parent", "sales_invoice", "montant_paye"]):
		if flt(ligne.montant_paye):
			continue
		paye = frappe.db.sql(
			"""select coalesce(sum(r.allocated_amount), 0) from `tabPayment Entry Reference` r
			join `tabPayment Entry` p on p.name = r.parent
			where r.reference_doctype = 'Sales Invoice' and r.reference_name = %s
			and p.docstatus = 1 and p.mode_of_payment = 'Virement'""",
			(ligne.sales_invoice,),
		)[0][0]
		if flt(paye):
			frappe.db.set_value("Dossier Remboursement Facture", ligne.name, "montant_paye", flt(paye), update_modified=False)
	for d in frappe.get_all("Dossier Remboursement", pluck="name"):
		total = frappe.db.sql("select coalesce(sum(montant_paye),0) from `tabDossier Remboursement Facture` where parent=%s", (d,))[0][0]
		frappe.db.set_value("Dossier Remboursement", d, "total_paye", flt(total), update_modified=False)
