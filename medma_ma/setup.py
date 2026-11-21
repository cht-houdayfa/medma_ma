from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
    "Company": [
        {"fieldname": "section_ids_maroc", "label": "Identifiants légaux (Maroc)", "fieldtype": "Section Break",
         "insert_after": "company_name", "collapsible": 1},
        {"fieldname": "ice", "label": "ICE", "fieldtype": "Data", "insert_after": "section_ids_maroc"},
        {"fieldname": "identifiant_fiscal", "label": "IF (identifiant fiscal)", "fieldtype": "Data", "insert_after": "ice"},
        {"fieldname": "registre_commerce", "label": "RC (registre de commerce)", "fieldtype": "Data", "insert_after": "identifiant_fiscal"},
        {"fieldname": "patente", "label": "Patente", "fieldtype": "Data", "insert_after": "registre_commerce"},
    ],
    "Lab Test": [
        {"fieldname": "section_prelevement", "label": "Prélèvement", "fieldtype": "Section Break",
         "insert_after": "company"},
        {"fieldname": "etat_prelevement", "label": "État du prélèvement", "fieldtype": "Select",
         "options": "À prélever\nPrélevé - en attente du résultat", "default": "À prélever", "read_only": 1,
         "in_standard_filter": 1, "allow_on_submit": 1, "insert_after": "section_prelevement"},
        {"fieldname": "date_prelevement", "label": "Date et heure du prélèvement", "fieldtype": "Datetime",
         "read_only": 1, "allow_on_submit": 1, "insert_after": "etat_prelevement"},
        {"fieldname": "preleve_par", "label": "Prélevé par", "fieldtype": "Link", "options": "User",
         "read_only": 1, "allow_on_submit": 1, "insert_after": "date_prelevement"},
    ],
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
    _initialiser_prelevements()
    seed_organismes()
    ensure_workspaces()
    from medma_ma.features import ensure_all

    ensure_all()
    ensure_permissions()
    ensure_permissions_reception()
    restreindre_espaces_admin()


CARTES = {
    "Rendez-vous du jour": (
        "Patient Appointment",
        [["Patient Appointment", "status", "in", ["Scheduled", "Open", "Confirmed", "Checked In"]], ["Patient Appointment", "appointment_date", "Timespan", "today"]],
    ),
    # le réceptionniste clique « Patient arrivé » : le patient passe dans cette file, visible par le médecin
    "Patients en salle d'attente": (
        "Patient Appointment",
        [["Patient Appointment", "status", "=", "Checked In"], ["Patient Appointment", "appointment_date", "Timespan", "today"]],
    ),
    "Médicaments en stock bas": ("Bin", [["Bin", "actual_qty", "<", 50]]),
    "Rendez-vous à venir": ("Patient Appointment", [["Patient Appointment", "status", "=", "Scheduled"]]),
    "Patients hospitalisés": ("Inpatient Record", [["Inpatient Record", "status", "=", "Admitted"]]),
    "Analyses à valider": ("Lab Test", [["Lab Test", "docstatus", "=", 0]]),
    "Prélèvements à faire": (
        "Lab Test", [["Lab Test", "docstatus", "=", 0], ["Lab Test", "etat_prelevement", "=", "À prélever"]]),
    "Résultats en attente": (
        "Lab Test",
        [["Lab Test", "docstatus", "=", 0], ["Lab Test", "etat_prelevement", "=", "Prélevé - en attente du résultat"]]),
    "Factures non soldées": (
        "Sales Invoice",
        [["Sales Invoice", "docstatus", "=", 1], ["Sales Invoice", "outstanding_amount", ">", 0]],
    ),
}

