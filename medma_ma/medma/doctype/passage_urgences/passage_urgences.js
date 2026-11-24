frappe.ui.form.on("Passage Urgences", {
	setup(frm) {
		// seuls les box d'urgence libres sont proposés (le lit déjà attribué à ce passage reste sélectionnable)
		frm.set_query("unite_service", () => ({
			filters: {service_unit_type: "Box d'urgence", is_group: 0, occupancy_status: "Vacant"},
		}));
	},
	patient(frm) {
		if (!frm.doc.patient) return frm.set_value("allergies_alerte", "");
		frappe.xcall("medma_ma.allergies.resume", {patient: frm.doc.patient}).then((t) => frm.set_value("allergies_alerte", t || ""));
	},
	refresh(frm) {
		frm.dashboard.clear_headline();
		if (frm.doc.allergies_alerte) {
			frm.dashboard.set_headline(`<span class="indicator-pill red">⚠ ${__("Allergies")} : ${frappe.utils.escape_html(frm.doc.allergies_alerte)}</span>`);
		}
		if (frm.is_new()) return;
		if (frm.doc.statut === "En attente") {
			frm.add_custom_button(__("Prendre en charge"), () => {
				frm.set_value("statut", "En cours de soins");
				frm.save();
			}).addClass("btn-primary");
		}
		if (frm.doc.statut !== "Terminé" && !frm.doc.consultation) {
			frm.add_custom_button(__("Créer la consultation"), () => {
				frappe.new_doc("Patient Encounter", {patient: frm.doc.patient, practitioner: frm.doc.practitioner});
			});
		}
		if (frm.doc.statut === "Terminé") {
			frm.add_custom_button(__("Résumé de sortie"), () => {
				frappe.db.get_value("Resume Sortie", {passage_urgences: frm.doc.name}, "name").then((r) => {
					if (r.message && r.message.name) return frappe.set_route("Form", "Resume Sortie", r.message.name);
					frappe.new_doc("Resume Sortie", {
						patient: frm.doc.patient, practitioner: frm.doc.practitioner, passage_urgences: frm.doc.name,
						motif: frm.doc.motif, diagnostic: frm.doc.diagnostic, traitement_sortie: frm.doc.traitement,
						orientation: frm.doc.orientation, inpatient_record: frm.doc.dossier_hospitalisation,
					});
				});
			}).addClass("btn-primary");
		}
		if (frm.doc.orientation === "Hospitalisation" && !frm.doc.dossier_hospitalisation) {
			frm.add_custom_button(__("Créer l'hospitalisation"), () => {
				frappe.new_doc("Inpatient Record", {patient: frm.doc.patient, admission_practitioner: frm.doc.practitioner});
			});
		}
	},
});
