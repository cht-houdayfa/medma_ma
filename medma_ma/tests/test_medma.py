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
		self.assertIn("exonéré de TVA", html)  # modèle par défaut : pas de TVA sur les actes médicaux

	def test_modele_de_taxe_par_defaut_sans_tva(self):
		defaut = frappe.get_all("Sales Taxes and Charges Template", filters={"is_default": 1}, pluck="name")
		self.assertEqual(len(defaut), 1)
		self.assertIn("exonéré", defaut[0])
		self.assertFalse(frappe.get_doc("Sales Taxes and Charges Template", defaut[0]).taxes)

	def test_la_facture_avec_tva_affiche_ht_tva_ttc(self):
		modele = frappe.db.get_value("Sales Taxes and Charges Template", {"name": ["like", "%VAT 20%"]}, "name")
		si = self._facture(400)
		ligne = frappe.get_doc("Sales Taxes and Charges Template", modele).taxes[0]
		si.taxes_and_charges = modele
		si.append("taxes", {"charge_type": "On Net Total", "account_head": ligne.account_head,
		                    "description": "TVA", "rate": 20})
		si.save()
		html = frappe.get_print("Sales Invoice", si.name, print_format="Facture MedMa")
		for texte in ("Total HT", "Total TTC", "480,00 MAD"):
			self.assertIn(texte, html)