ESPACES = [
    {
        "name": "Cabinet médecin",
        "module": "Healthcare",
        "icon": "stethoscope",
        "roles": ["Physician", "System Manager"],
        "cartes": ["Patients en salle d'attente", "Rendez-vous du jour", "Analyses à valider", "Patients hospitalisés"],
        "titre": "Mon cabinet",
        "raccourcis": [
            ("Patients", "Patient"),
            ("Rendez-vous", "Patient Appointment"),
            ("Consultations", "Patient Encounter"),
            ("Certificats médicaux", "Certificat Medical"),
            ("Analyses", "Lab Test"),
            ("Constantes", "Vital Signs"),
            ("Hospitalisations", "Inpatient Record"),
            ("Médicaments", "Medication"),
        ],
    },
    {
        "name": "Réception",
        "module": "Healthcare",
        "icon": "users",
        "roles": ["Healthcare Administrator", "Accounts User", "System Manager"],
        "cartes": ["Patients en salle d'attente", "Rendez-vous du jour", "Rendez-vous à venir", "Factures non soldées"],
        "titre": "Accueil et facturation",
        "raccourcis": [
            ("Patients", "Patient"),
            ("Rendez-vous", "Patient Appointment"),
            ("Factures", "Sales Invoice"),
            ("Paiements", "Payment Entry"),
            ("Couvertures patient", "Couverture Patient"),
            ("Certificats médicaux", "Certificat Medical"),
        ],
    },
    {
        "name": "Soins infirmiers",
        "module": "Healthcare",
        "icon": "heart",
        "roles": ["Nursing User", "System Manager"],
        "cartes": ["Patients en salle d'attente", "Rendez-vous du jour", "Patients hospitalisés"],
        "titre": "Soins et hospitalisation",
        "raccourcis": [
            ("Patients", "Patient"),
            ("Constantes", "Vital Signs"),
            ("Hospitalisations", "Inpatient Record"),
            ("Rendez-vous", "Patient Appointment"),
            ("Consultations", "Patient Encounter"),
        ],
    },
    {
        "name": "Laboratoire",
        "module": "Healthcare",
        "icon": "flask",
        "roles": ["Laboratory User", "System Manager"],
        "cartes": ["Prélèvements à faire", "Résultats en attente", "Analyses à valider"],
        "titre": "Analyses et résultats",
        "raccourcis": [
            ("Analyses", "Lab Test"),
            ("Patients", "Patient"),
            ("Modèles d'analyse", "Lab Test Template"),
        ],
    },
    {
        "name": "Pharmacie",
        "module": "Stock",
        "icon": "pill",
        "roles": ["Stock User", "Stock Manager", "Healthcare Administrator", "System Manager"],
        "cartes": ["Médicaments en stock bas"],
        "titre": "Pharmacie et stock",
        "raccourcis": [
            ("Médicaments (articles)", "Item"),
            ("Mouvements de stock", "Stock Entry"),
            ("Niveaux de stock", "Bin"),
            ("Prescriptions", "Medication Request"),
            ("Patients", "Patient"),
        ],
    },
    {
        "name": "MedMa",
        "module": "MedMa",
        "icon": "heart",
        "roles": [],
        "cartes": [],
        "titre": "Prise en charge et remboursements",
        "raccourcis": [
            ("Organismes payeurs", "Organisme Payeur"),
            ("Couvertures patient", "Couverture Patient"),
            ("Dossiers de remboursement", "Dossier Remboursement"),
        ],
    },
]


def _ensure_cartes():
    import json

    import frappe

    for label, (dt, filtres) in CARTES.items():
        if frappe.db.exists("Number Card", label):
            nc = frappe.get_doc("Number Card", label)
            nc.filters_json = json.dumps(filtres)
            nc.dynamic_filters_json = None
            nc.save(ignore_permissions=True)
            continue
        frappe.get_doc(
            {
                "doctype": "Number Card",
                "name": label,
                "label": label,
                "type": "Document Type",
                "document_type": dt,
                "function": "Count",
                "is_public": 1,
                "show_percentage_stats": 0,
                "filters_json": json.dumps(filtres),
            }
        ).insert(ignore_permissions=True)


def ensure_workspaces():
    """Crée ou met à jour les espaces de travail MedMa (idempotent : rejoué à chaque migration)."""
    import json

    import frappe

    _ensure_cartes()
    for spec in ESPACES:
        content = [{"id": "h", "type": "header", "data": {"text": f'<span class="h4"><b>{spec["titre"]}</b></span>', "col": 12}}]
        content += [{"id": f"c{i}", "type": "number_card", "data": {"number_card_name": c, "col": 4}} for i, c in enumerate(spec["cartes"])]
        content += [{"id": f"s{i}", "type": "shortcut", "data": {"shortcut_name": lab, "col": 3}} for i, (lab, _) in enumerate(spec["raccourcis"])]
        valeurs = {
            "label": spec["name"],
            "title": spec["name"],
            "module": spec["module"],
            "public": 1,
            "is_hidden": 0,
            "icon": spec["icon"],
            "content": json.dumps(content),
        }
        if frappe.db.exists("Workspace", spec["name"]):
            ws = frappe.get_doc("Workspace", spec["name"])
            ws.update(valeurs)
        else:
            ws = frappe.get_doc({"doctype": "Workspace", "name": spec["name"], **valeurs})
        ws.set("shortcuts", [{"label": lab, "type": "DocType", "link_to": dt, "doc_view": "List"} for lab, dt in spec["raccourcis"]])
        ws.set("number_cards", [{"number_card_name": c, "label": c} for c in spec["cartes"]])
        ws.set("roles", [{"role": r} for r in spec["roles"]])
        ws.save(ignore_permissions=True) if ws.get("creation") else ws.insert(ignore_permissions=True)


