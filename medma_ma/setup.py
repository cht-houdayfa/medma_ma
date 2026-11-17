from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
    "Patient": [
        {"fieldname": "cin", "label": "CIN (carte d'identité nationale)", "fieldtype": "Data",
         "insert_after": "sex", "unique": 0, "in_standard_filter": 1},
    ],
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
    ensure_workspace()
    restreindre_espaces_admin()


def ensure_workspace():
    """Espace de travail MedMa : accès rapide aux organismes, couvertures et dossiers de remboursement."""
    import json

    import frappe

    if frappe.db.exists("Workspace", "MedMa"):
        return
    raccourcis = [
        ("Organismes payeurs", "Organisme Payeur"),
        ("Couvertures patient", "Couverture Patient"),
        ("Dossiers de remboursement", "Dossier Remboursement"),
    ]
    content = [
        {"id": "medma-h", "type": "header", "data": {"text": '<span class="h4"><b>Prise en charge et remboursements</b></span>', "col": 12}}
    ] + [
        {"id": f"medma-s{i}", "type": "shortcut", "data": {"shortcut_name": lab, "col": 4}}
        for i, (lab, _) in enumerate(raccourcis)
    ]
    frappe.get_doc(
        {
            "doctype": "Workspace",
            "name": "MedMa",
            "label": "MedMa",
            "title": "MedMa",
            "module": "MedMa",
            "public": 1,
            "is_hidden": 0,
            "icon": "heart",
            "content": json.dumps(content),
            "shortcuts": [{"label": lab, "type": "DocType", "link_to": dt, "doc_view": "List"} for lab, dt in raccourcis],
        }
    ).insert(ignore_permissions=True)


def restreindre_espaces_admin():
    """Les espaces Users et Build (module Core) ne se bloquent pas par profil : réservés au Gestionnaire système."""
    import frappe

    for nom in ("Users", "Build"):
        if not frappe.db.exists("Workspace", nom):
            continue
        ws = frappe.get_doc("Workspace", nom)
        if [r.role for r in ws.roles] != ["System Manager"]:
            ws.set("roles", [{"role": "System Manager"}])
            ws.save(ignore_permissions=True)
