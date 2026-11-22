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
	("Certificat MedMa", "Certificat Medical", "certificat.html"),
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
		"aggregate_function_based_on": "net_total",
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
		"value_based_on": "net_total",
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
		# un nombre de rendez-vous, pas un montant : sans champ de valeur entier, Frappe affiche « 13.00 د.م. »
		"value_based_on": "duration",
		"currency": None,
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

REPORT_RDV_JOUR = {
	"name": "Rendez-vous du jour (liste)",
	"query": (
		"SELECT pa.appointment_time AS `Heure:Time:80`, pa.patient_name AS `Patient:Data:200`, "
		"pa.practitioner_name AS `Praticien:Data:180`, pa.appointment_type AS `Type:Data:160`, "
		"CASE pa.status WHEN 'Checked In' THEN 'Arrivé' WHEN 'Open' THEN 'Ouvert' WHEN 'Scheduled' THEN 'Prévu' "
		"WHEN 'Confirmed' THEN 'Confirmé' WHEN 'Closed' THEN 'Terminé' WHEN 'Cancelled' THEN 'Annulé' "
		"ELSE pa.status END AS `Statut:Data:100`, pa.name AS `Rendez-vous:Link/Patient Appointment:150` "
		"FROM `tabPatient Appointment` pa "
		"WHERE pa.appointment_date = CURDATE() AND pa.status != 'Cancelled' "
		"ORDER BY pa.appointment_time"
	),
}


def ensure_rapport_rdv_jour():
	rep = REPORT_RDV_JOUR
	valeurs = {
		"report_name": rep["name"],
		"ref_doctype": "Patient Appointment",
		"report_type": "Query Report",
		"is_standard": "No",
		"module": "MedMa",
		"query": rep["query"],
		"roles": [{"role": r} for r in ("Healthcare Administrator", "Physician", "Nursing User", "System Manager")],
	}
	if frappe.db.exists("Report", rep["name"]):
		r = frappe.get_doc("Report", rep["name"])
		r.update(valeurs)
		r.save(ignore_permissions=True)
	else:
		frappe.get_doc({"doctype": "Report", **valeurs}).insert(ignore_permissions=True)


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
	ws.set("roles", [{"role": r} for r in ("Accounts Manager", "System Manager")])
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


def ensure_taxes():
	"""Les actes médicaux (consultations, analyses) sont exonérés de TVA : le modèle par défaut ne doit pas ajouter 20 %.
	On crée un modèle « Actes médicaux (exonéré de TVA) » sans ligne de taxe et on le met par défaut ; les modèles TVA
	existants restent disponibles (parapharmacie, vente de produits).
	À faire valider par le comptable de l'établissement selon la nature des prestations facturées."""
	societe = frappe.db.get_value("Company", {}, "name")
	if not societe:
		return
	abbr = frappe.db.get_value("Company", societe, "abbr")
	nom = f"Actes médicaux (exonéré de TVA) - {abbr}"
	if not frappe.db.exists("Sales Taxes and Charges Template", nom):
		frappe.get_doc({"doctype": "Sales Taxes and Charges Template", "title": "Actes médicaux (exonéré de TVA)",
		                "company": societe, "is_default": 1}).insert(ignore_permissions=True)
	frappe.db.sql("update `tabSales Taxes and Charges Template` set is_default = 0 where name != %s and company = %s",
	              (nom, societe))
	frappe.db.set_value("Sales Taxes and Charges Template", nom, "is_default", 1, update_modified=False)


