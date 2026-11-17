"""Jeu de données de démonstration MedMa (100 % fictif).

Usage (sur un site où ERPNext, Healthcare et medma_ma sont installés) :
    bench --site <site> execute medma_ma.demo.load_demo

Tous les patients, médecins, numéros et montants sont inventés. Les tarifs sont des valeurs d'exemple,
pas des tarifs officiels (TNR/ANAM). Le chargement est idempotent : relancé, il ne duplique rien.
"""

import random

import frappe
from frappe.utils import add_days, flt, getdate, today

RNG = random.Random(2026)
LOG: list[str] = []
CTX: dict = {}


def log(msg):
	LOG.append(msg)
	print(msg)


def step(name):
	def deco(fn):
		def run(*a, **k):
			frappe.db.savepoint("demo_step")
			try:
				res = fn(*a, **k)
				frappe.db.commit()
				log(f"OK   {name}: {res}")
				return res
			except Exception as e:  # noqa: BLE001 - une étape en échec ne doit pas bloquer les suivantes
				frappe.db.rollback(save_point="demo_step")
				log(f"FAIL {name}: {type(e).__name__}: {str(e)[:400]}")
				return None

		return run

	return deco


def ensure(doctype, name, **fields):
	if frappe.db.exists(doctype, name):
		return frappe.get_doc(doctype, name)
	doc = frappe.get_doc({"doctype": doctype, **fields})
	doc.insert(ignore_permissions=True)
	return doc


# --------------------------------------------------------------------------- données

PRATICIENS = [
	# prénom, nom, sexe, département, tarif consultation (MAD, exemple), téléphone fictif
	("Karim", "Benjelloun", "Male", "Médecine générale", 200, "0600000101"),
	("Salma", "El Fassi", "Female", "Pédiatrie", 250, "0600000102"),
	("Youssef", "Amrani", "Male", "Cardiology", 400, "0600000103"),
	("Nadia", "Cherkaoui", "Female", "Gynaecology", 350, "0600000104"),
]

# prénom, nom, sexe, âge, groupe sanguin, ville, organisme, taux
PATIENTS = [
	("Mohamed", "Alaoui", "Male", 45, "A+", "Casablanca", "CNSS", 70),
	("Fatima", "Zahra Bennani", "Female", 38, "O+", "Rabat", "CNSS", 70),
	("Ahmed", "Tazi", "Male", 62, "B+", "Fès", "CNSS", 70),
	("Khadija", "Idrissi", "Female", 29, "A-", "Marrakech", "CNSS", 70),
	("Omar", "Lahlou", "Male", 51, "O-", "Tanger", "CNSS", 70),
	("Hassan", "Berrada", "Male", 55, "AB+", "Rabat", "CNOPS", 70),
	("Samira", "Kettani", "Female", 41, "A+", "Casablanca", "CNOPS", 70),
	("Rachid", "Sebti", "Male", 67, "B-", "Meknès", "CNOPS", 70),
	("Latifa", "Ouazzani", "Female", 34, "O+", "Agadir", "AMO Tadamon", 70),
	("Brahim", "Haddad", "Male", 72, "A+", "Oujda", "AMO Tadamon", 70),
	("Meriem", "Chraibi", "Female", 31, "B+", "Casablanca", "Wafa Assurance", 80),
	("Anas", "Mansouri", "Male", 27, "O+", "Rabat", "AXA Assurance Maroc", 90),
	("Hind", "Skalli", "Female", 8, "A+", "Casablanca", None, 0),
	("Ilyas", "Bouzid", "Male", 5, "O+", "Salé", "CNSS", 70),
	("Zineb", "Naciri", "Female", 36, "AB-", "Kénitra", None, 0),
	("Yassine", "Filali", "Male", 48, "B+", "Tétouan", None, 0),
]

