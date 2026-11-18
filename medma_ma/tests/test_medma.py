"""Tests de la logique métier MedMa.

Chaque test s'exécute dans une transaction annulée à la fin : aucune donnée n'est conservée.
Lancer : bench --site <site> execute medma_ma.tests.run_all
"""

import unittest

import frappe
from frappe.utils import add_days, today


def _nouvel_article():
	if not frappe.db.exists("Item", "TEST-ACTE"):
		frappe.get_doc(
			{"doctype": "Item", "item_code": "TEST-ACTE", "item_name": "Acte de test", "item_group": "Services",
			 "stock_uom": "Unit", "is_stock_item": 0}
		).insert(ignore_permissions=True)
	return "TEST-ACTE"


class Base(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		# Certains hooks ERPNext/Healthcare appellent frappe.db.commit() : on le neutralise pour que rollback() annule tout.
		self._commit = frappe.db.commit
		frappe.db.commit = lambda *a, **k: None
		self.company = frappe.db.get_value("Company", {}, "name")
		self.article = _nouvel_article()
		self.organisme = frappe.get_doc(
			{"doctype": "Organisme Payeur", "organisme_name": "TEST-ORG", "type_organisme": "CNSS", "taux_defaut": 70}
		).insert(ignore_permissions=True)
		self.patient = self._patient("Testeur")

	def tearDown(self):
		frappe.db.rollback()
		frappe.db.commit = self._commit

	def _patient(self, prenom):
		return frappe.get_doc({"doctype": "Patient", "first_name": prenom, "sex": "Male"}).insert(ignore_permissions=True)

	def _couverture(self, patient=None, taux=70, **kw):
		return frappe.get_doc(
			{"doctype": "Couverture Patient", "patient": (patient or self.patient).name, "organisme": self.organisme.name,
			 "numero_affiliation": "T-1", "taux_prise_en_charge": taux, **kw}
		).insert(ignore_permissions=True)

	def _facture(self, montant, couverture=None, patient=None, date=None, soumettre=False):
		p = patient or self.patient
		si = frappe.get_doc(
			{"doctype": "Sales Invoice", "customer": p.customer, "patient": p.name, "company": self.company,
			 "posting_date": date or today(), "set_posting_time": 1, "couverture_patient": couverture.name if couverture else None,
			 "items": [{"item_code": self.article, "qty": 1, "rate": montant}]}
		).insert(ignore_permissions=True)
		if soumettre:
			si.submit()
		return si


class TestPriseEnCharge(Base):
	def test_partage_70_30(self):
		si = self._facture(1000, self._couverture())
		self.assertEqual((si.part_organisme, si.part_patient), (700, 300))
		self.assertEqual(si.organisme_payeur, self.organisme.name)

	def test_arrondi_somme_exacte(self):
		si = self._facture(333.33, self._couverture())
		# le partage porte sur le total à payer (arrondi si l'arrondi est activé)
		self.assertAlmostEqual(si.part_organisme + si.part_patient, si.rounded_total or si.grand_total, places=2)

	def test_sans_couverture_tout_au_patient(self):
		si = self._facture(250)
		self.assertEqual((si.part_organisme, si.part_patient), (0, 250))

	def test_couverture_d_un_autre_patient_refusee(self):
		cov = self._couverture()
		autre = self._patient("Autre")
		with self.assertRaises(frappe.ValidationError):
			self._facture(100, cov, patient=autre)

	def test_couverture_inactive_refusee(self):
		cov = self._couverture(actif=0)
		with self.assertRaises(frappe.ValidationError):
			self._facture(100, cov)

	def test_couverture_expiree_refusee(self):
		cov = self._couverture(valide_au=add_days(today(), -1))
		with self.assertRaises(frappe.ValidationError):
			self._facture(100, cov)

	def test_taux_hors_bornes_refuse(self):
		for taux in (-1, 101):
			with self.assertRaises(frappe.ValidationError):
				self._couverture(taux=taux)

	def test_taux_zero_explicite_conserve_meme_si_defaut_70(self):
		# régression : un 0 explicite était remplacé par le taux par défaut de l'organisme (70)
		self.assertEqual(self.organisme.taux_defaut, 70)
		self.assertEqual(self._couverture(taux=0).taux_prise_en_charge, 0)

	def test_taux_absent_prend_le_defaut_de_l_organisme(self):
		cov = frappe.get_doc(
			{"doctype": "Couverture Patient", "patient": self.patient.name, "organisme": self.organisme.name, "numero_affiliation": "T-2"}
		).insert(ignore_permissions=True)
		self.assertEqual(cov.taux_prise_en_charge, 70)

	def test_organismes_par_defaut_idempotents(self):
		from medma_ma.setup import seed_organismes

		avant = frappe.db.count("Organisme Payeur")
		seed_organismes()
		seed_organismes()
		self.assertEqual(frappe.db.count("Organisme Payeur"), avant)
		self.assertTrue(frappe.db.exists("Organisme Payeur", "CNSS"))


class TestRemboursement(Base):
	def setUp(self):
		super().setUp()
		cov = self._couverture()
		self.f1 = self._facture(1000, cov, date=add_days(today(), -3), soumettre=True)  # organisme : 700
		self.f2 = self._facture(500, cov, date=add_days(today(), -2), soumettre=True)  # organisme : 350
		self.dossier = frappe.get_doc(
			{"doctype": "Dossier Remboursement", "organisme": self.organisme.name,
			 "date_debut": add_days(today(), -10), "date_fin": today()}
		)
		self.assertEqual(self.dossier.charger_factures(), 2)
		self.dossier.insert(ignore_permissions=True)

	def test_total_reclame(self):
		self.assertEqual(self.dossier.total_reclame, 1050)

	def test_une_facture_ne_peut_pas_etre_dans_deux_dossiers(self):
		autre = frappe.get_doc(
			{"doctype": "Dossier Remboursement", "organisme": self.organisme.name,
			 "date_debut": add_days(today(), -10), "date_fin": today()}
		)
		self.assertEqual(autre.charger_factures(), 0)

	def test_paiement_refuse_avant_envoi(self):
		with self.assertRaises(frappe.ValidationError):
			self.dossier.enregistrer_paiement(100, today(), "VIR-1")

	def test_envoi_puis_paiement_partiel_puis_solde(self):
		self.dossier.marquer_envoye()
		res = self.dossier.enregistrer_paiement(800, today(), "VIR-1")
		self.assertEqual((res["statut"], res["total_paye"]), ("Payé partiellement", 800))
		# répartition de la plus ancienne facture à la plus récente : 700 puis 100
		self.dossier.reload()
		self.assertEqual([r.montant_paye for r in self.dossier.factures], [700, 100])
		res = self.dossier.enregistrer_paiement(250, today(), "VIR-2")
		self.assertEqual((res["statut"], res["total_paye"]), ("Payé", 1050))

	def test_montant_excessif_refuse(self):
		self.dossier.marquer_envoye()
		with self.assertRaises(frappe.ValidationError):
			self.dossier.enregistrer_paiement(1051, today(), "VIR-1")

	def test_reference_obligatoire_et_montant_positif(self):
		self.dossier.marquer_envoye()
		with self.assertRaises(frappe.ValidationError):
			self.dossier.enregistrer_paiement(10, today(), "  ")
		with self.assertRaises(frappe.ValidationError):
			self.dossier.enregistrer_paiement(0, today(), "VIR-1")

	def test_paiement_reduit_la_creance(self):
		self.dossier.marquer_envoye()
		avant = frappe.db.get_value("Sales Invoice", self.f1.name, "outstanding_amount")
		self.dossier.enregistrer_paiement(700, today(), "VIR-1")
		apres = frappe.db.get_value("Sales Invoice", self.f1.name, "outstanding_amount")
		self.assertEqual(avant - apres, 700)


class TestImpression(Base):
	def test_formats_se_rendent_sans_erreur(self):
		cov = self._couverture()
		si = self._facture(400, cov, soumettre=True)
		html = frappe.get_print("Sales Invoice", si.name, print_format="Facture MedMa")
		self.assertIn("Part à payer par le patient", html)
		self.assertIn("120,00 MAD", html)  # 30 % de 400
		self.assertIn("400,00 MAD", html)  # total à payer


SURVEILLES = ["Sales Invoice", "Patient", "Customer", "Item", "Organisme Payeur", "Couverture Patient",
              "Dossier Remboursement", "Payment Entry", "GL Entry"]


def run_all():
	avant = {dt: frappe.db.count(dt) for dt in SURVEILLES}
	suite = unittest.defaultTestLoader.loadTestsFromModule(__import__("medma_ma.tests.test_medma", fromlist=["x"]))
	res = unittest.TextTestRunner(verbosity=2).run(suite)
	frappe.db.rollback()
	apres = {dt: frappe.db.count(dt) for dt in SURVEILLES}
	if avant != apres:
		diff = {dt: (avant[dt], apres[dt]) for dt in SURVEILLES if avant[dt] != apres[dt]}
		raise AssertionError(f"Les tests ont laissé des données dans la base : {diff}")
	print("Aucune fuite de données : compteurs identiques avant/après.")
	if not res.wasSuccessful():
		raise SystemExit(1)


class TestPortailEtCartes(Base):
	def test_portail_lie_utilisateur_et_patient_par_email(self):
		from healthcare.healthcare.web_form.lab_test.lab_test import get_patient

		email = "test.portail@chtmed.ma"
		frappe.get_doc({"doctype": "User", "email": email, "first_name": "Portail", "user_type": "Website User",
			"send_welcome_email": 0, "roles": [{"role": "Patient"}]}).insert(ignore_permissions=True)
		frappe.db.set_value("Patient", self.patient.name, "email", email)
		frappe.set_user(email)
		try:
			self.assertEqual(get_patient(), self.patient.name)
		finally:
			frappe.set_user("Administrator")

	def test_cartes_ont_des_filtres_valides(self):
		import json

		from medma_ma.setup import CARTES

		for label, (dt, filtres) in CARTES.items():
			self.assertTrue(frappe.db.exists("Number Card", label), label)
			frappe.get_list(dt, filters=[f[1:] if f[0] == dt else f for f in json.loads(frappe.db.get_value("Number Card", label, "filters_json"))], limit=1)

	def test_formulaires_portail_affichent_la_liste(self):
		for nom in ("lab-test", "prescription", "patient-appointments"):
			self.assertEqual(frappe.db.get_value("Web Form", nom, "show_list"), 1, nom)
