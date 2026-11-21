# Connexion des automates de laboratoire (LIS)

Un **agent local** (`deploy/lis/lis_agent.py`, bibliothèque standard Python 3) reçoit les résultats de l'automate
(**ASTM E1394 / LIS2-A2** ou **HL7 v2**, par TCP ou fichier) et les envoie à MedMa
(`medma_ma.lis.recevoir_resultats`). Les résultats arrivent dans l'analyse **en brouillon** : le technicien relit,
puis valide. Jamais de validation automatique.

```
Automate ──(ASTM/HL7, TCP ou fichier)──▶ PC du laboratoire (lis_agent.py) ──HTTPS──▶ MedMa
```

## État de validation (honnêteté)
- Analyse ASTM (trames STX/ETX) et HL7 (MLLP) : **testée** avec des messages simulés (tests automatisés).
- Écoute TCP (poignée de main ENQ/ACK, ACK MLLP) : **testée** en local avec un client simulé.
- Inscription des résultats côté MedMa (brouillon, refus des analyses validées, paramètres non reconnus rapportés) : **testée**.
- **Non testé** : un automate réel (chaque marque a ses variantes de champs) et l'envoi HTTPS avec clé API.
  Prévoir une phase de recette avec le manuel d'interface de l'appareil.

## Mise en place
1. **Compte et clés API** : créer (ou utiliser) un utilisateur du laboratoire (rôle *Laboratory User*) → *Paramètres API →
   Générer des clés*. Ne jamais mettre ces clés dans le dépôt.
2. Copier `deploy/lis/config.exemple.json` en `config.json` et renseigner `url`, `api_key`, `api_secret`, `appareil`, `port`.
3. **Correspondance** (`correspondance`) : code de l'automate → libellé du paramètre MedMa
   (celui de la colonne « Event » ou « Test Name » de la ligne de résultat). Un code non listé est essayé tel quel.
4. **Code-barres de l'échantillon = numéro de l'analyse MedMa** (ex. `HLC-LAB-2026-00031`) : c'est ainsi que le résultat
   retrouve l'analyse. Configurer l'automate (ou l'imprimante d'étiquettes) en conséquence.
5. Paramétrer l'automate : adresse du PC, port (`port` du config), protocole ASTM ou HL7.
6. Lancer :
   ```bash
   python3 lis_agent.py --config config.json ecouter
   ```
   Essai à blanc (sans envoi) : `python3 lis_agent.py --a-blanc fichier exemple_astm.txt`.

## Robustesse
- Chaque message brut est conservé dans `donnees/brut/` (trace d'audit).
- Si MedMa est injoignable, le résultat est mis en file dans `donnees/attente/` ; `python3 lis_agent.py rejouer` le renvoie.
- Paramètre non reconnu ou analyse déjà validée : rapporté dans la réponse et au journal, jamais ignoré en silence.

## À prévoir avec chaque marque
Mindray, Sysmex, Roche, Abbott… : demander le **manuel d'interface (LIS / Interface Manual)** et vérifier le format
des champs `O` / `R` (ASTM) ou `OBR` / `OBX` (HL7), l'identifiant de l'échantillon et les codes de test.
Certaines marques exigent une licence LIS ou l'intervention de leur technicien.
