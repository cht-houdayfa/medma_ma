frappe.ui.form.on("Passage Urgences", {
	refresh(frm) {
		frm.dashboard.clear_headline();
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
	},
});