SCRIPT_FACTURE = """
frappe.ui.form.on('Sales Invoice', {
	setup(frm) {
		// on ne propose que les couvertures du patient de la facture
		frm.set_query('couverture_patient', () => ({filters: {patient: frm.doc.patient || '', actif: 1}}));
	},
	refresh(frm) {
		if (frm.doc.docstatus !== 0) return;
		// « Healthcare Services » lit les consultations : réservé aux soignants (secret médical), la réception utilise le bouton ci-dessous
		if (!frappe.user.has_role('Physician') && !frappe.user.has_role('System Manager')) {
			const retirer = () => ['Healthcare Services', 'Prescriptions'].forEach(b => frm.remove_custom_button(__(b), __('Get Items From')));
			setTimeout(retirer, 300);
			setTimeout(retirer, 1500);
		}
		frm.add_custom_button(__('Ajouter la consultation'), () => {
			const d = new frappe.ui.Dialog({
				title: __('Consultation du praticien'),
				fields: [{fieldname: 'praticien', fieldtype: 'Link', options: 'Healthcare Practitioner', label: __('Praticien'),
				          reqd: 1, default: frm.doc.ref_practitioner}],
				primary_action_label: __('Ajouter'),
				primary_action(v) {
					frappe.db.get_value('Healthcare Practitioner', v.praticien, ['op_consulting_charge_item', 'op_consulting_charge'])
						.then(r => {
							const p = r.message || {};
							if (!p.op_consulting_charge_item) {
								frappe.msgprint(__("Aucun tarif de consultation n'est défini pour ce praticien."));
								return;
							}
							// le code article est posé APRÈS la création de la ligne : c'est ce changement qui déclenche le
							// chargement du nom, de l'unité et du compte de produits par ERPNext
							const ligne = frm.add_child('items', {qty: 1});
							frm.refresh_field('items');
							frappe.model.set_value(ligne.doctype, ligne.name, 'item_code', p.op_consulting_charge_item).then(() =>
								frappe.model.set_value(ligne.doctype, ligne.name, 'rate', p.op_consulting_charge || 0));
							d.hide();
						});
				}
			});
			d.show();
		});
	}
});
"""


def ensure_client_script_facture():
	nom = "MedMa - Facture"
	valeurs = {"dt": "Sales Invoice", "view": "Form", "enabled": 1, "script": SCRIPT_FACTURE}
	if frappe.db.exists("Client Script", nom):
		cs = frappe.get_doc("Client Script", nom)
		cs.update(valeurs)
		cs.save(ignore_permissions=True)
	else:
		frappe.get_doc({"doctype": "Client Script", "name": nom, **valeurs}).insert(ignore_permissions=True)


SCRIPT_ARRIVEE = """
frappe.ui.form.on('Patient Appointment', {
	refresh(frm) {
		if (frm.is_new()) return;
		if (['Open', 'Scheduled', 'Confirmed'].includes(frm.doc.status)) {
			frm.add_custom_button(__('Patient arrivé'), () => {
				frm.set_value('status', 'Checked In');
				frm.save().then(() => frappe.show_alert({message: __('Arrivée enregistrée'), indicator: 'green'}));
			}).addClass('btn-primary');
		} else if (frm.doc.status === 'Checked In') {
			frm.dashboard.set_headline(__('Patient arrivé — en attente de consultation'), 'green');
		}
	}
});
"""


def ensure_client_script_arrivee():
	nom = "MedMa - Arrivée patient"
	valeurs = {"dt": "Patient Appointment", "view": "Form", "enabled": 1, "script": SCRIPT_ARRIVEE}
	if frappe.db.exists("Client Script", nom):
		cs = frappe.get_doc("Client Script", nom)
		cs.update(valeurs)
		cs.save(ignore_permissions=True)
	else:
		frappe.get_doc({"doctype": "Client Script", "name": nom, **valeurs}).insert(ignore_permissions=True)


SCRIPT_PRELEVEMENT = """
frappe.ui.form.on('Lab Test', {
	refresh(frm) {
		if (frm.is_new() || frm.doc.docstatus !== 0) return;
		if (frm.doc.etat_prelevement === 'Prélevé - en attente du résultat') {
			frm.dashboard.set_headline(__('Prélevé — en attente du résultat'), 'orange');
			return;
		}
		frm.dashboard.set_headline(__('Échantillon à prélever'), 'blue');
		frm.add_custom_button(__('Prélèvement effectué'), () => {
			frappe.confirm(__("Confirmer que l'échantillon a été prélevé ?"), () => {
				frm.set_value('etat_prelevement', 'Prélevé - en attente du résultat');
				frm.set_value('date_prelevement', frappe.datetime.now_datetime());
				frm.set_value('preleve_par', frappe.session.user);
				frm.save().then(() => frappe.show_alert({message: __('Prélèvement enregistré'), indicator: 'green'}));
			});
		}).addClass('btn-primary');
	}
});
"""


