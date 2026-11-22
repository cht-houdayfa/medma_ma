import frappe


def creer_analyse_depuis_demande(doc, methode=None):
    """Prescription d'analyse validée par le médecin → l'analyse apparaît seule dans « Prélèvements à faire ».

    Healthcare ne crée l'analyse qu'à la main (bouton « Lab Test » sur la demande de service). Ici elle est créée en
    brouillon dès la validation de la consultation, sauf si l'établissement exige le paiement avant (réglage Healthcare)."""
    if doc.template_dt != "Lab Test Template":
        return
    if frappe.db.exists("Lab Test", {"service_request": doc.name}):
        return
    if frappe.db.get_single_value("Healthcare Settings", "process_service_request_only_if_paid") and (
        doc.billing_status != "Invoiced"
    ):
        return
    from healthcare.healthcare.doctype.service_request.service_request import make_lab_test

    analyse = make_lab_test(frappe._dict(doc.as_dict()))
    analyse.flags.ignore_permissions = True
    analyse.insert()


def marquer_resultat_valide(doc, method=None):
    """À la validation de l'analyse, l'état du prélèvement passe à « Résultat validé »."""
    import frappe

    if doc.meta.has_field("etat_prelevement"):
        frappe.db.set_value("Lab Test", doc.name, "etat_prelevement", "Résultat validé", update_modified=False)
        doc.etat_prelevement = "Résultat validé"