SURVEILLES = ["Passage Urgences", "Resume Sortie", "Certificat Medical", "Sales Invoice", "Patient", "Customer", "Item", "Organisme Payeur", "Couverture Patient",
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


class TestCertificat(Base):
	def _certificat(self, **kw):
		prat = frappe.get_all("Healthcare Practitioner", pluck="name", limit=1)[0]
		return frappe.get_doc({"doctype": "Certificat Medical", "patient": self.patient.name, "practitioner": prat,
			"type_certificat": "Arrêt de travail", **kw})

	def test_arret_calcule_les_jours(self):
		c = self._certificat(debut=today(), fin=add_days(today(), 4)).insert(ignore_permissions=True)
		self.assertEqual(c.nombre_jours, 5)

	def test_arret_exige_les_dates_et_leur_ordre(self):
		with self.assertRaises(frappe.ValidationError):
			self._certificat().insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			self._certificat(debut=today(), fin=add_days(today(), -1)).insert(ignore_permissions=True)

	def test_certificat_simple_sans_periode(self):
		c = self._certificat(type_certificat="Certificat médical", debut=today(), fin=today()).insert(ignore_permissions=True)
		self.assertEqual((c.nombre_jours, c.debut), (0, None))

	def test_impression(self):
		c = self._certificat(debut=today(), fin=add_days(today(), 1)).insert(ignore_permissions=True)
		html = frappe.get_print("Certificat Medical", c.name, print_format="Certificat MedMa")
		self.assertIn("ARRÊT DE TRAVAIL", html)
		self.assertIn("2 jour(s)", html)
		# document français : reste de gauche à droite même imprimé depuis une interface arabe
		self.assertIn("direction: ltr", html)


class TestCataloguesConsultation(Base):
	def test_medecin_choisit_medicaments_et_analyses_dans_les_listes(self):
		from frappe.desk.search import search_link

		frappe.set_user("demo.medecin@chtmed.ma")
		try:
			self.assertTrue(search_link("Medication", ""))
			self.assertTrue(search_link("Lab Test Template", ""))
			self.assertFalse(frappe.has_permission("Medication", "write"))
			# la ligne d'analyse de la consultation lit aussi ce modèle : sans droit, le formulaire affiche « Pas permis »
			self.assertTrue(frappe.has_permission("Observation Template", "read"))
			self.assertTrue(frappe.has_permission("Nursing Checklist Template", "read"))
			# la grille d'analyses de la consultation propose le catalogue (colonne « Analyse »)
			champ = frappe.get_meta("Lab Prescription").get_field("lab_test_code")
			self.assertEqual((champ.in_list_view, champ.label), (1, "Analyse"))
			# prescription par DCI : la marque n'est pas obligatoire (sinon « Drug Code is mandatory » dès que le médicament a plusieurs marques)
			self.assertFalse(frappe.get_meta("Drug Prescription").get_field("drug_code").reqd)
		finally:
			frappe.set_user("Administrator")


class TestImportCatalogues(Base):
	def _csv(self, contenu):
		import tempfile

		f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
		f.write(contenu)
		f.close()
		self.addCleanup(__import__("os").unlink, f.name)
		return f.name

	def test_medicaments_idempotent_et_erreurs_listees(self):
		from medma_ma.importer import importer_medicaments

		src = self._csv(
			"nom_commercial;dci;dosage;unite;forme;classe;ppv;prix_achat;code\n"
			"TESTIMP-A;Testamol;500;mg;Comprimé;Antalgique;12,50;9;AMM1\n"
			"TESTIMP-B;Testamol;500;mg;Comprimé;Antalgique;11;;\n"
			"TESTIMP-C;Testamol;;mg;Comprimé;Antalgique;5;;\n"
		)
		r1 = importer_medicaments(src)
		self.assertEqual((r1["crees"], len(r1["erreurs"])), (2, 1))
		med = frappe.get_doc("Medication", "Testamol 500mg")
		self.assertEqual({x.item_code: x.rate for x in med.linked_items}, {"TESTIMP-A": 12.5, "TESTIMP-B": 11})
		r2 = importer_medicaments(src)
		self.assertEqual((r2["crees"], r2["mis_a_jour"]), (0, 2))
		self.assertEqual(len(frappe.get_doc("Medication", "Testamol 500mg").linked_items), 2)

	def test_analyses_et_simulation(self):
		from medma_ma.importer import importer_analyses

		src = self._csv("code,nom,departement,tarif\nB999,Test TSH importé,Biochemistry,150\n")
		importer_analyses(src, dry_run=1)
		self.assertFalse(frappe.db.exists("Lab Test Template", "Test TSH importé"))
		importer_analyses(src)
		self.assertEqual(frappe.db.get_value("Lab Test Template", "Test TSH importé", "lab_test_code"), "B999")


def _agent_lis():
	import importlib.util
	import os

	chemin = os.path.join(os.path.dirname(__file__), "..", "..", "deploy", "lis", "lis_agent.py")
	spec = importlib.util.spec_from_file_location("lis_agent", chemin)
	mod = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(mod)
	return mod


class TestLIS(Base):
	def test_astm_avec_trames_et_hl7_mllp(self):
		agent = _agent_lis()
		astm = (b"\x05\x02" b"1H|\\^&|||BC-6800\r" b"P|1\r" b"O|1|HLC-LAB-2026-00001||^^^GLU|R\r"
		        b"R|1|^^^GLU|5.4|mmol/L|3.9-6.1|N||F\r" b"L|1|N\r\x03" b"00\r\n\x04")
		ech = agent.analyser(astm)
		self.assertEqual(ech[0]["echantillon"], "HLC-LAB-2026-00001")
		self.assertEqual((ech[0]["resultats"][0]["code"], ech[0]["resultats"][0]["valeur"]), ("GLU", "5.4"))
		hl7 = (b"\x0bMSH|^~\\&|BC|LAB|M|C|2026||ORU^R01|1|P|2.3.1\rOBR|1||HLC-LAB-2026-00002|X\r"
		       b"OBX|1|NM|WBC^Globules blancs||6.2|10*9/L|4-10|N|||F\rOBX|2|ED|IMG^histo||blob\r\x1c\r")
		ech = agent.analyser(hl7)
		self.assertEqual(ech[0]["echantillon"], "HLC-LAB-2026-00002")
		self.assertEqual(len(ech[0]["resultats"]), 1)  # l'image (ED) est ignorée
		self.assertEqual(ech[0]["resultats"][0]["libelle"], "Globules blancs")

	def test_resultats_inscrits_en_brouillon_sans_validation(self):
		from medma_ma.lis import recevoir_resultats

		modele = frappe.db.get_value("Lab Test Template", {"lab_test_name": "CRP"}, "name")
		analyse = frappe.get_doc({"doctype": "Lab Test", "patient": self.patient.name, "template": modele,
		                          "company": self.company, "patient_sex": self.patient.sex or "Male"}).insert(ignore_permissions=True)
		rep = recevoir_resultats(analyse.name, [{"libelle": "CRP", "valeur": "12.5", "reference": "0-5"},
		                                        {"libelle": "XYZ", "valeur": "1"}], "Test")
		self.assertEqual(len(rep["appliques"]), 1)
		self.assertEqual(rep["ignores"][0]["libelle"], "XYZ")  # rien n'est perdu en silence
		analyse.reload()
		self.assertEqual(analyse.docstatus, 0)  # jamais validé automatiquement
		self.assertEqual(analyse.normal_test_items[0].result_value, "12.5")
		self.assertEqual(analyse.etat_prelevement, "Prélevé - en attente du résultat")

	def test_analyse_validee_refuse_les_resultats(self):
		from medma_ma.lis import recevoir_resultats

		analyse = frappe.get_all("Lab Test", filters={"docstatus": 1}, pluck="name", limit=1)[0]
		with self.assertRaises(frappe.ValidationError):
			recevoir_resultats(analyse, [{"libelle": "CRP", "valeur": "1"}])


class TestMenusParRole(Base):
	def _espaces(self, role):
		from frappe.desk.desktop import get_workspace_sidebar_items

		frappe.set_user(f"demo.{role}@chtmed.ma")
		try:
			return {p["name"] for p in get_workspace_sidebar_items().get("pages", [])}
		finally:
			frappe.set_user("Administrator")

	def test_la_reception_inscrit_les_patients_sans_voir_le_dossier_medical(self):
		u = "demo.reception@chtmed.ma"
		self.assertTrue(frappe.has_permission("Patient", "create", user=u))
		self.assertTrue(frappe.has_permission("Healthcare Practitioner", "read", user=u))
		self.assertTrue(frappe.has_permission("Patient Appointment", "create", user=u))
		# secret médical : pas d'accès aux consultations ni aux constantes
		self.assertFalse(frappe.has_permission("Patient Encounter", "read", user=u))
		self.assertFalse(frappe.has_permission("Vital Signs", "read", user=u))

	def test_la_reception_ne_voit_ni_pilotage_ni_clinique(self):
		vus = self._espaces("reception")
		self.assertIn("Réception", vus)
		# ni pilotage, ni clinique, ni comptabilité complète, ni module Healthcare natif, ni ventes
		for interdit in ("Tableau de bord", "Laboratoire", "Soins infirmiers", "Accounting", "Payables",
		                 "Receivables", "Financial Reports", "Healthcare", "Selling"):
			self.assertNotIn(interdit, vus)
		# son guide, et seulement le sien
		self.assertIn("Guide Réception", vus)
		self.assertFalse({v for v in vus if v.startswith("Guide ")} - {"Guide Réception"})

	def test_chaque_metier_ne_voit_que_ses_espaces(self):
		autorises = {
			"medecin": {"Cabinet médecin", "Urgences", "Guide Médecin"},
			"infirmier": {"Soins infirmiers", "Urgences", "Guide Infirmier"},
			"labo": {"Laboratoire", "Guide Laboratoire"},
			"pharmacie": {"Pharmacie", "Stock", "Guide Pharmacie"},
			"compta": {"Tableau de bord", "MedMa", "Accounting", "Payables", "Receivables", "Financial Reports",
			           "Guide Comptabilité"},
		}
		for role, ok in autorises.items():
			vus = self._espaces(role)
			self.assertFalse(vus - ok, f"{role} voit des espaces hors métier : {sorted(vus - ok)}")

	def test_la_direction_voit_tout_le_metier(self):
		vus = self._espaces("direction")
		for attendu in ("Tableau de bord", "Réception", "Laboratoire", "Soins infirmiers", "Pharmacie"):
			self.assertIn(attendu, vus)

	def test_graphique_rendez_vous_affiche_des_entiers(self):
		champ = frappe.db.get_value("Dashboard Chart", "Rendez-vous par praticien", "value_based_on")
		self.assertEqual(frappe.get_meta("Patient Appointment").get_field(champ).fieldtype, "Int")
		# une devise ferait afficher « 13.00 د.م. » pour un nombre de rendez-vous
		self.assertFalse(frappe.db.get_value("Dashboard Chart", "Rendez-vous par praticien", "currency"))


class TestPrescriptionParDci(Base):
	def test_la_marque_n_est_pas_obligatoire(self):
		doc = frappe.get_doc({"doctype": "Patient Encounter", "drug_prescription": [
			{"medication": "Amlodipine", "dosage_form": "Comprimé", "period": "1 Week"}]})
		self.assertEqual(type(doc).__name__, "PatientEncounterMedMa")
		doc.validate_medications()  # ne doit pas lever « Drug Code is mandatory »


class TestCorrectifs(Base):
	def test_la_pharmacie_lit_les_ordonnances_sans_les_modifier(self):
		user = frappe.db.get_value("User", {"email": "demo.pharmacie@chtmed.ma"}, "name")
		self.assertTrue(frappe.has_permission("Medication Request", "read", user=user))
		self.assertFalse(frappe.has_permission("Medication Request", "write", user=user))
		self.assertFalse(frappe.has_permission("Patient Encounter", "read", user=user))

	def test_patient_sans_invitation_par_defaut(self):
		self.assertEqual(str(frappe.get_meta("Patient").get_field("invite_user").default), "0")

	def test_etat_du_prelevement_a_une_etape_validee(self):
		options = frappe.get_meta("Lab Test").get_field("etat_prelevement").options.split("\n")
		self.assertIn("Résultat validé", options)

	def test_fuseau_a_utc_plus_un(self):
		from frappe.utils import get_system_timezone, now_datetime
		import datetime
		self.assertEqual(get_system_timezone(), "Africa/Algiers")
		ecart = now_datetime() - datetime.datetime.utcnow()
		self.assertAlmostEqual(ecart.total_seconds(), 3600, delta=60)


class TestIdentifiantPatient(Base):
	def _patient_cin(self, nom, cin):
		doc = frappe.get_doc({"doctype": "Patient", "first_name": nom, "sex": "Male", "cin": cin})
		doc.insert(ignore_permissions=True)
		return doc

	def test_identifiant_serie_et_cin_unique(self):
		a = self._patient_cin("TestIdA", " zz 99 ")
		try:
			self.assertTrue(a.name.startswith("HLC-PAT-"), a.name)
			self.assertEqual(a.cin, "ZZ99")
			# même nom autorisé, identifiants distincts
			b = frappe.get_doc({"doctype": "Patient", "first_name": "TestIdA", "sex": "Male"}).insert(ignore_permissions=True)
			self.assertNotEqual(a.name, b.name)
			# même CIN refusé, même écrit autrement
			with self.assertRaises(frappe.ValidationError):
				self._patient_cin("TestIdC", "zz99")
			frappe.delete_doc("Patient", b.name, force=True, ignore_permissions=True)
		finally:
			frappe.delete_doc("Patient", a.name, force=True, ignore_permissions=True)


class TestUrgences(Base):
	def _passage(self, **kw):
		return frappe.get_doc({"doctype": "Passage Urgences", "patient": self.patient.name, "motif": "Douleur thoracique",
		                       "niveau_triage": "2 - Très urgent", **kw}).insert(ignore_permissions=True)

	def test_cycle_de_prise_en_charge_et_delai(self):
		p = self._passage()
		self.assertTrue(p.name.startswith("URG-"))
		self.assertEqual(p.statut, "En attente")
		self.assertFalse(p.date_prise_en_charge)
		p.statut = "En cours de soins"
		p.date_arrivee = frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=-25)
		p.save()
		p.reload()
		self.assertTrue(p.date_prise_en_charge)
		self.assertGreaterEqual(p.delai_attente, 24)
		# la sortie exige une orientation
		p.statut = "Terminé"
		with self.assertRaises(frappe.ValidationError):
			p.save()
		p.reload()
		p.statut = "Terminé"
		p.orientation = "Retour à domicile"
		p.save()
		self.assertTrue(p.date_sortie)

	def test_liens_affichent_le_nom_et_pas_le_numero(self):
		for dt in ("Patient", "Healthcare Practitioner"):
			self.assertTrue(frappe.get_meta(dt).show_title_field_in_link, dt)

	def test_heure_darrivee_prise_sur_le_serveur(self):
		p = self._passage()
		self.assertTrue(p.date_arrivee)
		self.assertLess(abs((frappe.utils.now_datetime() - frappe.utils.get_datetime(p.date_arrivee)).total_seconds()), 60)

	def test_constantes_aberrantes_refusees(self):
		with self.assertRaises(frappe.ValidationError):
			self._passage(saturation=250)
		with self.assertRaises(frappe.ValidationError):
			self._passage(tension_systolique=80, tension_diastolique=120)

	def test_menu_rapport_et_fiche(self):
		from frappe.desk.desktop import get_workspace_sidebar_items

		for role in ("medecin", "infirmier", "reception"):
			frappe.set_user(f"demo.{role}@chtmed.ma")
			try:
				self.assertIn("Urgences", {p["name"] for p in get_workspace_sidebar_items().get("pages", [])}, role)
			finally:
				frappe.set_user("Administrator")
		self._passage(niveau_triage="1 - Détresse vitale", motif="Arrêt respiratoire")
		self._passage(niveau_triage="4 - Moins urgent", motif="Entorse")
		res = frappe.db.sql(frappe.db.get_value("Report", "File d'attente des urgences", "query"), as_dict=False)
		self.assertTrue(res[0][0].startswith("1"))
		html = frappe.get_print("Passage Urgences", self._passage(motif="Fièvre").name, print_format="Fiche Urgences MedMa")
		for texte in ("FICHE D'URGENCE", "Fièvre", "Niveau de tri"):
			self.assertIn(texte, html)

	def test_cartes_et_acces(self):
		self._passage(niveau_triage="1 - Détresse vitale")
		for carte in ("Urgences en attente", "Urgences vitales en cours", "Passages urgences du jour"):
			self.assertTrue(frappe.db.exists("Number Card", carte), carte)
		for role, droit in (("infirmier", "create"), ("medecin", "write"), ("reception", "create")):
			self.assertTrue(frappe.has_permission("Passage Urgences", droit, user=f"demo.{role}@chtmed.ma"), role)
		for role in ("labo", "pharmacie", "compta"):
			self.assertFalse(frappe.has_permission("Passage Urgences", "read", user=f"demo.{role}@chtmed.ma"), role)