def ensure_client_script_prelevement():
	nom = "MedMa - Prélèvement"
	valeurs = {"dt": "Lab Test", "view": "Form", "enabled": 1, "script": SCRIPT_PRELEVEMENT}
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
	ensure_client_script_arrivee()
	ensure_client_script_facture()
	ensure_taxes()
	ensure_client_script_prelevement()
	ensure_client_scripts_dossier()
	ensure_client_scripts_couverture()
	ensure_branding()
	ensure_guide()
	ensure_portail()
	ensure_ordonnance_ui()


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
    ("Guide Réception", ["Healthcare Administrator"], "Votre journée à la réception", "Espace « Réception »",
     ["Nouveau patient : nom, CIN, téléphone, puis la couverture (CNSS / CNOPS / AMO / mutuelle).",
      "Nouveau rendez-vous : choisir le praticien, « Check Availability » (créneaux libres), réserver.",
      "À l'arrivée du patient : ouvrir son rendez-vous → bouton « Patient arrivé ». Il apparaît chez le médecin.",
      "Facture : bouton « Ajouter la consultation », choisir la couverture : part organisme / part patient sont calculées seules.",
      "Encaisser la part patient : bouton « Enregistrer le paiement » ; Imprimer → « Facture MedMa ».",
      "Rapport « Rendez-vous du jour (liste) » pour suivre la salle d'attente."]),
    ("Guide Médecin", ["Physician"], "Votre journée de consultation", "Espace « Cabinet médecin »",
     ["Carte « Patients en salle d'attente » : les patients arrivés apparaissent ici.",
      "Ouvrir le rendez-vous → Consultation : motif, constantes, diagnostic.",
      "Ordonnance : médicament par nom de marque ou générique (DCI) ; analyses : elles partent seules au laboratoire.",
      "Valider la consultation, puis Imprimer → « Ordonnance MedMa » (PDF).",
      "Certificats médicaux → Nouveau : arrêt de travail (nombre de jours calculé) ; Imprimer → « Certificat MedMa ».",
      "Carte « Analyses à valider » : consulter les résultats reçus du laboratoire."]),
    ("Guide Infirmier", ["Nursing User"], "Vos tâches de soins", "Espace « Soins infirmiers »",
     ["Rendez-vous du jour et patients en salle d'attente.",
      "Prendre les constantes (tension, pouls, température, poids) dans « Signes vitaux » du patient.",
      "Suivre les patients hospitalisés : lits, soins et observations.",
      "Les informations de facturation ne sont pas visibles pour ce rôle."]),
    ("Guide Laboratoire", ["Laboratory User"], "Du prélèvement au résultat", "Espace « Laboratoire »",
     ["Carte « Prélèvements à faire » : les analyses prescrites apparaissent automatiquement.",
      "Ouvrir l'analyse → bouton « Prélèvement effectué » : l'état passe à « en attente du résultat ».",
      "Carte « Résultats en attente » : saisir les valeurs, ou les recevoir automatiquement de l'automate (voir deploy/LIS.md).",
      "Valider l'analyse : l'état devient « Résultat validé » et le médecin et le patient la voient."]),
    ("Guide Pharmacie", ["Stock User"], "Délivrer sur ordonnance", "Espace « Pharmacie »",
     ["Prescriptions : liste des ordonnances (lecture seule) à délivrer.",
      "Carte « Médicaments en stock bas » : médicaments sous le seuil de 50 unités.",
      "Mouvements de stock : entrée (réception fournisseur) ou sortie (délivrance).",
      "Niveaux de stock : quantité disponible par médicament."]),
    ("Guide Comptabilité", ["Accounts Manager"], "Facturation et remboursements", "Espaces « Tableau de bord » et « MedMa »",
     ["Tableau de bord : chiffre d'affaires hors taxes, créances ouvertes, factures émises.",
      "Rapport « Créances par organisme » : ce que doivent la CNSS, la CNOPS, l'AMO et les mutuelles.",
      "Dossier de remboursement : Charger les factures → Marquer comme envoyé → Enregistrer un paiement.",
      "Imprimer → « Bordereau MedMa » pour l'envoi à l'organisme.",
      "Les actes médicaux sont exonérés de TVA : aucune taxe n'est ajoutée par défaut."]),
]


