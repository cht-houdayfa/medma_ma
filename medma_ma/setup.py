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
         "options": "À prélever\nPrélevé - en attente du résultat\nRésultat validé", "default": "À prélever", "read_only": 1,
         "in_standard_filter": 1, "allow_on_submit": 1, "insert_after": "section_prelevement"},
        {"fieldname": "date_prelevement", "label": "Date et heure du prélèvement", "fieldtype": "Datetime",
         "read_only": 1, "allow_on_submit": 1, "insert_after": "etat_prelevement"},
        {"fieldname": "preleve_par", "label": "Prélevé par", "fieldtype": "Link", "options": "User",
         "read_only": 1, "allow_on_submit": 1, "insert_after": "date_prelevement"},
    ],
    "Patient Encounter": [
        {"fieldname": "allergie_confirmee", "label": "Prescrire malgré l'allergie signalée", "fieldtype": "Check",
         "insert_after": "drug_prescription", "description": "À cocher seulement après avoir pesé le risque d'allergie"},
    ],
    "Patient": [
        {"fieldname": "allergies_connues", "label": "Allergies connues (liste structurée)", "fieldtype": "Table",
         "options": "Allergie Patient", "insert_after": "allergies"},
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
    ensure_permissions_pharmacie()
    ensure_unites_urgences()
    ensure_permissions_urgences()
    ensure_fuseau()
    ensure_titres_liens()
    ensure_titres_rendez_vous()
    ensure_devise()
    ensure_identifiant_patient()
    ensure_patient_sans_compte()
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
    "Urgences en attente": ("Passage Urgences", [["Passage Urgences", "statut", "=", "En attente"]]),
    "Urgences en cours": (
        "Passage Urgences",
        [["Passage Urgences", "statut", "in", ["En cours de soins", "En observation"]]]),
    "Urgences vitales en cours": (
        "Passage Urgences",
        [["Passage Urgences", "statut", "!=", "Terminé"],
         ["Passage Urgences", "niveau_triage", "in", ["1 - Détresse vitale", "2 - Très urgent"]]]),
    "Passages urgences du jour": (
        "Passage Urgences", [["Passage Urgences", "date_arrivee", "Timespan", "today"]]),
    "Lits d'urgence libres": (
        "Healthcare Service Unit",
        [["Healthcare Service Unit", "service_unit_type", "=", "Box d'urgence"],
         ["Healthcare Service Unit", "occupancy_status", "=", "Vacant"]]),
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
        "actions": [
            ("Nouveau patient", "/app/patient/new"),
            ("Nouveau rendez-vous", "/app/patient-appointment/new"),
            ("Nouvelle facture", "/app/sales-invoice/new"),
        ],
        "rapports": ["Rendez-vous du jour (liste)"],
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
        "name": "Urgences",
        "module": "Healthcare",
        "icon": "alert-triangle",
        "roles": ["Physician", "Nursing User", "Healthcare Administrator", "System Manager"],
        "cartes": ["Urgences en attente", "Urgences en cours", "Urgences vitales en cours", "Lits d'urgence libres"],
        "titre": "Service des urgences",
        "actions": [("Nouveau passage aux urgences", "/app/passage-urgences/new"),
                    ("Lits d'urgence", "/app/healthcare-service-unit?service_unit_type=Box%20d%27urgence")],
        "rapports": ["File d'attente des urgences"],
        "raccourcis": [
            ("Passages aux urgences", "Passage Urgences"),
            ("Résumés de sortie", "Resume Sortie"),
            ("Patients", "Patient"),
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
        "roles": ["Healthcare Administrator", "Accounts Manager", "Accounts User", "System Manager"],
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
    from medma_ma.features import ensure_rapport_rdv_jour

    ensure_rapport_rdv_jour()
    for spec in ESPACES:
        content = [{"id": "h", "type": "header", "data": {"text": f'<span class="h4"><b>{spec["titre"]}</b></span>', "col": 12}}]
        col_carte = {1: 4, 2: 6, 3: 4, 4: 3}.get(len(spec["cartes"]), 4)
        content += [{"id": f"c{i}", "type": "number_card", "data": {"number_card_name": c, "col": col_carte}} for i, c in enumerate(spec["cartes"])]
        actions = spec.get("actions", [])
        rapports = spec.get("rapports", [])
        if actions:
            content += [{"id": "ha", "type": "header", "data": {"text": '<span class="h5"><b>Actions rapides</b></span>', "col": 12}}]
            content += [{"id": f"a{i}", "type": "shortcut", "data": {"shortcut_name": lab, "col": 3}} for i, (lab, _) in enumerate(actions)]
        if rapports:
            content += [{"id": f"r{i}", "type": "shortcut", "data": {"shortcut_name": lab, "col": 3}} for i, lab in enumerate(rapports)]
        content += [{"id": "hr", "type": "header", "data": {"text": '<span class="h5"><b>Dossiers</b></span>', "col": 12}}]
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
        raccourcis = [{"label": lab, "type": "URL", "url": url, "color": "green"} for lab, url in spec.get("actions", [])]
        raccourcis += [{"label": lab, "type": "Report", "link_to": lab, "is_query_report": 1} for lab in spec.get("rapports", [])]
        raccourcis += [{"label": lab, "type": "DocType", "link_to": dt, "doc_view": "List"} for lab, dt in spec["raccourcis"]]
        ws.set("shortcuts", raccourcis)
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
        # Healthcare natif (tous les écrans) : l'administration technique seulement ; chaque métier a son espace
        "Healthcare": ["System Manager"],
        # Comptabilité complète : le comptable et la direction ; la réception facture depuis son espace
        "Accounting": ["Accounts Manager", "System Manager"],
        "Payables": ["Accounts Manager", "System Manager"],
        "Receivables": ["Accounts Manager", "System Manager"],
        "Financial Reports": ["Accounts Manager", "System Manager"],
        # Ventes : inutile à la pharmacie et à la réception
        "Selling": ["Sales Manager", "System Manager"],
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


def ensure_permissions_pharmacie():
    """La pharmacie délivre sur ordonnance : elle doit lire les prescriptions (Medication Request), le catalogue
    des médicaments et le nom du patient. Lecture seule : aucune modification du dossier médical."""
    import frappe
    from frappe.permissions import add_permission, update_permission_property

    role = "Stock User"
    for dt in ("Medication Request", "Medication", "Patient", "Code Value"):
        if not frappe.db.exists("Custom DocPerm", {"parent": dt, "role": role, "permlevel": 0}):
            add_permission(dt, role, 0, "read")
        for droit in ("read", "print", "report"):
            update_permission_property(dt, role, 0, droit, 1)
        frappe.clear_cache(doctype=dt)


def ensure_unites_urgences():
    """Crée (une seule fois) le type « Box d'urgence » et quatre boxes sous un groupe « Urgences »."""
    import frappe

    if not frappe.db.exists("Healthcare Service Unit Type", "Box d'urgence"):
        frappe.get_doc({"doctype": "Healthcare Service Unit Type", "service_unit_type": "Box d'urgence",
                        "inpatient_occupancy": 1, "allow_appointments": 0, "is_billable": 0}).insert(ignore_permissions=True)
    company = frappe.db.get_value("Company", {}, "name")
    racine = frappe.db.get_value("Healthcare Service Unit", {"is_group": 1, "parent_healthcare_service_unit": ["is", "not set"], "company": company}, "name")
    if not racine:
        return
    groupe = frappe.db.get_value("Healthcare Service Unit", {"healthcare_service_unit_name": "Urgences", "is_group": 1}, "name")
    if not groupe:
        groupe = frappe.get_doc({"doctype": "Healthcare Service Unit", "healthcare_service_unit_name": "Urgences", "is_group": 1,
                                 "parent_healthcare_service_unit": racine, "company": company}).insert(ignore_permissions=True).name
    for n in range(1, 5):
        nom = f"Box urgences {n}"
        if not frappe.db.exists("Healthcare Service Unit", {"healthcare_service_unit_name": nom}):
            frappe.get_doc({"doctype": "Healthcare Service Unit", "healthcare_service_unit_name": nom, "is_group": 0,
                            "service_unit_type": "Box d'urgence", "parent_healthcare_service_unit": groupe, "company": company,
                            "inpatient_occupancy": 1}).insert(ignore_permissions=True)


def ensure_permissions_urgences():
    """Les urgences accueillent tout patient : l'infirmier de tri, le médecin et la réception doivent trouver le patient
    et le médecin d'astreinte. Lecture seule : le dossier médical n'est pas ouvert."""
    import frappe
    from frappe.permissions import add_permission, update_permission_property

    for role, dts in {"Nursing User": ("Patient", "Healthcare Practitioner", "Healthcare Service Unit"),
                      "Physician": ("Patient", "Healthcare Practitioner", "Healthcare Service Unit"),
                      "Healthcare Administrator": ("Healthcare Service Unit",)}.items():
        for dt in dts:
            if not frappe.db.exists("Custom DocPerm", {"parent": dt, "role": role, "permlevel": 0}) and not any(
                p.role == role and p.read for p in frappe.get_meta(dt).permissions
            ):
                add_permission(dt, role, 0, "read")
                update_permission_property(dt, role, 0, "read", 1)
            frappe.clear_cache(doctype=dt)


def ensure_fuseau():
    """Le Maroc vit à UTC+1 toute l'année (sauf le mois de Ramadan). La base de fuseaux de Python donne UTC+0 pour
    « Africa/Casablanca » en dehors des années passées : les heures et les cartes « du jour » avaient 1 h de retard.
    « Africa/Algiers » est fixe à UTC+1 et correspond à l'heure marocaine hors Ramadan."""
    import frappe

    if frappe.db.get_single_value("System Settings", "time_zone") != "Africa/Algiers":
        frappe.db.set_single_value("System Settings", "time_zone", "Africa/Algiers")
        frappe.clear_cache()
    # le fuseau personnel des utilisateurs s'affiche sous chaque champ date-heure : il doit être le même
    frappe.db.sql("update tabUser set time_zone = 'Africa/Algiers' where time_zone is not null and time_zone != 'Africa/Algiers'")


def ensure_titres_liens():
    """Les identifiants patient sont des numéros (HLC-PAT-2026-00001) : dans les champs de liaison (urgences, rendez-vous,
    factures...) on affiche le nom du patient et du praticien, pas leur numéro."""
    import frappe
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter

    for dt in ("Patient", "Healthcare Practitioner"):
        if not frappe.get_meta(dt).show_title_field_in_link:
            make_property_setter(dt, None, "show_title_field_in_link", "1", "Check", for_doctype=True)
            frappe.clear_cache(doctype=dt)


def ensure_titres_rendez_vous():
    """Le titre d'un rendez-vous (colonne « Titre » des listes) doit être « Patient avec Praticien », pas son numéro
    ni « with » en anglais. Corrige aussi les rendez-vous créés avant la traduction."""
    import frappe

    frappe.db.sql(
        """update `tabPatient Appointment`
           set title = concat(ifnull(patient_name, patient), ' avec ', ifnull(practitioner_name, practitioner))
           where (title is null or title = '' or title = name or title like '% with %')
             and (practitioner_name is not null or practitioner is not null)""")


def ensure_identifiant_patient():
    """Identifiant du patient : un numéro de série (HLC-PAT-2026-00001), pas son nom. Deux patients homonymes
    ne se distinguaient que par un suffixe « - 1 ». Ne concerne que les nouveaux patients."""
    import frappe

    if frappe.db.get_single_value("Healthcare Settings", "patient_name_by") != "Naming Series":
        frappe.db.set_single_value("Healthcare Settings", "patient_name_by", "Naming Series")
        frappe.clear_cache(doctype="Healthcare Settings")


def ensure_devise():
    """ERPNext affiche « د.م. » après chaque montant, même en français : on affiche « MAD », lisible partout."""
    import frappe

    if frappe.db.exists("Currency", "MAD") and frappe.db.get_value("Currency", "MAD", "symbol") != "MAD":
        frappe.db.set_value("Currency", "MAD", "symbol", "MAD")
        frappe.clear_cache()


def ensure_patient_sans_compte():
    """Healthcare coche « Inviter en tant qu'Utilisateur » par défaut : chaque nouveau patient créerait un compte
    et enverrait un e-mail. À la clinique, on ne le fait que sur demande."""
    import frappe

    if frappe.db.get_value("DocField", {"parent": "Patient", "fieldname": "invite_user"}, "default") in (None, "", "0"):
        return
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter

    make_property_setter("Patient", "invite_user", "default", "0", "Data")
    frappe.clear_cache(doctype="Patient")


def _initialiser_prelevements():
    """Les analyses déjà créées avant l'ajout du champ sont considérées « à prélever » tant qu'elles sont en brouillon."""
    import frappe

    frappe.db.sql(
        "update `tabLab Test` set etat_prelevement = 'À prélever' "
        "where docstatus = 0 and (etat_prelevement is null or etat_prelevement = '')"
    )
