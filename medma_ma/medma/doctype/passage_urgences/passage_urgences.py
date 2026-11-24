import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime, time_diff_in_seconds

# (champ, minimum, maximum, libellé) : bornes de saisie plausibles, pour repérer une faute de frappe
BORNES = [
    ("tension_systolique", 30, 300, "Tension systolique"),
    ("tension_diastolique", 20, 200, "Tension diastolique"),
    ("frequence_cardiaque", 20, 300, "Pouls"),
    ("frequence_respiratoire", 4, 80, "Fréquence respiratoire"),
    ("saturation", 40, 100, "Saturation en O2"),
    ("temperature", 25, 45, "Température"),
    ("glycemie", 0.1, 10, "Glycémie"),
    ("score_douleur", 0, 10, "Douleur"),
    ("glasgow", 3, 15, "Score de Glasgow"),
]


class PassageUrgences(Document):
    def validate(self):
        # heure du serveur (fuseau du Maroc) : l'horloge du navigateur peut être décalée
        self.date_arrivee = self.date_arrivee or now_datetime()
        self._verifier_constantes()
        self._suivre_horaires()

    def _verifier_constantes(self):
        for champ, mini, maxi, libelle in BORNES:
            valeur = self.get(champ)
            if valeur is None or valeur == "" or (valeur == 0 and champ != "score_douleur"):
                continue
            if not mini <= valeur <= maxi:
                frappe.throw(_("{0} : la valeur {1} est hors des limites plausibles ({2} à {3}).").format(_(libelle), valeur, mini, maxi))
        if self.tension_systolique and self.tension_diastolique and self.tension_diastolique >= self.tension_systolique:
            frappe.throw(_("La tension diastolique doit être inférieure à la systolique."))

    def _suivre_horaires(self):
        """Le délai d'attente est celui de l'arrivée à la première prise en charge ; la sortie est horodatée à la clôture."""
        if self.statut != "En attente" and not self.date_prise_en_charge:
            self.date_prise_en_charge = now_datetime()
        if self.statut == "En attente":
            self.date_prise_en_charge = None
            self.delai_attente = 0
        elif self.date_prise_en_charge and self.date_arrivee:
            secondes = time_diff_in_seconds(get_datetime(self.date_prise_en_charge), get_datetime(self.date_arrivee))
            self.delai_attente = max(int(secondes // 60), 0)
        if self.statut == "Terminé":
            if not self.orientation:
                frappe.throw(_("Indiquez l'orientation du patient avant de clôturer le passage."))
            self.date_sortie = self.date_sortie or now_datetime()
        else:
            self.date_sortie = None
            self.orientation = None