MEDICAMENTS = [
	# générique, classe, dosage, unité, forme, marque (exemple), prix vente (MAD, exemple), prix achat
	("Paracétamol", "Antalgique", 1000, "mg", "Tablet", "Doliprane 1000 mg", 14, 9),
	("Amoxicilline", "Antibiotique", 1000, "mg", "Tablet", "Clamoxyl 1 g", 48, 33),
	("Oméprazole", "Inhibiteur de la pompe à protons", 20, "mg", "Capsule", "Mopral 20 mg", 62, 44),
	("Metformine", "Antidiabétique", 850, "mg", "Tablet", "Glucophage 850 mg", 28, 19),
	("Amlodipine", "Antihypertenseur", 5, "mg", "Tablet", "Amlor 5 mg", 55, 38),
]

ANALYSES = [
	# nom, département, prix (MAD, exemple)
	("NFS (Numération formule sanguine)", "Haematology", 90),
	("Glycémie à jeun", "Biochemistry", 40),
	("Bilan lipidique", "Biochemistry", 150),
	("CRP", "Biochemistry", 120),
	("Créatinine", "Biochemistry", 50),
]

DIAGNOSTICS = [
	("Grippe saisonnière", "Fièvre", ["Paracétamol"]),
	("Angine", "Mal de gorge", ["Amoxicilline", "Paracétamol"]),
	("Hypertension artérielle", "Maux de tête", ["Amlodipine"]),
	("Diabète de type 2", "Fatigue", ["Metformine"]),
	("Gastrite", "Douleurs abdominales", ["Oméprazole"]),
]


def company():
	if "company" not in CTX:
		CTX["company"] = frappe.db.get_value("Company", {}, "name")
		CTX["abbr"] = frappe.db.get_value("Company", CTX["company"], "abbr")
	return CTX["company"]


# --------------------------------------------------------------------------- étapes


@step("référentiels")
def ref_data():
	for u in ("mg", "g", "ml"):
		ensure("UOM", u, uom_name=u)
	for c in ("Antalgique", "Antibiotique", "Inhibiteur de la pompe à protons", "Antidiabétique", "Antihypertenseur"):
		ensure("Medication Class", c, medication_class=c)
	for d in ("Médecine générale", "Pédiatrie"):
		ensure("Medical Department", d, department=d)
	for dx, sym, _ in DIAGNOSTICS:
		ensure("Diagnosis", dx, diagnosis=dx)
		ensure("Complaint", sym, complaints=sym)
	return "ok"


@step("unités de soins")
def service_units():
	c, ab = company(), CTX["abbr"]
	root = f"All Healthcare Service Units - {ab}"
	for t, kw in (
		("Salle de consultation", {"allow_appointments": 1}),
		("Chambre d'hospitalisation", {"inpatient_occupancy": 1}),
	):
		ensure("Healthcare Service Unit Type", t, service_unit_type=t, **kw)

	def unit(name, parent, is_group=0, typ=None, **kw):
		full = f"{name} - {ab}"
		if frappe.db.exists("Healthcare Service Unit", full):
			return full
		d = frappe.get_doc(
			{
				"doctype": "Healthcare Service Unit",
				"healthcare_service_unit_name": name,
				"parent_healthcare_service_unit": parent,
				"is_group": is_group,
				"service_unit_type": typ,
				"company": c,
				**kw,
			}
		)
		d.insert(ignore_permissions=True)
		return d.name

	g1 = unit("Consultations", root, 1)
	CTX["cabinets"] = [unit(f"Cabinet {i}", g1, 0, "Salle de consultation") for i in (1, 2, 3, 4)]
	g2 = unit("Hospitalisation", root, 1)
	CTX["lits"] = [unit(f"Chambre 10{i}", g2, 0, "Chambre d'hospitalisation") for i in (1, 2, 3)]
	return f"{len(CTX['cabinets'])} cabinets, {len(CTX['lits'])} chambres"


@step("tarifs consultation")
def consultation_items():
	for _, _, _, dept, prix, _ in PRATICIENS:
		pass
	types = [("Consultation générale", 200), ("Consultation spécialiste", 350), ("Contrôle / suivi", 150), ("Téléconsultation", 150)]
	for n, prix in types:
		ensure("Item", n, item_code=n, item_name=n, item_group="Services", stock_uom="Unit", is_stock_item=0)
		if not frappe.db.exists("Item Price", {"item_code": n, "price_list": "Vente standard"}):
			frappe.get_doc(
				{"doctype": "Item Price", "item_code": n, "price_list": "Vente standard", "price_list_rate": prix, "currency": "MAD"}
			).insert(ignore_permissions=True)
		ensure("Appointment Type", n, appointment_type=n, allow_booking_for="Practitioner", default_duration=20)
	return f"{len(types)} types"


