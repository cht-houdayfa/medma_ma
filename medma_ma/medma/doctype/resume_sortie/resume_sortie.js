frappe.ui.form.on("Resume Sortie", {
	onload(frm) {
		// le médecin connecté est proposé par défaut
		if (!frm.is_new() || frm.doc.practitioner) return;
		frappe.db.get_value("Healthcare Practitioner", {user_id: frappe.session.user}, "name").then((r) => {
			if (r.message && r.message.name) frm.set_value("practitioner", r.message.name);
		});
	},
	refresh(frm) {
		if (frm.is_new() || !frm.doc.patient) return;
		frappe.xcall("medma_ma.allergies.resume", {patient: frm.doc.patient}).then((t) => {
			frm.dashboard.clear_headline();
			if (t) frm.dashboard.set_headline(`<span class="indicator-pill red">⚠ ${__("Allergies")} : ${frappe.utils.escape_html(t)}</span>`);
		});
	},
});