def ensure_guide():
    """Un guide par rôle : chaque utilisateur ne voit dans son menu que le guide de son propre métier."""
    import json

    esc = frappe.utils.escape_html
    # l'ancien guide unique, visible de tous, est remplacé
    if frappe.db.exists("Workspace", "Guide démo"):
        frappe.delete_doc("Workspace", "Guide démo", force=True, ignore_permissions=True)
    for nom, roles, titre, espace, etapes in GUIDE:
        contenu = [{"id": "gh", "type": "header", "data": {"text": f'<span class="h4"><b>{esc(titre)}</b></span>', "col": 12}},
                   {"id": "gp", "type": "paragraph", "data": {"text": f"Votre espace de travail : {esc(espace)}. Données de démonstration fictives.", "col": 12}}]
        for j, e in enumerate(etapes):
            contenu.append({"id": f"e{j}", "type": "paragraph", "data": {"text": f"{j + 1}. {esc(e)}", "col": 12}})
        valeurs = {"label": nom, "title": nom, "module": "Desk", "public": 1, "is_hidden": 0,
                   "icon": "book", "content": json.dumps(contenu, ensure_ascii=False)}
        if frappe.db.exists("Workspace", nom):
            ws = frappe.get_doc("Workspace", nom)
            ws.update(valeurs)
        else:
            ws = frappe.get_doc({"doctype": "Workspace", "name": nom, **valeurs})
        ws.set("roles", [{"role": r} for r in roles + ["System Manager"]])
        ws.save(ignore_permissions=True) if ws.get("creation") else ws.insert(ignore_permissions=True)


# --- Portail patient ------------------------------------------------------------------------------

FORMULAIRES_PORTAIL = ["lab-test", "prescription", "patient-appointments"]


def ensure_portail():
    """Les formulaires web de Healthcare s'ouvrent par défaut sur « nouveau » ; on affiche d'abord la liste du patient.

    Le lien utilisateur → patient se fait par l'e-mail du patient (Healthcare cherche Patient.email = utilisateur connecté).
    """
    for nom in FORMULAIRES_PORTAIL:
        if frappe.db.exists("Web Form", nom):
            frappe.db.set_value("Web Form", nom, "show_list", 1, update_modified=False)
    ensure_portail_rendez_vous()


CSS_PORTAIL = """
.web-form-container, .web-list-container { font-family: inherit; }
.web-list-header .btn-primary, a.btn[href$="/new"], .list-view-actions .btn-primary { display: none !important; }
.web-list-table th { background: #f1f5f4; color: #0f4c46; font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: .03em; }
.web-list-table td { vertical-align: middle; }
.web-list-table tr:hover td { background: #f7fbfa; }
.indicator-pill { border-radius: 999px; padding: 3px 10px; font-weight: 600; }
a[href="/app"], a[href="/desk"] { display: none !important; }
.mm-portail-note { background: #eef7f5; border-inline-start: 4px solid #0f766e; padding: 12px 16px; border-radius: 8px; color: #134e48; margin-bottom: 16px; }
"""


def _polir_formulaire(nom, titre, libelles, colonnes, champs_ajoutes=(), masques=()):
    """Formulaire web standard → page patient en lecture seule, titres et colonnes en français.

    Frappe refuse d'enregistrer un formulaire standard hors mode développeur : on écrit directement en base.
    """
    if not frappe.db.exists("Web Form", nom):
        return
    frappe.db.set_value("Web Form", nom, {
        "title": titre, "list_title": titre, "allow_edit": 0, "allow_delete": 0,
        "introduction_text": (
            '<div class="mm-portail-note">Pour toute question, ou pour prendre, modifier ou annuler un rendez-vous, '
            "contactez la réception de l'établissement.</div>"
        ),
        "custom_css": CSS_PORTAIL,
    }, update_modified=False)
    existants = set(frappe.get_all("Web Form Field", filters={"parent": nom}, pluck="fieldname"))
    idx = len(existants) + 100
    for champ, typ in champs_ajoutes:
        if champ not in existants:
            idx += 1
            frappe.get_doc({"doctype": "Web Form Field", "parent": nom, "parenttype": "Web Form",
                            "parentfield": "web_form_fields", "idx": idx, "fieldname": champ, "fieldtype": typ,
                            "label": libelles.get(champ, champ), "read_only": 1}).db_insert()
    for champ, libelle in libelles.items():
        frappe.db.set_value("Web Form Field", {"parent": nom, "fieldname": champ},
                            {"label": libelle, "read_only": 1}, update_modified=False)
    for champ in masques:
        frappe.db.set_value("Web Form Field", {"parent": nom, "fieldname": champ}, "hidden", 1, update_modified=False)
    frappe.db.set_value("Web Form", nom, "allow_comments", 0, update_modified=False)
    frappe.db.delete("Web Form List Column", {"parent": nom})
    for i, (champ, typ) in enumerate(colonnes, 1):
        frappe.get_doc({"doctype": "Web Form List Column", "parent": nom, "parenttype": "Web Form",
                        "parentfield": "list_columns", "idx": i, "fieldname": champ, "fieldtype": typ,
                        "label": libelles.get(champ, champ)}).db_insert()
    frappe.clear_document_cache("Web Form", nom)