@step("praticiens")
def practitioners():
	slots = [
		{"day": d, "from_time": "09:00:00", "to_time": "13:00:00"} for d in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
	] + [{"day": d, "from_time": "15:00:00", "to_time": "18:00:00"} for d in ("Monday", "Wednesday", "Friday")]
	ensure("Practitioner Schedule", "Horaires cabinet", schedule_name="Horaires cabinet", time_slots=slots)
	CTX["praticiens"] = []
	for i, (pre, nom, sexe, dept, prix, tel) in enumerate(PRATICIENS):
		item = f"Consultation - Dr {pre} {nom}"
		ensure("Item", item, item_code=item, item_name=item, item_group="Services", stock_uom="Unit", is_stock_item=0)
		if not frappe.db.exists("Item Price", {"item_code": item, "price_list": "Vente standard"}):
			frappe.get_doc(
				{"doctype": "Item Price", "item_code": item, "price_list": "Vente standard", "price_list_rate": prix, "currency": "MAD"}
			).insert(ignore_permissions=True)
		existing = frappe.db.get_value("Healthcare Practitioner", {"first_name": pre, "last_name": nom})
		if existing:
			CTX["praticiens"].append(existing)
			continue
		d = frappe.get_doc(
			{
				"doctype": "Healthcare Practitioner",
				"first_name": pre,
				"last_name": nom,
				"gender": sexe,
				"status": "Active",
				"department": dept,
				"mobile_phone": tel,
				"op_consulting_charge_item": item,
				"op_consulting_charge": prix,
				"practitioner_schedules": [{"schedule": "Horaires cabinet", "service_unit": CTX["cabinets"][i % len(CTX["cabinets"])]}],
			}
		)
		d.insert(ignore_permissions=True)
		CTX["praticiens"].append(d.name)
	return ", ".join(CTX["praticiens"])


@step("analyses de laboratoire")
def lab_templates():
	for nom, dept, prix in ANALYSES:
		if frappe.db.exists("Lab Test Template", nom):
			continue
		frappe.get_doc(
			{
				"doctype": "Lab Test Template",
				"lab_test_name": nom,
				"lab_test_code": nom,
				"lab_test_description": nom,
				"department": dept,
				"lab_test_group": "Laboratory",
				"lab_test_template_type": "Single",
				"is_billable": 1,
				"lab_test_rate": prix,
			}
		).insert(ignore_permissions=True)
	return f"{len(ANALYSES)} analyses"


@step("médicaments")
def medications():
	for gen, classe, dose, uom, forme, marque, pv, pa in MEDICAMENTS:
		ensure("Brand", marque, brand=marque)
		if not frappe.db.exists("Medication", gen):
			frappe.get_doc(
				{
					"doctype": "Medication",
					"generic_name": gen,
					"medication_class": classe,
					"strength": dose,
					"strength_uom": uom,
					"dosage_form": forme,
					"linked_items": [
						{
							"item_code": marque,
							"item_group": "Drug",
							"stock_uom": "Unit",
							"brand": marque,
							"is_billable": 1,
							"rate": pv,
						}
					],
				}
			).insert(ignore_permissions=True)
		# Les médicaments sont des articles de stock, valorisés au prix d'achat.
		if frappe.db.exists("Item", marque):
			frappe.db.set_value("Item", marque, {"is_stock_item": 1, "valuation_rate": pa}, update_modified=False)
	return f"{len(MEDICAMENTS)} médicaments"


@step("stock pharmacie")
def stock():
	c = company()
	wh = f"Magasins - {CTX['abbr']}"
	if frappe.db.exists("Stock Entry", {"remarks": "Démo : stock initial pharmacie", "docstatus": 1}):
		return "déjà fait"
	se = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"company": c,
			"remarks": "Démo : stock initial pharmacie",
			"items": [
				{"item_code": m[5], "qty": 200, "basic_rate": m[7], "t_warehouse": wh} for m in MEDICAMENTS
			],
		}
	)
	se.insert(ignore_permissions=True)
	se.submit()
	return f"{len(MEDICAMENTS)} lignes reçues"


