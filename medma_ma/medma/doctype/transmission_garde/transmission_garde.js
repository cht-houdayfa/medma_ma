frappe.ui.form.on("Transmission Garde", {
	onload(frm) {
		if (frm.is_new() && !frm.doc.infirmier_sortant) frm.set_value("infirmier_sortant", frappe.session.user);
	},
	refresh(frm) {
		// reprend les patients actuellement aux urgences pour ne rien oublier
		if (frm.is_new() && frm.doc.service === "Urgences" && !(frm.doc.patients || []).length) {
			frappe.db.get_list("Passage Urgences", {filters: {statut: ["!=", "Terminé"]}, fields: ["patient", "motif", "niveau_triage", "statut"], order_by: "niveau_triage asc"})
				.then((l) => {
					(l || []).forEach((p) => frm.add_child("patients", {patient: p.patient, situation: `${p.niveau_triage} — ${p.motif} (${p.statut})`}));
					frm.refresh_field("patients");
				});
		}
	},
});
