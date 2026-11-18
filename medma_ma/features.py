"""Fonctionnalités MedMa créées en base à l'installation et à chaque migration (idempotent) :
formats d'impression, tableau de bord, rapport de créances par organisme, rappel WhatsApp."""

import json
import os
import re

import frappe

TPL_DIR = os.path.join(os.path.dirname(__file__), "print_templates")


def _lire(nom):
	with open(os.path.join(TPL_DIR, nom), encoding="utf-8") as f:
		return f.read()


def _composer(nom):
	"""Les formats d'impression sont stockés en base : on inline le style et la macro plutôt que d'utiliser include."""
	html = _lire(nom)
	html = html.replace('{% include "_style.html" %}', _lire("_style.html"))
	html = re.sub(r'\{% from "_entete_societe.html" import [^%]* %\}', lambda _m: _lire("_entete_societe.html"), html)
	return html


FORMATS = [
	("Ordonnance MedMa", "Patient Encounter", "ordonnance.html"),
	("Facture MedMa", "Sales Invoice", "facture.html"),
	("Bordereau MedMa", "Dossier Remboursement", "bordereau.html"),
]


def ensure_print_formats():
	for nom, dt, fichier in FORMATS:
		valeurs = {
			"doc_type": dt,
			"module": "MedMa",
			"standard": "No",
			"custom_format": 1,
			"print_format_type": "Jinja",
			"html": _composer(fichier),
			"disabled": 0,
			"font_size": 12,
		}
		if frappe.db.exists("Print Format", nom):
			pf = frappe.get_doc("Print Format", nom)
			pf.update(valeurs)
			pf.save(ignore_permissions=True)
		else:
			frappe.get_doc({"doctype": "Print Format", "name": nom, **valeurs}).insert(ignore_permissions=True)
		# format par défaut du type de document
		frappe.make_property_setter(
			{"doctype": dt, "doctype_or_field": "DocType", "property": "default_print_format", "value": nom, "property_type": "Data"},
			validate_fields_for_doctype=False,
		)


# ------------------------------------------------------------------ tableau de bord

CARTES_BORD = {
	"Chiffre d'affaires facturé": {
		"document_type": "Sales Invoice",
		"function": "Sum",
		"aggregate_function_based_on": "grand_total",
		"filters_json": [["Sales Invoice", "docstatus", "=", 1]],
	},
	"Créances ouvertes (MAD)": {
		"document_type": "Sales Invoice",
		"function": "Sum",
		"aggregate_function_based_on": "outstanding_amount",
		"filters_json": [["Sales Invoice", "docstatus", "=", 1]],
	},
	"Factures émises": {"document_type": "Sales Invoice", "function": "Count", "filters_json": [["Sales Invoice", "docstatus", "=", 1]]},
}

GRAPHIQUES = {
	"Chiffre d'affaires mensuel": {
		"chart_type": "Sum",
		"document_type": "Sales Invoice",
		"based_on": "posting_date",
		"value_based_on": "grand_total",
		"time_interval": "Monthly",
		"timespan": "Last Year",
		"timeseries": 1,
		"type": "Bar",
		"filters_json": json.dumps([["Sales Invoice", "docstatus", "=", 1]]),
		"color": "#0e7c66",
	},
	"Rendez-vous par praticien": {
		"chart_type": "Group By",
		"document_type": "Patient Appointment",
		"group_by_type": "Count",
		"group_by_based_on": "practitioner_name",
		"number_of_groups": 10,
		"timeseries": 0,
		"type": "Donut",
		"filters_json": json.dumps([]),
	},
	"Part des organismes (MAD)": {
		"chart_type": "Group By",
		"document_type": "Sales Invoice",
		"group_by_type": "Sum",
		"group_by_based_on": "organisme_payeur",
		"aggregate_function_based_on": "part_organisme",
		"number_of_groups": 10,
		"timeseries": 0,
		"type": "Bar",
		"filters_json": json.dumps([["Sales Invoice", "docstatus", "=", 1], ["Sales Invoice", "organisme_payeur", "is", "set"]]),
	},
}