@step("patients et couvertures")
def patients():
	CTX["patients"] = []
	for i, (pre, nom, sexe, age, gs, ville, org, taux) in enumerate(PATIENTS):
		cin = f"DEMO{100000 + i}"
		existing = frappe.db.get_value("Patient", {"cin": cin})
		if existing:
			CTX["patients"].append((existing, org, taux))
			continue
		dob = add_days(today(), -int(age * 365.25) - RNG.randint(0, 300))
		p = frappe.get_doc(
			{
				"doctype": "Patient",
				"first_name": pre,
				"last_name": nom,
				"sex": sexe,
				"dob": dob,
				"blood_group": gs.replace("+", " Positive").replace("-", " Negative"),
				"mobile": f"06000002{i:02d}",
				"cin": cin,
			}
		)
		p.insert(ignore_permissions=True)
		cov = None
		if org:
			cov = frappe.get_doc(
				{
					"doctype": "Couverture Patient",
					"patient": p.name,
					"organisme": org,
					"numero_affiliation": f"{RNG.randint(100000000, 999999999)}",
					"taux_prise_en_charge": taux,
				}
			)
			cov.insert(ignore_permissions=True)
		CTX["patients"].append((p.name, org, taux))
	return f"{len(CTX['patients'])} patients"


# --------------------------------------------------------------------------- parcours cliniques


def _praticiens():
	return frappe.get_all(
		"Healthcare Practitioner",
		filters={"first_name": ["in", [p[0] for p in PRATICIENS]]},
		fields=["name", "first_name", "last_name", "department", "op_consulting_charge_item", "op_consulting_charge"],
		order_by="creation asc",
	)


def _patients():
	rows = frappe.get_all(
		"Patient", filters={"cin": ["like", "DEMO%"]}, fields=["name", "customer", "sex", "cin", "patient_name"], order_by="cin asc"
	)
	for r in rows:
		cov = frappe.db.get_value(
			"Couverture Patient", {"patient": r.name}, ["name", "organisme", "taux_prise_en_charge"], as_dict=True
		)
		r["couverture"] = cov
	return rows


def _jours_ouvres(n_back):
	jours = []
	d = getdate(today())
	for k in range(1, n_back + 1):
		x = add_days(d, -k)
		if getdate(x).weekday() < 5:
			jours.append(getdate(x))
	return jours


def _heure(k):
	h = 9 * 60 + 20 * k
	return f"{h // 60:02d}:{h % 60:02d}:00"