def ensure_workspace():
    ensure_workspaces()


def restreindre_espaces_admin():
    """Espaces non métier réservés à l'administration. Users/Build (module Core) ne se bloquent pas par profil de modules ;
    l'espace Healthcare complet est réservé aux administrateurs, les médecins ayant leur espace « Cabinet médecin »."""
    import frappe

    restrictions = {
        "Users": ["System Manager"],
        "Build": ["System Manager"],
        "Healthcare": ["Healthcare Administrator", "System Manager"],
    }
    for nom, roles in restrictions.items():
        if not frappe.db.exists("Workspace", nom):
            continue
        ws = frappe.get_doc("Workspace", nom)
        if sorted(r.role for r in ws.roles) != sorted(roles):
            ws.set("roles", [{"role": r} for r in roles])
            ws.save(ignore_permissions=True)


def ensure_permissions():
    """Le formulaire de rendez-vous de Healthcare lit « Healthcare Settings » pour tout utilisateur : sans droit de lecture,
    chaque médecin voit « Pas d'autorisation ». Lecture seule uniquement (aucune écriture)."""
    import frappe
    from frappe.permissions import add_permission

    for role in ("Physician", "Nursing User", "Laboratory User", "Accounts User"):
        existe = frappe.db.exists("Custom DocPerm", {"parent": "Healthcare Settings", "role": role, "permlevel": 0})
        if not existe:
            add_permission("Healthcare Settings", role, 0, "read")
    frappe.clear_cache(doctype="Healthcare Settings")

    # Listes de choix de la consultation : le médecin sélectionne médicaments et analyses dans les catalogues (lecture seule).
    catalogues = {
        "Medication": ("Physician", "Nursing User", "Laboratory User"),
        "Lab Test Template": ("Physician", "Nursing User"),
        "Observation Template": ("Physician", "Nursing User", "Laboratory User"),
        "Nursing Checklist Template": ("Physician",),
    }
    for dt, roles in catalogues.items():
        for role in roles:
            if not frappe.db.exists("Custom DocPerm", {"parent": dt, "role": role, "permlevel": 0}):
                add_permission(dt, role, 0, "read")
        frappe.clear_cache(doctype=dt)


def ensure_permissions_reception():
    """La réception inscrit les patients et choisit le praticien du rendez-vous. Healthcare ne donne au rôle
    « Healthcare Administrator » aucun droit sur Patient : sans cela, « Pas permis » à la création d'un rendez-vous.
    Le dossier médical (consultations, constantes) reste réservé aux soignants : on n'ouvre que Patient et Praticien."""
    import frappe
    from frappe.permissions import add_permission, update_permission_property

    role = "Healthcare Administrator"
    for dt, droits in {"Patient": ("read", "write", "create", "print", "email", "export", "share", "report"),
                       "Healthcare Practitioner": ("read",)}.items():
        if not frappe.db.exists("Custom DocPerm", {"parent": dt, "role": role, "permlevel": 0}):
            add_permission(dt, role, 0, "read")
        for droit in droits:
            update_permission_property(dt, role, 0, droit, 1)
        frappe.clear_cache(doctype=dt)


def _initialiser_prelevements():
    """Les analyses déjà créées avant l'ajout du champ sont considérées « à prélever » tant qu'elles sont en brouillon."""
    import frappe

    frappe.db.sql(
        "update `tabLab Test` set etat_prelevement = 'À prélever' "
        "where docstatus = 0 and (etat_prelevement is null or etat_prelevement = '')"
    )