REPORT_CREANCES = {
	"name": "Créances par organisme",
	# « À recouvrer » = part organisme facturée − montants effectivement payés d'après les dossiers de remboursement.
	"query": (
		"SELECT si.organisme_payeur AS `Organisme:Link/Organisme Payeur:200`, "
		"COUNT(*) AS `Factures:Int:90`, "
		"SUM(si.part_organisme) AS `Part organisme:Currency:140`, "
		"IFNULL(MAX(d.paye), 0) AS `Payé par l'organisme:Currency:160`, "
		"SUM(si.part_organisme) - IFNULL(MAX(d.paye), 0) AS `À recouvrer:Currency:140` "
		"FROM `tabSales Invoice` si "
		"LEFT JOIN (SELECT organisme, SUM(total_paye) AS paye FROM `tabDossier Remboursement` GROUP BY organisme) d "
		"ON d.organisme = si.organisme_payeur "
		"WHERE si.docstatus = 1 AND IFNULL(si.organisme_payeur, '') != '' "
		"GROUP BY si.organisme_payeur "
		"ORDER BY SUM(si.part_organisme) - IFNULL(MAX(d.paye), 0) DESC"
	),
}

ANCIENNES_CARTES = ["Chiffre d'affaires du mois", "Patients enregistrés"]


def ensure_dashboard():
	for label, spec in CARTES_BORD.items():
		valeurs = {
			"label": label,
			"type": "Document Type",
			"document_type": spec["document_type"],
			"function": spec["function"],
			"is_public": 1,
			"show_percentage_stats": 0,
			"filters_json": json.dumps(spec["filters_json"]),
		}
		if spec.get("aggregate_function_based_on"):
			valeurs["aggregate_function_based_on"] = spec["aggregate_function_based_on"]
		if frappe.db.exists("Number Card", label):
			nc = frappe.get_doc("Number Card", label)
			nc.update(valeurs)
			nc.save(ignore_permissions=True)
		else:
			frappe.get_doc({"doctype": "Number Card", "name": label, **valeurs}).insert(ignore_permissions=True)

	for nom, spec in GRAPHIQUES.items():
		valeurs = {"chart_name": nom, "is_public": 1, "is_custom": 0, **spec}
		if frappe.db.exists("Dashboard Chart", nom):
			ch = frappe.get_doc("Dashboard Chart", nom)
			ch.update(valeurs)
			ch.save(ignore_permissions=True)
		else:
			frappe.get_doc({"doctype": "Dashboard Chart", "name": nom, **valeurs}).insert(ignore_permissions=True)

	rep = REPORT_CREANCES
	valeurs = {
		"report_name": rep["name"],
		"ref_doctype": "Sales Invoice",
		"report_type": "Query Report",
		"is_standard": "No",
		"module": "MedMa",
		"query": rep["query"],
		"roles": [{"role": r} for r in ("Accounts Manager", "Accounts User", "Healthcare Administrator", "System Manager")],
	}
	if frappe.db.exists("Report", rep["name"]):
		r = frappe.get_doc("Report", rep["name"])
		r.update(valeurs)
		r.save(ignore_permissions=True)
	else:
		frappe.get_doc({"doctype": "Report", **valeurs}).insert(ignore_permissions=True)

	_workspace_bord()
	for ancien in ANCIENNES_CARTES:
		if frappe.db.exists("Number Card", ancien):
			frappe.delete_doc("Number Card", ancien, force=1, ignore_permissions=True)