MENU_PORTAIL = {
    "/personal-details": "Mes informations",
    "/lab-test": "Mes analyses",
    "/prescription": "Mes ordonnances",
    "/patient-appointments": "Mes rendez-vous",
}


def ensure_portail_rendez_vous():
    """Portail patient : rendez-vous, analyses et ordonnances en lecture seule, menu en français.

    La prise de rendez-vous en ligne n'est pas proposée (le patient n'a pas le droit de créer un rendez-vous) :
    pas de formulaire de création inutilisable.
    """
    _polir_formulaire(
        "patient-appointments", "Mes rendez-vous",
        {"patient": "Patient", "practitioner": "Praticien", "practitioner_name": "Praticien",
         "appointment_date": "Date", "appointment_time": "Heure", "department": "Département",
         "appointment_type": "Type", "status": "Statut"},
        [("appointment_date", "Date"), ("appointment_time", "Data"), ("practitioner_name", "Data"),
         ("department", "Link"), ("status", "Select")],
        champs_ajoutes=[("practitioner_name", "Data")])
    _polir_formulaire(
        "lab-test", "Mes analyses",
        {"lab_test_name": "Analyse", "department": "Département", "status": "Statut",
         "submitted_date": "Date du résultat", "patient_name": "Patient", "patient_age": "Âge",
         "patient_sex": "Sexe", "practitioner_name": "Médecin prescripteur", "lab_test_comment": "Commentaires",
         "custom_result": "Résultat", "employee_name": "Technicien de laboratoire", "company": "Établissement"},
        [("submitted_date", "Datetime"), ("lab_test_name", "Data"), ("practitioner_name", "Data"),
         ("status", "Select")],
        masques=["patient", "practitioner", "inpatient_record", "report_preference", "requesting_department",
                 "employee", "employee_designation", "company", "department", "descriptive_test_items",
                 "organisms", "sensitivity_test_items", "custom_result", "email", "mobile"])
    _polir_formulaire(
        "prescription", "Mes ordonnances",
        {"practitioner": "Praticien", "practitioner_name": "Praticien", "visit_department": "Département",
         "encounter_date": "Date", "encounter_time": "Heure", "drug_prescription": "Médicaments",
         "lab_test_prescription": "Analyses prescrites", "encounter_comment": "Recommandations",
         "status": "Statut"},
        [("encounter_date", "Date"), ("encounter_time", "Data"), ("practitioner_name", "Data")],
        champs_ajoutes=[("practitioner_name", "Data")])
    for route, titre in MENU_PORTAIL.items():
        frappe.db.set_value("Portal Menu Item", {"route": route}, "title", titre, update_modified=False)
    frappe.db.set_value("Portal Menu Item", {"route": "/newsletters"}, "enabled", 0, update_modified=False)
    frappe.clear_cache()


# --- Ordonnance : le médecin choisit l'analyse dans le catalogue -------------------------------------

def ensure_ordonnance_ui():
    """Dans la consultation, la grille « Lab Tests » affichait « Observation » (modèles vides) ; le choix du catalogue
    des analyses (Lab Test Template) était caché dans le formulaire de ligne. On met le catalogue en colonne."""
    reglages = [
        ("Lab Prescription", "lab_test_code", "in_list_view", "1", "Check"),
        ("Lab Prescription", "lab_test_code", "label", "Analyse", "Data"),
        ("Lab Prescription", "observation_template", "in_list_view", "0", "Check"),
        ("Lab Prescription", "observation_template", "hidden", "1", "Check"),
        # prescription par DCI : le médecin choisit le médicament, la marque (Drug Code) reste facultative
        ("Drug Prescription", "drug_code", "reqd", "0", "Check"),
    ]
    for doctype, champ, prop, valeur, typ in reglages:
        frappe.make_property_setter(
            {"doctype": doctype, "doctype_or_field": "DocField", "fieldname": champ,
             "property": prop, "value": valeur, "property_type": typ},
            validate_fields_for_doctype=False,
        )
    frappe.clear_cache(doctype="Lab Prescription")
    frappe.clear_cache(doctype="Drug Prescription")
    frappe.clear_cache(doctype="Patient Encounter")
