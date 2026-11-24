frappe.listview_settings["Passage Urgences"] = {
	add_fields: ["niveau_triage", "statut"],
	get_indicator(doc) {
		const couleurs = {"1": "red", "2": "orange", "3": "yellow", "4": "green", "5": "blue"};
		if (doc.statut === "Terminé") return [__("Terminé"), "gray", "statut,=,Terminé"];
		return [`${doc.niveau_triage} · ${doc.statut}`, couleurs[(doc.niveau_triage || "3")[0]], `statut,=,${doc.statut}`];
	},
};
