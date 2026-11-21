#!/usr/bin/env python3
"""Agent LIS MedMa : reçoit les résultats d'un automate (ASTM / HL7) et les envoie à MedMa.

Bibliothèque standard uniquement. À installer sur un PC du laboratoire relié à l'automate.

  python3 lis_agent.py --config config.json ecouter            # serveur TCP (l'automate se connecte)
  python3 lis_agent.py --config config.json fichier resultat.txt   # message enregistré (ASTM ou HL7)
  python3 lis_agent.py --config config.json rejouer            # renvoie les messages en attente (réseau coupé)
  python3 lis_agent.py --a-blanc ...                            # affiche sans envoyer

Le numéro d'échantillon lu par l'automate (code-barres) doit être le numéro de l'analyse MedMa (HLC-LAB-AAAA-NNNNN).
"""
import argparse
import json
import os
import socketserver
import sys
import time
import urllib.request

ENQ, ACK, EOT, STX, ETX, ETB = b"\x05", b"\x06", b"\x04", b"\x02", b"\x03", b"\x17"
VT, FS, CR = b"\x0b", b"\x1c", b"\x0d"


# ---------------------------------------------------------------- analyse des messages

def _composant(champ, i=0):
    parts = champ.split("^")
    return parts[i].strip() if i < len(parts) else ""


def _texte_astm(octets):
    """Retire les trames (STX n … ETX/ETB cc CRLF) et les octets de contrôle ; renvoie le texte des enregistrements."""
    texte, i, n = bytearray(), 0, len(octets)
    if STX not in octets:
        return octets.decode("utf-8", "replace").replace("\r\n", "\r").replace("\n", "\r")
    while i < n:
        if octets[i:i + 1] == STX:
            j = i + 2  # saute le numéro de trame
            while j < n and octets[j:j + 1] not in (ETX, ETB):
                texte.append(octets[j])
                j += 1
            i = j + 5  # ETX + 2 car. somme de contrôle + CRLF
        else:
            i += 1
    return texte.decode("utf-8", "replace")


def analyser_astm(octets):
    """ASTM E1394 / LIS2-A2 → liste de {'echantillon', 'resultats': [{'code','libelle','valeur','unite','reference'}]}."""
    echantillons, courant = [], None
    for enr in _texte_astm(octets).replace("\n", "\r").split("\r"):
        enr = enr.strip("\x02\x03\x04\x05")
        if not enr:
            continue
        champs = enr.split("|")
        type_ = champs[0][-1:] if champs[0] else ""
        if type_ == "O":
            ident = _composant(champs[2]) if len(champs) > 2 else ""
            ident = ident or (_composant(champs[3]) if len(champs) > 3 else "")
            courant = {"echantillon": ident, "resultats": []}
            echantillons.append(courant)
        elif type_ == "R" and courant is not None and len(champs) > 3:
            test = champs[2]
            code = _composant(test, 3) or _composant(test, 0)
            courant["resultats"].append({
                "code": code, "libelle": _composant(test, 1) or code, "valeur": champs[3].strip(),
                "unite": champs[4].strip() if len(champs) > 4 else "",
                "reference": champs[5].strip() if len(champs) > 5 else "",
            })
    return echantillons


def analyser_hl7(octets):
    """HL7 v2 (ORU^R01, éventuellement encadré MLLP) → même structure que analyser_astm."""
    texte = octets.replace(VT, b"").replace(FS, b"").decode("utf-8", "replace").replace("\r\n", "\r").replace("\n", "\r")
    echantillons, courant = [], None
    for seg in texte.split("\r"):
        champs = seg.strip().split("|")
        if champs[0] == "OBR":
            ident = _composant(champs[3]) if len(champs) > 3 else ""
            ident = ident or (_composant(champs[2]) if len(champs) > 2 else "")
            courant = {"echantillon": ident, "resultats": []}
            echantillons.append(courant)
        elif champs[0] == "OBX" and courant is not None and len(champs) > 5:
            if champs[2] in ("ED", "RP", "TX", "FT"):  # images, histogrammes, texte libre : ignorés
                continue
            code = _composant(champs[3], 0)
            courant["resultats"].append({
                "code": code, "libelle": _composant(champs[3], 1) or code, "valeur": champs[5].strip(),
                "unite": _composant(champs[6]) if len(champs) > 6 else "",
                "reference": champs[7].strip() if len(champs) > 7 else "",
            })
    return echantillons


def analyser(octets):
    return analyser_hl7(octets) if (b"MSH|" in octets or b"OBX|" in octets) else analyser_astm(octets)


# ---------------------------------------------------------------- envoi à MedMa

