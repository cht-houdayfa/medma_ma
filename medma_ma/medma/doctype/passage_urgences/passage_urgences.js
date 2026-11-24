frappe.ui.form.on("Passage Urgences", {
	refresh(frm) {
		const couleurs = {"1": "red", "2": "orange", "3": "yellow", "4": "green", "5": "blue"};
		frm.dashboard.clear_headline();
		if (frm.doc.niveau_triage) {
			frm.dashboard.set_headline(
				`<span class="indicator-pill ${couleurs[frm.doc.niveau_triage[0]]}">Niveau ${frm.doc.niveau_triage}</span>`);
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
	},
});
