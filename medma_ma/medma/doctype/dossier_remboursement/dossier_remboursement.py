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
		self.total_paye = sum(flt(r.montant_paye) for r in self.factures)
		if flt(self.total_paye) > flt(self.total_reclame) + 0.005:
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

	@frappe.whitelist()
	def marquer_envoye(self):
		self.check_permission("write")
		if self.statut != "Brouillon":
			frappe.throw(_("Seul un dossier en brouillon peut être marqué comme envoyé."))
		if not self.factures:
			frappe.throw(_("Le dossier ne contient aucune facture."))
		self.statut = "Envoyé"
		self.save()
		return self.statut

	@frappe.whitelist()
	def enregistrer_paiement(self, montant, date_paiement, reference):
		"""Enregistre un virement reçu de l'organisme et le répartit sur les factures, de la plus ancienne à la plus récente."""
		self.check_permission("write")
		if self.statut not in ("Envoyé", "Payé partiellement"):
			frappe.throw(_("Le dossier doit être envoyé avant d'enregistrer un paiement."))
		montant = flt(montant)
		if montant <= 0:
			frappe.throw(_("Le montant doit être positif."))
		if not (reference or "").strip():
			frappe.throw(_("La référence du virement est obligatoire."))
		reste = flt(self.total_reclame) - flt(self.total_paye)
		if montant > reste + 0.005:
			frappe.throw(_("Le montant ({0}) dépasse le reste à recouvrer ({1}).").format(montant, reste))

		restant = montant
		for row in self.factures:
			if restant <= 0:
				break
			a_payer = min(flt(row.part_organisme) - flt(row.montant_paye), restant)
			if a_payer <= 0.005:
				continue
			_creer_paiement(row.sales_invoice, a_payer, date_paiement, reference)
			row.montant_paye = flt(row.montant_paye) + a_payer
			restant -= a_payer

		self.total_paye = sum(flt(r.montant_paye) for r in self.factures)
		self.statut = "Payé" if flt(self.total_paye) >= flt(self.total_reclame) - 0.005 else "Payé partiellement"
		self.save()
		return {"statut": self.statut, "total_paye": self.total_paye}


def _creer_paiement(sales_invoice, montant, date_paiement, reference):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	pe = get_payment_entry("Sales Invoice", sales_invoice, party_amount=flt(montant))
	pe.posting_date = date_paiement
	pe.mode_of_payment = "Virement"
	compte = frappe.db.get_value("Account", {"company": pe.company, "account_type": "Bank", "is_group": 0}, "name")
	if compte:
		pe.paid_to = compte
	pe.reference_no = reference
	pe.reference_date = date_paiement
	pe.insert(ignore_permissions=True)
	pe.submit()
	return pe.name