def charger(chemin):
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def vers_medma(echantillon, cfg, appareil):
    """Applique la correspondance codes automate → paramètres MedMa, puis prépare les arguments d'appel."""
    corr = cfg.get("correspondance", {})
    resultats = []
    for r in echantillon["resultats"]:
        libelle = corr.get(r["code"]) or corr.get(r["libelle"]) or r["libelle"]
        resultats.append({"libelle": libelle, "valeur": r["valeur"], "unite": r["unite"], "reference": r["reference"]})
    return {"lab_test": echantillon["echantillon"], "resultats": json.dumps(resultats), "appareil": appareil}


def envoyer(args, cfg, a_blanc=False):
    if a_blanc:
        print(json.dumps(args, ensure_ascii=False, indent=2))
        return True
    url = cfg["url"].rstrip("/") + "/api/method/medma_ma.lis.recevoir_resultats"
    req = urllib.request.Request(
        url, data=json.dumps(args).encode(), method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"token {cfg['api_key']}:{cfg['api_secret']}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as rep:
            corps = json.loads(rep.read().decode()).get("message", {})
        print(f"[ok] {corps.get('lab_test')}: {len(corps.get('appliques', []))} appliqué(s), "
              f"{len(corps.get('ignores', []))} non reconnu(s) {corps.get('ignores') or ''}")
        return True
    except Exception as e:  # réseau coupé, analyse refusée…
        print(f"[échec] {args['lab_test']}: {e}", file=sys.stderr)
        return False


def traiter(octets, cfg, appareil, a_blanc=False):
    dossier = cfg.get("dossier_donnees", "donnees")
    for sous in ("brut", "attente"):
        os.makedirs(os.path.join(dossier, sous), exist_ok=True)
    horodatage = time.strftime("%Y%m%d-%H%M%S")
    with open(os.path.join(dossier, "brut", f"{horodatage}.bin"), "wb") as f:  # trace d'audit du message d'origine
        f.write(octets)
    for i, ech in enumerate(analyser(octets)):
        if not ech["echantillon"] or not ech["resultats"]:
            continue
        args = vers_medma(ech, cfg, appareil)
        if not envoyer(args, cfg, a_blanc) and not a_blanc:
            with open(os.path.join(dossier, "attente", f"{horodatage}-{i}.json"), "w", encoding="utf-8") as f:
                json.dump(args, f, ensure_ascii=False)


def rejouer(cfg):
    attente = os.path.join(cfg.get("dossier_donnees", "donnees"), "attente")
    for nom in sorted(os.listdir(attente)) if os.path.isdir(attente) else []:
        chemin = os.path.join(attente, nom)
        if envoyer(charger(chemin), cfg):
            os.remove(chemin)


# ---------------------------------------------------------------- serveur TCP (ASTM et HL7/MLLP)

def serveur(cfg, a_blanc):
    appareil = cfg.get("appareil", "automate")

    class Gestionnaire(socketserver.BaseRequestHandler):
        def handle(self):
            tampon = b""
            self.request.settimeout(60)
            try:
                while True:
                    morceau = self.request.recv(4096)
                    if not morceau:
                        break
                    tampon += morceau
                    if tampon.startswith(VT) or b"MSH|" in tampon:  # HL7 / MLLP
                        if FS + CR in tampon:
                            self.request.sendall(VT + b"MSH|^~\\&|MEDMA\rMSA|AA\r" + FS + CR)
                            traiter(tampon, cfg, appareil, a_blanc)
                            tampon = b""
                    else:  # ASTM : poignée de main ENQ / ACK, une trame = un ACK, EOT = fin
                        if morceau.endswith(ENQ):
                            self.request.sendall(ACK)
                        elif ETX in morceau or ETB in morceau:
                            self.request.sendall(ACK)
                        if EOT in morceau:
                            traiter(tampon, cfg, appareil, a_blanc)
                            tampon = b""
            except OSError:
                pass

    class Serveur(socketserver.ThreadingTCPServer):
        allow_reuse_address = True

    with Serveur((cfg.get("ecoute", "0.0.0.0"), int(cfg.get("port", 5000))), Gestionnaire) as s:
        print(f"Écoute sur le port {cfg.get('port', 5000)} (ASTM / HL7). Ctrl+C pour arrêter.")
        s.serve_forever()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", default="config.json")
    p.add_argument("--a-blanc", action="store_true", help="affiche sans envoyer")
    p.add_argument("action", choices=["ecouter", "fichier", "rejouer"])
    p.add_argument("chemin", nargs="?")
    a = p.parse_args()
    cfg = charger(a.config) if os.path.exists(a.config) else {}
    if a.action == "ecouter":
        serveur(cfg, a.a_blanc)
    elif a.action == "fichier":
        with open(a.chemin, "rb") as f:
            traiter(f.read(), cfg, cfg.get("appareil", "fichier"), a.a_blanc)
    else:
        rejouer(cfg)


if __name__ == "__main__":
    main()
