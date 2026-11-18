"""Import des catalogues officiels (médicaments, analyses) depuis des fichiers CSV.

    bench --site <site> execute medma_ma.importer.importer_medicaments --kwargs "{'fichier': '/chemin/medicaments.csv'}"
    bench --site <site> execute medma_ma.importer.importer_analyses   --kwargs "{'fichier': '/chemin/analyses.csv', 'dry_run': 1}"

Idempotent (relancer met à jour, ne duplique pas). Aucune donnée officielle n'est embarquée : le client fournit le fichier
issu de la source réglementaire (liste des médicaments du Ministère de la Santé, NABM/ANAM pour les analyses).
Les lignes invalides sont ignorées et listées ; avec dry_run=1 rien n'est écrit.
"""

import csv

import frappe
from frappe.utils import flt

COLONNES_MEDICAMENTS = ["nom_commercial", "dci", "dosage", "unite", "forme", "classe", "ppv", "prix_achat", "code"]
COLONNES_ANALYSES = ["code", "nom", "departement", "tarif"]


def _lire(fichier, colonnes):
    with open(fichier, encoding="utf-8-sig", newline="") as f:
        lecteur = csv.DictReader(f, delimiter=_delimiteur(fichier))
        manquantes = [c for c in colonnes if c not in (lecteur.fieldnames or []) and c not in ("prix_achat", "code", "forme", "classe")]
        if manquantes:
            detail = ", ".join(manquantes)
            raise ValueError(f"Colonnes manquantes : {detail}")
        return [{k: (v or "").strip() for k, v in ligne.items() if k} for ligne in lecteur]


def _delimiteur(fichier):
    with open(fichier, encoding="utf-8-sig") as f:
        entete = f.readline()
    return ";" if entete.count(";") > entete.count(",") else ","


def _garantir(doctype, nom, **valeurs):
    if not frappe.db.exists(doctype, nom):
        frappe.get_doc({"doctype": doctype, "name": nom, **valeurs}).insert(ignore_permissions=True)


def importer_medicaments(fichier, dry_run=0):
    lignes = _lire(fichier, COLONNES_MEDICAMENTS)
    rapport = {"crees": 0, "mis_a_jour": 0, "erreurs": []}
    for i, l in enumerate(lignes, start=2):
        try:
            for c in ("nom_commercial", "dci", "dosage", "unite", "ppv"):
                if not l.get(c):
                    raise ValueError(f"« {c} » vide")
            dosage, ppv = flt(l["dosage"].replace(",", ".")), flt(l["ppv"].replace(",", "."))
            if dosage <= 0 or ppv < 0:
                raise ValueError("dosage ou prix invalide")
            achat = flt((l.get("prix_achat") or "0").replace(",", ".")) or None
            if dry_run:
                rapport["crees"] += 1
                continue
            generique = f"{l['dci']} {l['dosage']}{l['unite']}"
            classe = l.get("classe") or "Non classé"
            _garantir("UOM", l["unite"], uom_name=l["unite"])
            _garantir("Medication Class", classe, medication_class=classe)
            if l.get("forme"):
                _garantir("Dosage Form", l["forme"], dosage_form=l["forme"])
            _garantir("Brand", l["nom_commercial"], brand=l["nom_commercial"])
            ligne_art = {
                "item_code": l["nom_commercial"], "item_group": "Drug", "stock_uom": "Unit",
                "brand": l["nom_commercial"], "is_billable": 1, "rate": ppv,
            }
            if frappe.db.exists("Medication", generique):
                med = frappe.get_doc("Medication", generique)
                existant = next((x for x in med.linked_items if x.item_code == l["nom_commercial"]), None)
                if existant:
                    existant.rate = ppv
                    rapport["mis_a_jour"] += 1
                else:
                    med.append("linked_items", ligne_art)
                    rapport["crees"] += 1
                med.save(ignore_permissions=True)
            else:
                frappe.get_doc({
                    "doctype": "Medication", "generic_name": generique, "medication_class": classe,
                    "strength": dosage, "strength_uom": l["unite"], "dosage_form": l.get("forme") or None,
                    "linked_items": [ligne_art],
                }).insert(ignore_permissions=True)
                rapport["crees"] += 1
            if frappe.db.exists("Item", l["nom_commercial"]):
                frappe.db.set_value("Item", l["nom_commercial"], {
                    "is_stock_item": 1,
                    "valuation_rate": achat or ppv,
                    "description": (f"Code : {l['code']}" if l.get("code") else None),
                }, update_modified=False)
        except Exception as e:
            rapport["erreurs"].append(f"ligne {i} ({l.get('nom_commercial', '?')}) : {e}")
    return _finir(rapport, dry_run)


def importer_analyses(fichier, dry_run=0):
    lignes = _lire(fichier, COLONNES_ANALYSES)
    rapport = {"crees": 0, "mis_a_jour": 0, "erreurs": []}
    for i, l in enumerate(lignes, start=2):
        try:
            for c in ("code", "nom", "tarif"):
                if not l.get(c):
                    raise ValueError(f"« {c} » vide")
            tarif = flt(l["tarif"].replace(",", "."))
            if tarif < 0:
                raise ValueError("tarif négatif")
            existe = frappe.db.exists("Lab Test Template", l["nom"])
            if dry_run:
                rapport["mis_a_jour" if existe else "crees"] += 1
                continue
            dept = l.get("departement") or "Biochemistry"
            _garantir("Medical Department", dept, department=dept)
            valeurs = {"lab_test_code": l["code"], "department": dept, "lab_test_rate": tarif, "is_billable": 1}
            if existe:
                frappe.db.set_value("Lab Test Template", l["nom"], valeurs)
                rapport["mis_a_jour"] += 1
            else:
                frappe.get_doc({
                    "doctype": "Lab Test Template", "lab_test_name": l["nom"], "lab_test_description": l["nom"],
                    "lab_test_group": "Laboratory", "lab_test_template_type": "Single", **valeurs,
                }).insert(ignore_permissions=True)
                rapport["crees"] += 1
        except Exception as e:
            rapport["erreurs"].append(f"ligne {i} ({l.get('nom', '?')}) : {e}")
    return _finir(rapport, dry_run)


def _finir(rapport, dry_run):
    if not dry_run:
        frappe.db.commit()
    print(f"{'[SIMULATION] ' if dry_run else ''}créés : {rapport['crees']} · mis à jour : {rapport['mis_a_jour']} · erreurs : {len(rapport['erreurs'])}")
    for e in rapport["erreurs"][:50]:
        print("  -", e)
    return rapport
