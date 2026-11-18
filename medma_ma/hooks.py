app_name = "medma_ma"
app_title = "MedMa"
app_publisher = "MedMa"
app_description = "Couche marocaine pour Frappe Health : CNSS, CNOPS, AMO, mutuelles"
app_email = "contact@chtmed.ma"
app_license = "mit"
required_apps = ["erpnext", "healthcare"]

after_install = "medma_ma.setup.after_install_and_migrate"
after_migrate = "medma_ma.setup.after_install_and_migrate"

doc_events = {
    "Sales Invoice": {"validate": "medma_ma.invoice.calculer_prise_en_charge"},
}

# Thème MedMa (couleurs, écran de connexion, logo)
app_include_css = "/assets/medma_ma/css/medma.css"
web_include_css = "/assets/medma_ma/css/medma.css"
app_logo_url = "/assets/medma_ma/images/medma-logo.svg"
add_to_apps_screen = [
    {"name": "medma_ma", "logo": "/assets/medma_ma/images/medma-logo.svg", "title": "MedMa", "route": "/app/cabinet-medecin"}
]