@step("rendez-vous, constantes, consultations, analyses")
def parcours():
	if frappe.db.count("Patient Appointment", {"notes": "demo"}):
		return "déjà chargé"
	c = company()
	pracs, pats = _praticiens(), _patients()
	jours = _jours_ouvres(21)
	slot = {}
	ids = {"rdv": 0, "enc": 0, "vitals": 0, "lab": 0}
	CTX["rdv_clos"] = []

	def creneau(prac, jour):
		k = slot.get((prac, jour), 0)
		slot[(prac, jour)] = k + 1
		return _heure(k)

	for n in range(30):
		prac = pracs[RNG.randrange(len(pracs))]
		pat = pats[RNG.randrange(len(pats))]
		jour = jours[RNG.randrange(len(jours))]
		suivi = RNG.random() < 0.25
		if suivi:
			typ, item, prix = "Contrôle / suivi", "Contrôle / suivi", 150
		else:
			typ = "Consultation générale" if prac.department == "Médecine générale" else "Consultation spécialiste"
			item, prix = prac.op_consulting_charge_item, prac.op_consulting_charge
		heure = creneau(prac.name, jour)
		appt = frappe.get_doc(
			{
				"doctype": "Patient Appointment",
				"appointment_type": typ,
				"appointment_for": "Practitioner",
				"company": c,
				"patient": pat.name,
				"practitioner": prac.name,
				"appointment_date": jour,
				"appointment_time": heure,
				"duration": 20,
				"status": "Closed",
				"notes": "demo",
			}
		)
		appt.flags.ignore_validate = True
		appt.flags.ignore_mandatory = True
		appt.insert(ignore_permissions=True)
		frappe.db.set_value("Patient Appointment", appt.name, "status", "Closed", update_modified=False)
		ids["rdv"] += 1
		CTX.setdefault("rdv_clos", []).append((appt.name, pat, prac, jour, item, prix))

		# constantes
		frappe.get_doc(
			{
				"doctype": "Vital Signs",
				"naming_series": "HLC-VTS-.YYYY.-",
				"patient": pat.name,
				"appointment": appt.name,
				"signs_date": jour,
				"signs_time": heure,
				"temperature": round(RNG.uniform(36.4, 38.6), 1),
				"pulse": RNG.randint(62, 96),
				"bp": f"{RNG.randint(110, 150)}/{RNG.randint(68, 95)}",
				"height": RNG.randint(150, 188),
				"weight": RNG.randint(48, 98),
			}
		).insert(ignore_permissions=True)
		ids["vitals"] += 1

		# consultation (un rendez-vous sur deux, hors contrôle)
		if not suivi and RNG.random() < 0.7:
			dx, sym, meds = DIAGNOSTICS[RNG.randrange(len(DIAGNOSTICS))]
			rows = []
			for gen in meds:
				m = next(x for x in MEDICAMENTS if x[0] == gen)
				rows.append(
					{
						"medication": gen,
						"drug_code": m[5],
						"drug_name": gen,
						"dosage_form": m[4],
						"period": "1 Week",
						"comment": "1 prise matin et soir",
					}
				)
			labs = []
			if dx in ("Diabète de type 2", "Hypertension artérielle"):
				labs = [{"lab_test_code": "Glycémie à jeun"}, {"lab_test_code": "Bilan lipidique"}]
			elif dx == "Angine":
				labs = [{"lab_test_code": "CRP"}, {"lab_test_code": "NFS (Numération formule sanguine)"}]
			enc = frappe.get_doc(
				{
					"doctype": "Patient Encounter",
					"patient": pat.name,
					"practitioner": prac.name,
					"appointment": appt.name,
					"company": c,
					"encounter_date": jour,
					"encounter_time": heure,
					"symptoms": [{"complaint": sym}],
					"diagnosis": [{"diagnosis": dx}],
					"drug_prescription": rows,
					"lab_test_prescription": labs,
					"encounter_comment": f"Consultation de démonstration ({dx}).",
				}
			)
			enc.flags.ignore_validate = True
			enc.insert(ignore_permissions=True)
			ids["enc"] += 1
			for lab in labs[:1]:
				try:
					lt = frappe.get_doc(
						{
							"doctype": "Lab Test",
							"naming_series": "HLC-LAB-.YYYY.-",
							"template": lab["lab_test_code"],
							"patient": pat.name,
							"patient_sex": pat.sex,
							"practitioner": prac.name,
							"company": c,
							"result_date": jour,
						}
					)
					lt.insert(ignore_permissions=True)
					ids["lab"] += 1
				except Exception as e:  # noqa: BLE001
					log(f"  (lab test ignoré : {str(e)[:120]})")

	# rendez-vous à venir
	futurs = []
	d = getdate(today())
	k = 1
	while len(futurs) < 8:
		x = add_days(d, k)
		k += 1
		if getdate(x).weekday() < 5:
			futurs.append(getdate(x))
	for i, jour in enumerate(futurs):
		prac = pracs[i % len(pracs)]
		pat = pats[(i * 3) % len(pats)]
		typ = "Consultation générale" if prac.department == "Médecine générale" else "Consultation spécialiste"
		a = frappe.get_doc(
			{
				"doctype": "Patient Appointment",
				"appointment_type": typ,
				"appointment_for": "Practitioner",
				"company": c,
				"patient": pat.name,
				"practitioner": prac.name,
				"appointment_date": jour,
				"appointment_time": _heure(i % 6),
				"duration": 20,
				"status": "Scheduled",
				"notes": "demo",
			}
		)
		a.flags.ignore_validate = True
		a.flags.ignore_mandatory = True
		a.insert(ignore_permissions=True)
		ids["rdv"] += 1
	return ids


