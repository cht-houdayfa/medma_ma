import csv, html, re, sys, time, urllib.request

URL = "https://ammps.gov.ma/recherche-medicaments?page=%d"
OUT = "ammps_raw.csv"
COLS = ["id", "nom", "dosage", "substance", "presentation", "forme", "ppv", "ph", "statut", "epi", "ppv_brut"]


def get(n):
    for essai in range(4):
        try:
            req = urllib.request.Request(URL % n, headers={"User-Agent": "Mozilla/5.0 (catalogue import, 1 req/s)"})
            return urllib.request.urlopen(req, timeout=40).read().decode("utf-8")
        except Exception:
            time.sleep(3 * (essai + 1))
    raise RuntimeError(f"page {n} inaccessible")


def txt(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def prix(s):
    s = txt(s).replace("DH", "").replace("\xa0", "").replace(" ", "")
    if not s:
        return ""
    if "," in s:  # 1.234,50 ou 55,90
        s = s.replace(".", "").replace(",", ".")
    else:  # 4.303.00 : le dernier point est la décimale
        m = re.match(r"^(\d[\d.]*)\.(\d{2})$", s)
        s = (m.group(1).replace(".", "") + "." + m.group(2)) if m else s.replace(".", "")
    return s if re.match(r"^\d+(\.\d+)?$", s) else ""


def cards(h):
    for blk in re.split(r'<div class="medicament-card"', h)[1:]:
        mid = re.search(r"#medicamentModal(\d+)", blk)
        g = lambda pat: (re.search(pat, blk, re.S) or [None, ""])[1]
        pr = re.findall(r"<small>(PPV|PH)</small>\s*<strong>(.*?)</strong>", blk, re.S)
        d = dict(pr)
        mod = re.search(r'id="medicamentModal%s".*?(?=<div class="modal fade"|$)' % (mid.group(1) if mid else "x"), h, re.S)
        epi = ""
        if mod:
            e = re.search(r'>EPI</span>\s*<span class="ammps-modal-value">(.*?)</span>', mod.group(0), re.S)
            epi = txt(e.group(1)) if e else ""
        yield {
            "id": mid.group(1) if mid else "",
            "nom": txt(g(r'medicament-title">(.*?)</h5>')),
            "dosage": txt(g(r"<strong>Dosage :</strong>(.*?)</div>")),
            "substance": txt(g(r"<strong>Substance active :</strong>(.*?)</div>")),
            "presentation": txt(g(r"<strong>Présentation :</strong>(.*?)</div>")),
            "forme": txt(g(r'medicament-forme">(.*?)</div>')),
            "ppv": prix(d.get("PPV")),
            "ph": prix(d.get("PH")),
            "statut": txt(g(r'status-pill[^"]*">(.*?)</span>')),
            "epi": epi,
            "ppv_brut": txt(d.get("PPV")),
        }


debut, fin = int(sys.argv[1]), int(sys.argv[2])
with open(OUT, "a", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, COLS, delimiter=";")
    if f.tell() == 0:
        w.writeheader()
    for n in range(debut, fin + 1):
        rows = list(cards(get(n)))
        w.writerows(rows)
        f.flush()
        print(n, len(rows), flush=True)
        time.sleep(1)