class TestUrgencesComplements(Base):
	def _passage(self, **kw):
		return frappe.get_doc({"doctype": "Passage Urgences", "patient": self.patient.name, "motif": "Chute",
		                       "niveau_triage": "3 - Urgent", **kw}).insert(ignore_permissions=True)

	def _boxes(self):
		return frappe.get_all("Healthcare Service Unit", {"service_unit_type": "Box d'urgence", "is_group": 0}, pluck="name", order_by="name")

	def test_les_boxes_existent_et_se_liberent(self):
		boxes = self._boxes()
		self.assertGreaterEqual(len(boxes), 4)
		p = self._passage(unite_service=boxes[0])
		self.assertEqual(frappe.db.get_value("Healthcare Service Unit", boxes[0], "occupancy_status"), "Occupied")
		# un second patient ne peut pas prendre le même lit
		autre = self._patient("AutreUrg")
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "Passage Urgences", "patient": autre.name, "motif": "Fièvre", "niveau_triage": "4 - Moins urgent",
			                "unite_service": boxes[0]}).insert(ignore_permissions=True)
		# changement de lit : l'ancien se libère
		p.reload()
		p.unite_service = boxes[1]
		p.save()
		self.assertEqual(frappe.db.get_value("Healthcare Service Unit", boxes[0], "occupancy_status"), "Vacant")
		self.assertEqual(frappe.db.get_value("Healthcare Service Unit", boxes[1], "occupancy_status"), "Occupied")
		# la clôture libère le lit
		p.reload()
		p.statut = "Terminé"
		p.orientation = "Retour à domicile"
		p.save()
		self.assertEqual(frappe.db.get_value("Healthcare Service Unit", boxes[1], "occupancy_status"), "Vacant")

	def test_un_lit_dhospitalisation_est_refuse_aux_urgences(self):
		chambre = frappe.db.get_value("Healthcare Service Unit", {"service_unit_type": "Chambre d'hospitalisation"}, "name")
		if chambre:
			with self.assertRaises(frappe.ValidationError):
				self._passage(unite_service=chambre)

	def test_allergie_bloque_la_prescription(self):
		from medma_ma.allergies import verifier_prescription

		self.patient.append("allergies_connues", {"categorie": "Médicament", "substance": "pénicilline", "gravite": "Sévère"})
		self.patient.save(ignore_permissions=True)
		ordonnance = frappe._dict(patient=self.patient.name, allergie_confirmee=0,
		                          drug_prescription=[frappe._dict(drug_name="Pénicilline V 1MUI", medication=None)])
		with self.assertRaises(frappe.ValidationError):
			verifier_prescription(ordonnance)
		# médicament sans rapport : aucune alerte
		verifier_prescription(frappe._dict(patient=self.patient.name, allergie_confirmee=0,
		                                   drug_prescription=[frappe._dict(drug_name="Paracétamol 1g", medication=None)]))
		# confirmation explicite du médecin : autorisé
		ordonnance.allergie_confirmee = 1
		verifier_prescription(ordonnance)
		# le passage aux urgences affiche l'allergie
		self.assertIn("pénicilline", self._passage().allergies_alerte)

	def test_resume_de_sortie_prerempli_et_imprimable(self):
		prat = frappe.db.get_value("Healthcare Practitioner", {}, "name")
		p = self._passage(diagnostic="Entorse de cheville", traitement="Repos, glaçage", practitioner=prat)
		p.reload()
		p.statut = "Terminé"
		p.orientation = "Retour à domicile"
		p.save()
		r = frappe.get_doc({"doctype": "Resume Sortie", "patient": self.patient.name, "practitioner": prat,
		                    "passage_urgences": p.name, "diagnostic": "Entorse de cheville"}).insert(ignore_permissions=True)
		self.assertEqual(r.traitement_sortie, "Repos, glaçage")
		self.assertEqual(r.orientation, "Retour à domicile")
		html = frappe.get_print("Resume Sortie", r.name, print_format="Résumé de sortie MedMa")
		for texte in ("RÉSUMÉ DE SORTIE", "Entorse de cheville", "Repos, glaçage"):
			self.assertIn(texte, html)
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "Resume Sortie", "patient": self._patient("Autre2").name, "practitioner": prat,
			                "passage_urgences": p.name, "diagnostic": "x"}).insert(ignore_permissions=True)

	def test_carte_lits_libres_et_droits(self):
		self.assertTrue(frappe.db.exists("Number Card", "Lits d'urgence libres"))
		for role in ("infirmier", "medecin", "reception"):
			self.assertTrue(frappe.has_permission("Healthcare Service Unit", "read", user=f"demo.{role}@chtmed.ma"), role)
		self.assertTrue(frappe.has_permission("Resume Sortie", "create", user="demo.medecin@chtmed.ma"))
		self.assertFalse(frappe.has_permission("Resume Sortie", "create", user="demo.infirmier@chtmed.ma"))