@step("résultats de laboratoire")
def resultats_labo():
	valeurs = {
		"Glycémie à jeun": lambda: f"{RNG.uniform(0.8, 1.9):.2f}",
		"Bilan lipidique": lambda: f"{RNG.uniform(1.4, 2.6):.2f}",
		"CRP": lambda: f"{RNG.uniform(1, 48):.0f}",
		"NFS (Numération formule sanguine)": lambda: f"{RNG.uniform(4.2, 11.5):.1f}",
		"Créatinine": lambda: f"{RNG.uniform(6, 14):.0f}",
	}
	ok = bad = 0
	for n in frappe.get_all("Lab Test", filters={"docstatus": 0}, pluck="name"):
		d = frappe.get_doc("Lab Test", n)
		try:
			for r in d.normal_test_items:
				r.result_value = valeurs.get(d.template, lambda: "1")()
			d.save(ignore_permissions=True)
			d.submit()
			ok += 1
		except Exception as e:  # noqa: BLE001
			bad += 1
			log(f"  (labo {n} non validé : {str(e)[:100]})")
			frappe.db.rollback()
	return f"{ok} validés, {bad} en brouillon"


def _compte(type_):
	return frappe.db.get_value("Account", {"company": company(), "account_type": type_, "is_group": 0}, "name")


def _paiement(si_name, montant, date, mode, ref=None):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	if flt(montant) <= 0:
		return None
	pe = get_payment_entry("Sales Invoice", si_name, party_amount=flt(montant))
	pe.posting_date = date
	pe.mode_of_payment = mode
	compte = _compte("Bank") if mode == "Virement" else _compte("Cash")
	if compte:
		pe.paid_to = compte
	if mode == "Virement":
		pe.reference_no = ref or f"VIR-{si_name[-6:]}"
		pe.reference_date = date
	pe.insert(ignore_permissions=True)
	pe.submit()
	return pe.name


@step("factures partagées et paiements")
def facturation():
	if frappe.db.count("Sales Invoice", {"remarks": "demo"}):
		return "déjà chargé"
	c = company()
	rdvs = frappe.get_all(
		"Patient Appointment",
		filters={"notes": "demo", "status": "Closed"},
		fields=["name", "patient", "practitioner", "appointment_date", "appointment_type"],
		order_by="appointment_date asc",
	)
	pracs = {p.name: p for p in _praticiens()}
	pats = {p.name: p for p in _patients()}
	stats = {"factures": 0, "couvertes": 0, "impayees": 0}
	for i, r in enumerate(rdvs):
		pat, prac = pats[r.patient], pracs[r.practitioner]
		if r.appointment_type == "Contrôle / suivi":
			item, prix = "Contrôle / suivi", 150
		else:
			item, prix = prac.op_consulting_charge_item, prac.op_consulting_charge
		cov = pat.couverture
		si = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"customer": pat.customer,
				"patient": pat.name,
				"company": c,
				"currency": "MAD",
				"posting_date": r.appointment_date,
				"set_posting_time": 1,
				"due_date": r.appointment_date,
				"remarks": "demo",
				"couverture_patient": cov.name if cov else None,
				"items": [{"item_code": item, "qty": 1, "rate": prix}],
			}
		)
		si.insert(ignore_permissions=True)
		si.submit()
		frappe.db.set_value("Patient Appointment", r.name, {"invoiced": 1, "ref_sales_invoice": si.name}, update_modified=False)
		stats["factures"] += 1
		if cov:
			stats["couvertes"] += 1
		# les 3 dernières factures restent impayées côté patient (démonstration des créances)
		if i >= len(rdvs) - 3:
			stats["impayees"] += 1
			continue
		_paiement(si.name, si.part_patient if cov else si.grand_total, r.appointment_date, "Espèces")
	return stats


