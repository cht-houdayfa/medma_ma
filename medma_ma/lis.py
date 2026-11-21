import frappe
from frappe import _
from frappe.utils import cstr


def _norm(texte):
    """Comparaison tolérante : casse, espaces et accents ignorés."""
    import unicodedata

    t = unicodedata.normalize("NFKD", cstr(texte)).encode("ascii", "ignore").decode().lower()
    return "".join(c for c in t if c.isalnum())


@frappe.whitelist(methods=["POST"])
def recevoir_resultats(lab_test, resultats, appareil=None):
    """Reçoit les résultats d'un automate (via l'agent local) et les inscrit dans l'analyse **en brouillon**.

    - `lab_test` : numéro de l'analyse (le code-barres de l'échantillon, ex. HLC-LAB-2026-00031) ;
    - `resultats` : liste de {"libelle", "valeur", "unite"?, "reference"?} ;
    - jamais de validation automatique : le technicien relit puis valide (Submit).
    Retourne ce qui a été appliqué et ce qui n'a pas pu l'être (rien n'est ignoré en silence)."""
    import json

    if isinstance(resultats, str):
        resultats = json.loads(resultats)
    if not frappe.has_permission("Lab Test", "write"):
        frappe.throw(_("Droits insuffisants pour saisir des résultats."), frappe.PermissionError)
    nom = cstr(lab_test).strip()
    if not frappe.db.exists("Lab Test", nom):
        frappe.throw(_("Analyse introuvable : {0}").format(nom))
    doc = frappe.get_doc("Lab Test", nom)
    if doc.docstatus != 0:
        frappe.throw(_("L'analyse {0} est déjà validée ou annulée : résultats refusés.").format(nom))

    lignes = list(doc.normal_test_items)
    appliques, ignores = [], []
    for r in resultats or []:
        libelle, valeur = cstr(r.get("libelle")).strip(), cstr(r.get("valeur")).strip()
        if not libelle or not valeur:
            ignores.append({"libelle": libelle, "motif": "libellé ou valeur vide"})
            continue
        cible = next(
            (l for l in lignes if _norm(l.lab_test_event) == _norm(libelle) or _norm(l.lab_test_name) == _norm(libelle)),
            None,
        )
        if cible is None and len(lignes) == 1 and len(resultats) == 1:
            cible = lignes[0]  # analyse à un seul paramètre
        if cible is None:
            ignores.append({"libelle": libelle, "valeur": valeur, "motif": "aucun paramètre correspondant"})
            continue
        cible.result_value = valeur
        if r.get("reference") and not cible.normal_range:
            cible.normal_range = cstr(r["reference"])
        appliques.append({"parametre": cible.lab_test_event or cible.lab_test_name, "valeur": valeur})

    if appliques:
        if doc.get("etat_prelevement") == "À prélever":
            doc.etat_prelevement = "Prélevé - en attente du résultat"
        doc.flags.ignore_mandatory = True
        doc.save()
        doc.add_comment(
            "Comment",
            _("Résultats reçus de l'appareil {0} : {1} paramètre(s). À relire puis valider.").format(
                appareil or "?", len(appliques)
            ),
        )
    return {"lab_test": nom, "appliques": appliques, "ignores": ignores}