def _workspace_bord():
	nom = "Tableau de bord"
	cartes = list(CARTES_BORD)
	graphs = list(GRAPHIQUES)
	content = [{"id": "h", "type": "header", "data": {"text": '<span class="h4"><b>Pilotage de l\'établissement</b></span>', "col": 12}}]
	content += [{"id": f"c{i}", "type": "number_card", "data": {"number_card_name": c, "col": 4}} for i, c in enumerate(cartes)]
	content += [{"id": f"g{i}", "type": "chart", "data": {"chart_name": g, "col": 6}} for i, g in enumerate(graphs)]
	content += [{"id": "r", "type": "shortcut", "data": {"shortcut_name": "Créances par organisme", "col": 4}}]
	valeurs = {
		"label": nom,
		"title": nom,
		"module": "MedMa",
		"public": 1,
		"is_hidden": 0,
		"icon": "chart",
		"content": json.dumps(content),
	}
	if frappe.db.exists("Workspace", nom):
		ws = frappe.get_doc("Workspace", nom)
		ws.update(valeurs)
	else:
		ws = frappe.get_doc({"doctype": "Workspace", "name": nom, **valeurs})
	ws.set("number_cards", [{"number_card_name": c, "label": c} for c in cartes])
	ws.set("charts", [{"chart_name": g, "label": g} for g in graphs])
	ws.set("shortcuts", [{"label": "Créances par organisme", "type": "Report", "link_to": REPORT_CREANCES["name"], "is_query_report": 1}])
	ws.set("roles", [{"role": r} for r in ("Accounts Manager", "Healthcare Administrator", "System Manager")])
	ws.save(ignore_permissions=True) if ws.get("creation") else ws.insert(ignore_permissions=True)


# ------------------------------------------------------------------ rappel WhatsApp (clic, sans API)

SCRIPT_WHATSAPP = """
frappe.ui.form.on('Patient Appointment', {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.patient || frm.doc.status === 'Closed' || frm.doc.status === 'Cancelled') return;
		frm.add_custom_button(__('Rappel WhatsApp'), () => {
			frappe.db.get_value('Patient', frm.doc.patient, 'mobile').then(r => {
				let tel = ((r.message && r.message.mobile) || '').replace(/\\D/g, '');
				if (!tel) { frappe.msgprint(__('Aucun numéro de mobile pour ce patient.')); return; }
				if (tel.startsWith('0')) tel = '212' + tel.slice(1);
				const date = frappe.datetime.str_to_user(frm.doc.appointment_date);
				const heure = (frm.doc.appointment_time || '').slice(0, 5);
				const msg =
					'Bonjour ' + (frm.doc.patient_name || '') + ', rappel de votre rendez-vous le ' + date + ' à ' + heure +
					' avec Dr ' + (frm.doc.practitioner_name || '') + '. En cas d\\'empêchement, merci de nous prévenir.' +
					'\\n\\nمرحبا، نذكركم بموعدكم يوم ' + date + ' على الساعة ' + heure + '.';
				window.open('https://wa.me/' + tel + '?text=' + encodeURIComponent(msg), '_blank');
			});
		}, __('Actions'));
	}
});
"""


def ensure_client_scripts():
	nom = "MedMa - Rappel WhatsApp"
	valeurs = {"dt": "Patient Appointment", "view": "Form", "enabled": 1, "script": SCRIPT_WHATSAPP}
	if frappe.db.exists("Client Script", nom):
		cs = frappe.get_doc("Client Script", nom)
		cs.update(valeurs)
		cs.save(ignore_permissions=True)
	else:
		frappe.get_doc({"doctype": "Client Script", "name": nom, **valeurs}).insert(ignore_permissions=True)


SCRIPT_DOSSIER = """
frappe.ui.form.on('Dossier Remboursement', {
	refresh(frm) {
		const brouillon = frm.is_new() || frm.doc.statut === 'Brouillon';
		if (brouillon) {
			frm.add_custom_button(__('Charger les factures'), () => {
				if (!frm.doc.organisme || !frm.doc.date_debut || !frm.doc.date_fin) {
					frappe.msgprint(__("Renseignez l'organisme et la période."));
					return;
				}
				frm.call('charger_factures').then(r => {
					frappe.show_alert({message: __('{0} facture(s) ajoutée(s)', [r.message]), indicator: 'green'});
					frm.refresh_field('factures');
					frm.dirty();
				});
			});
		}
		if (!frm.is_new() && frm.doc.statut === 'Brouillon' && (frm.doc.factures || []).length) {
			frm.add_custom_button(__('Marquer comme envoyé'), () => {
				frm.call('marquer_envoye').then(() => frm.reload_doc());
			}, __('Actions'));
		}
		if (!frm.is_new() && ['Envoyé', 'Payé partiellement'].includes(frm.doc.statut)) {
			frm.add_custom_button(__('Enregistrer un paiement'), () => {
				const reste = flt(frm.doc.total_reclame) - flt(frm.doc.total_paye);
				frappe.prompt([
					{fieldname: 'montant', label: __('Montant reçu (MAD)'), fieldtype: 'Currency', reqd: 1, default: reste},
					{fieldname: 'date_paiement', label: __('Date'), fieldtype: 'Date', reqd: 1, default: frappe.datetime.get_today()},
					{fieldname: 'reference', label: __('Référence du virement'), fieldtype: 'Data', reqd: 1}
				], v => {
					frm.call('enregistrer_paiement', v).then(() => frm.reload_doc());
				}, __("Paiement de l'organisme"), __('Enregistrer'));
			}, __('Actions'));
		}
	}
});
"""