@step("dossiers de remboursement")
def dossiers():
	if frappe.db.count("Dossier Remboursement"):
		return "déjà chargé"
	debut = add_days(today(), -30)
	fin = add_days(today(), -1)
	scenario = [
		("CNSS", "Payé"),
		("CNOPS", "Payé partiellement"),
		("AMO Tadamon", "Envoyé"),
		("Wafa Assurance", "Brouillon"),
	]
	out = []
	for org, statut in scenario:
		d = frappe.get_doc({"doctype": "Dossier Remboursement", "organisme": org, "date_debut": debut, "date_fin": fin})
		d.charger_factures()
		if not d.factures:
			out.append(f"{org}: aucune facture")
			continue
		d.statut = "Brouillon"
		d.insert(ignore_permissions=True)
		invoices = [r.sales_invoice for r in d.factures]
		paye = 0
		if statut in ("Payé", "Payé partiellement"):
			cible = invoices if statut == "Payé" else invoices[: max(1, len(invoices) // 2)]
			for si in cible:
				part = flt(frappe.db.get_value("Sales Invoice", si, "part_organisme"))
				if _paiement(si, part, add_days(today(), -1), "Virement", ref=f"{org[:4].upper()}-{si[-5:]}"):
					paye += part
					for ligne in d.factures:
						if ligne.sales_invoice == si:
							ligne.montant_paye = part
		d.statut = statut
		d.save(ignore_permissions=True)
		out.append(f"{org}: {len(invoices)} fact., {statut}, réclamé {d.total_reclame}, payé {paye}")
	return " | ".join(out)


@step("correction des ordonnances")
def corriger_prescriptions():
	marques = {m[0]: m[5] for m in MEDICAMENTS}
	n = 0
	for r in frappe.get_all("Drug Prescription", filters={"parenttype": "Patient Encounter"}, fields=["name", "drug_code", "medication"]):
		if r.drug_code in marques and not r.medication:
			frappe.db.set_value("Drug Prescription", r.name, {"medication": r.drug_code, "drug_code": marques[r.drug_code]}, update_modified=False)
			n += 1
	return f"{n} lignes corrigées"


@step("validation des consultations")
def valider_consultations():
	ok = bad = 0
	for n in frappe.get_all("Patient Encounter", filters={"docstatus": 0}, pluck="name"):
		try:
			d = frappe.get_doc("Patient Encounter", n)
			d.flags.ignore_validate = False
			d.submit()
			ok += 1
		except Exception as e:  # noqa: BLE001
			bad += 1
			frappe.db.rollback()
			if bad <= 2:
				log(f"  (consultation {n} laissée en brouillon : {str(e)[:120]})")
	return f"{ok} validées, {bad} en brouillon"


@step("hospitalisation")
def hospitalisation():
	from healthcare.healthcare.doctype.inpatient_record.inpatient_record import admit_patient

	if frappe.db.count("Inpatient Record"):
		return "déjà chargé"
	pats = _patients()
	prac = _praticiens()[0]
	lits = frappe.get_all("Healthcare Service Unit", filters={"service_unit_type": "Chambre d'hospitalisation"}, pluck="name")
	n = 0
	for pat, lit, jours in ((pats[2], lits[0], 3), (pats[9], lits[1], 1)):
		rec = frappe.get_doc(
			{
				"doctype": "Inpatient Record",
				"patient": pat.name,
				"company": company(),
				"scheduled_date": add_days(today(), -jours),
				"admission_practitioner": prac.name,
				"expected_length_of_stay": jours + 2,
				"status": "Admission Scheduled",
			}
		)
		rec.insert(ignore_permissions=True)
		admit_patient(rec, lit, f"{add_days(today(), -jours)} 10:00:00", add_days(today(), 2))
		n += 1
	return f"{n} patients hospitalisés"


ROLES_DEMO = {
	"medecin": ("Dr Karim Benjelloun (démo)", ["Physician", "Nursing User", "Laboratory User"]),
	"reception": ("Réception (démo)", ["Healthcare Administrator", "Sales User", "Accounts User"]),
	"pharmacie": ("Pharmacie (démo)", ["Stock User", "Stock Manager", "Sales User"]),
	"compta": ("Comptabilité (démo)", ["Accounts Manager", "Accounts User"]),
}


@step("utilisateurs de démonstration")
def utilisateurs():
	import secrets

	lignes = []
	for cle, (nom, roles) in ROLES_DEMO.items():
		email = f"demo.{cle}@chtmed.ma"
		if frappe.db.exists("User", email):
			continue
		mdp = secrets.token_urlsafe(9)
		u = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": nom,
				"language": "fr",
				"send_welcome_email": 0,
				"new_password": mdp,
				"roles": [{"role": r} for r in roles],
			}
		)
		u.insert(ignore_permissions=True)
		lignes.append(f"{email}  {mdp}")
	if lignes:
		CTX["creds"] = lignes
		import os

		chemin = frappe.get_site_path("private", "demo_users.txt")
		os.makedirs(os.path.dirname(chemin), exist_ok=True)
		with open(chemin, "w") as f:
			f.write("\n".join(lignes) + "\n")
		os.chmod(chemin, 0o600)
		return f"{len(lignes)} comptes créés (identifiants dans {chemin})"
	return "déjà créés"


