app_name = "medma_ma"
app_title = "MedMa"
app_publisher = "MedMa"
app_description = "Couche marocaine pour Frappe Health : CNSS, CNOPS, AMO, mutuelles"
app_email = "contact@chtmed.ma"
app_license = "gpl-3.0"
required_apps = ["erpnext", "healthcare"]

after_install = "medma_ma.setup.after_install_and_migrate"
after_migrate = "medma_ma.setup.after_install_and_migrate"

doc_events = {
    "Sales Invoice": {"validate": "medma_ma.invoice.calculer_prise_en_charge"},
    "Patient": {"validate": "medma_ma.patient.verifier_cin"},
    "Patient Encounter": {"validate": ["medma_ma.allergies.verifier_prescription", "medma_ma.allergies.verifier_interactions"]},
    "Service Request": {"on_submit": "medma_ma.laboratoire.creer_analyse_depuis_demande"},
    "Lab Test": {"on_submit": "medma_ma.laboratoire.marquer_resultat_valide"},
}

# Thème MedMa (couleurs, écran de connexion, logo)
app_include_css = "/assets/medma_ma/css/medma.css"
web_include_css = "/assets/medma_ma/css/medma.css"
app_logo_url = "/assets/medma_ma/images/medma-logo.svg"
add_to_apps_screen = [
    {"name": "medma_ma", "logo": "/assets/medma_ma/images/medma-logo.svg", "title": "MedMa", "route": "/app/cabinet-médecin"}
]

override_doctype_class = {
    "Patient Encounter": "medma_ma.overrides.PatientEncounterMedMa",
}

# Portail patient : pas de formulaire de création (la prise de rendez-vous en ligne n'est pas proposée)
website_redirects = [
	{"source": "/patient-appointments/new", "target": "/patient-appointments"},
	{"source": "/lab-test/new", "target": "/lab-test"},
	{"source": "/prescription/new", "target": "/prescription"},
]