def ensure_client_scripts_dossier():
	nom = "MedMa - Dossier de remboursement"
	valeurs = {"dt": "Dossier Remboursement", "view": "Form", "enabled": 1, "script": SCRIPT_DOSSIER}
	if frappe.db.exists("Client Script", nom):
		cs = frappe.get_doc("Client Script", nom)
		cs.update(valeurs)
		cs.save(ignore_permissions=True)
	else:
		frappe.get_doc({"doctype": "Client Script", "name": nom, **valeurs}).insert(ignore_permissions=True)


SCRIPT_COUVERTURE = """
frappe.ui.form.on('Couverture Patient', {
	organisme(frm) {
		if (!frm.doc.organisme) return;
		frappe.db.get_value('Organisme Payeur', frm.doc.organisme, 'taux_defaut').then(r => {
			frm.set_value('taux_prise_en_charge', (r.message && r.message.taux_defaut) || 0);
		});
	}
});
"""


def ensure_client_scripts_couverture():
	nom = "MedMa - Couverture patient"
	valeurs = {"dt": "Couverture Patient", "view": "Form", "enabled": 1, "script": SCRIPT_COUVERTURE}
	if frappe.db.exists("Client Script", nom):
		cs = frappe.get_doc("Client Script", nom)
		cs.update(valeurs)
		cs.save(ignore_permissions=True)
	else:
		frappe.get_doc({"doctype": "Client Script", "name": nom, **valeurs}).insert(ignore_permissions=True)


def ensure_all():
	ensure_print_formats()
	ensure_dashboard()
	ensure_client_scripts()
	ensure_client_scripts_dossier()
	ensure_client_scripts_couverture()
	ensure_branding()
	ensure_guide()
	ensure_portail()


# --- Thème et identité visuelle -------------------------------------------------------------------

LOGO = "/assets/medma_ma/images/medma-logo.svg"


def ensure_assets_link():
    """Expose public/ sous sites/assets/medma_ma (le volume `sites` masque ce que bench build fait dans l'image)."""
    import os

    cible = os.path.join(frappe.get_app_path("medma_ma"), "public")
    lien = os.path.join(frappe.get_site_path("..", "assets"), "medma_ma")
    if os.path.islink(lien) and os.path.realpath(lien) == os.path.realpath(cible):
        return
    if os.path.lexists(lien):
        os.remove(lien)
    os.symlink(cible, lien)


def ensure_branding():
    """Nom, logo et menus : l'utilisateur voit MedMa, pas les liens de support du framework."""
    ensure_assets_link()
    ws = frappe.get_single("Website Settings")
    ws.app_name = "MedMa"
    ws.app_logo = LOGO
    ws.splash_image = LOGO
    ws.favicon = LOGO
    ws.footer_powered = "MedMa — Gestion de cabinets et cliniques"
    ws.hide_footer_signup = 1
    ws.save(ignore_permissions=True)

    nav = frappe.get_single("Navbar Settings")
    nav.app_logo = LOGO
    # Menu d'aide : on garde uniquement ce qui est utile à un cabinet (pas de liens de support du framework).
    for ligne in nav.help_dropdown:
        ligne.hidden = 1
    nav.save(ignore_permissions=True)


# --- Guide de démonstration par rôle ----------------------------------------------------------------