# Modules visibles par rôle (tous les autres sont masqués via un Module Profile).
# Core/Desk/Contacts/Email restent accessibles : profil utilisateur, ToDo, notifications.
BASE_MODULES = {"Core", "Desk", "Contacts", "Email", "Custom"}
PROFILS = {
	"medecin": ("Profil Médecin", {"Healthcare", "MedMa"}, "Cabinet médecin"),
	"reception": ("Profil Réception", {"Healthcare", "MedMa", "Accounts"}, "Réception"),
	"pharmacie": ("Profil Pharmacie", {"Healthcare", "Stock", "Selling"}, "Stock"),
	"compta": ("Profil Comptabilité", {"Accounts", "MedMa"}, "Accounting"),
}


@step("identifiants légaux fictifs de la société")
def identifiants_societe():
	c = company()
	frappe.db.set_value(
		"Company",
		c,
		{
			"ice": "000000000000000",
			"identifiant_fiscal": "00000000",
			"registre_commerce": "000000",
			"patente": "00000000",
		},
		update_modified=False,
	)
	return "ICE/IF/RC/Patente fictifs (à remplacer par ceux du client)"


@step("profils par rôle (menus)")
def profils_modules():
	tous = set(frappe.get_all("Module Def", pluck="name"))
	res = []
	for cle, (nom_profil, autorises, accueil) in PROFILS.items():
		bloques = sorted(tous - autorises - BASE_MODULES)
		if frappe.db.exists("Module Profile", nom_profil):
			mp = frappe.get_doc("Module Profile", nom_profil)
		else:
			mp = frappe.get_doc({"doctype": "Module Profile", "module_profile_name": nom_profil})
		mp.set("block_modules", [{"module": m} for m in bloques])
		mp.save(ignore_permissions=True) if mp.name else mp.insert(ignore_permissions=True)
		email = f"demo.{cle}@chtmed.ma"
		if frappe.db.exists("User", email):
			u = frappe.get_doc("User", email)
			u.module_profile = nom_profil
			if frappe.db.exists("Workspace", accueil):
				u.default_workspace = accueil
			u.save(ignore_permissions=True)
			res.append(f"{cle}: {len(autorises)} modules visibles")
	return ", ".join(res)


def load_demo():
	"""Point d'entrée : bench --site <site> execute medma_ma.demo.load_demo"""
	frappe.flags.mute_emails = True
	from medma_ma.setup import ensure_custom_fields, seed_organismes

	ensure_custom_fields()
	seed_organismes()
	frappe.db.commit()
	for fn in (
		ref_data, service_units, consultation_items, practitioners, lab_templates, medications, stock, patients,
		parcours, resultats_labo, facturation, dossiers, corriger_prescriptions, valider_consultations, hospitalisation, utilisateurs, identifiants_societe, profils_modules,
	):
		fn()
	echecs = [m for m in LOG if m.startswith("FAIL")]
	print(f"\nTerminé : {len(LOG) - len(echecs)} étapes OK, {len(echecs)} en échec.")
	return echecs
