from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
    "Sales Invoice": [
        {"fieldname": "section_prise_en_charge", "label": "Prise en charge (CNSS / AMO / mutuelle)",
         "fieldtype": "Section Break", "insert_after": "patient_name", "collapsible": 1},
        {"fieldname": "couverture_patient", "label": "Couverture du patient", "fieldtype": "Link",
         "options": "Couverture Patient", "insert_after": "section_prise_en_charge"},
        {"fieldname": "organisme_payeur", "label": "Organisme payeur", "fieldtype": "Link",
         "options": "Organisme Payeur", "read_only": 1, "insert_after": "couverture_patient"},
        {"fieldname": "col_prise_en_charge", "fieldtype": "Column Break", "insert_after": "organisme_payeur"},
        {"fieldname": "taux_prise_en_charge", "label": "Taux de prise en charge (%)", "fieldtype": "Percent",
         "read_only": 1, "insert_after": "col_prise_en_charge"},
        {"fieldname": "part_organisme", "label": "Part organisme", "fieldtype": "Currency",
         "read_only": 1, "insert_after": "taux_prise_en_charge"},
        {"fieldname": "part_patient", "label": "Part patient", "fieldtype": "Currency",
         "read_only": 1, "insert_after": "part_organisme"},
    ]
}


def ensure_custom_fields():
    create_custom_fields(CUSTOM_FIELDS, update=True)


# Jurisdictions and bodies that exist in Morocco. Rates are placeholders to be confirmed per contract/tariff:
# 70% is the usual public AMO reimbursement level; private insurers and mutuelles vary by policy, so they start at 0.
ORGANISMES = [
    ("CNSS", "CNSS", 70),
    ("CNOPS", "CNOPS", 70),
    ("AMO Tadamon", "AMO Tadamon", 70),
    ("MGPAP", "Mutuelle", 0),
    ("CMIM", "Mutuelle", 0),
    ("Wafa Assurance", "Assurance privée", 0),
    ("RMA", "Assurance privée", 0),
    ("AXA Assurance Maroc", "Assurance privée", 0),
    ("Saham Assurance", "Assurance privée", 0),
    ("AtlantaSanad", "Assurance privée", 0),
    ("Allianz Maroc", "Assurance privée", 0),
]


def seed_organismes():
    import frappe

    for nom, type_organisme, taux in ORGANISMES:
        if frappe.db.exists("Organisme Payeur", nom):
            continue
        frappe.get_doc(
            {"doctype": "Organisme Payeur", "organisme_name": nom, "type_organisme": type_organisme, "taux_defaut": taux}
        ).insert(ignore_permissions=True)


def after_install_and_migrate():
    ensure_custom_fields()
    seed_organismes()