GUIDE = [
    ("Médecin", "Espace « Cabinet médecin »",
     ["Rendez-vous du jour → ouvrir un patient → Consultation → ordonnance (marque + générique).",
      "Prescrire une analyse ; Imprimer → « Ordonnance MedMa » (PDF).",
      "Carte « Analyses à valider » : résultats en attente."]),
    ("Réception", "Espace « Réception »",
     ["Nouveau patient (CIN, couverture CNSS/CNOPS/AMO) ; prendre un rendez-vous.",
      "Facture : choisir la couverture, part organisme / part patient calculées seules ; Imprimer → « Facture MedMa ».",
      "Encaisser la part patient (Paiement)."]),
    ("Infirmier", "Espace « Soins infirmiers »",
     ["Prendre les constantes (tension, poids, température) d'un patient.",
      "Suivre les patients hospitalisés et les rendez-vous du jour."]),
    ("Laboratoire", "Espace « Laboratoire »",
     ["Carte « Analyses à valider » : saisir les résultats puis valider.",
      "Le résultat apparaît aussitôt dans le dossier du patient."]),
    ("Direction", "Espace « Tableau de bord »",
     ["Vue d'ensemble : chiffre d'affaires, créances, activité et accès à tous les modules métier."]),
    ("Patient (portail)", "Portail /lab-test, /prescription, /patient-appointments",
     ["Se connecter avec demo.patient : le patient ne voit que ses rendez-vous, analyses et ordonnances.",
      "Aucun accès au bureau, aux factures ni aux dossiers des autres patients."]),
    ("Pharmacie", "Espace « Pharmacie »",
     ["Carte « Médicaments en stock bas » (2 médicaments sous 50 unités).",
      "Niveaux de stock, mouvement de stock (réception / sortie), prescriptions à délivrer."]),
    ("Comptabilité", "Espaces « Tableau de bord » et « MedMa »",
     ["Chiffre d'affaires, créances, rapport « Créances par organisme ».",
      "Dossier de remboursement : Charger les factures → Marquer comme envoyé → Enregistrer un paiement ; Imprimer → « Bordereau MedMa »."]),
]


def ensure_guide():
    import json

    esc = frappe.utils.escape_html
    contenu = [{"id": "gh", "type": "header", "data": {"text": '<span class="h4"><b>Guide de démonstration</b></span>', "col": 12}},
               {"id": "gp", "type": "paragraph", "data": {"text": "Chaque rôle voit uniquement son propre menu. Données 100 % fictives ; connectez-vous avec les comptes demo.* (médecin, réception, pharmacie, compta).", "col": 12}}]
    for i, (role, espace, etapes) in enumerate(GUIDE):
        contenu.append({"id": f"r{i}", "type": "header", "data": {"text": f'<span class="h5"><b>{esc(role)}</b> — {esc(espace)}</span>', "col": 12}})
        for j, e in enumerate(etapes):
            contenu.append({"id": f"r{i}_{j}", "type": "paragraph", "data": {"text": f"• {esc(e)}", "col": 12}})
    valeurs = {"label": "Guide démo", "title": "Guide démo", "module": "Desk", "public": 1, "is_hidden": 0,
               "icon": "book", "content": json.dumps(contenu, ensure_ascii=False)}
    if frappe.db.exists("Workspace", "Guide démo"):
        ws = frappe.get_doc("Workspace", "Guide démo")
        ws.update(valeurs)
        ws.save(ignore_permissions=True)
    else:
        frappe.get_doc({"doctype": "Workspace", "name": "Guide démo", **valeurs}).insert(ignore_permissions=True)


# --- Portail patient ------------------------------------------------------------------------------

FORMULAIRES_PORTAIL = ["lab-test", "prescription", "patient-appointments"]


def ensure_portail():
    """Les formulaires web de Healthcare s'ouvrent par défaut sur « nouveau » ; on affiche d'abord la liste du patient.

    Le lien utilisateur → patient se fait par l'e-mail du patient (Healthcare cherche Patient.email = utilisateur connecté).
    """
    for nom in FORMULAIRES_PORTAIL:
        if frappe.db.exists("Web Form", nom):
            frappe.db.set_value("Web Form", nom, "show_list", 1, update_modified=False)
