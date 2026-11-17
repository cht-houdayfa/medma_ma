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
	"Patients enregistrés": {"document_type": "Patient", "function": "Count", "filters_json": []},
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

ANCIENNES_CARTES = ["Chiffre d'affaires du mois"]


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


def ensure_all():
	ensure_print_formats()
	ensure_dashboard()
	ensure_client_scripts()
