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
