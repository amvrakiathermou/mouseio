# Μετατροπέας: Excel (v3) -> data.js / data.json για την εφαρμογή + αναφορά λαθών
# Χρήση: python converter.py protypo.xlsx φάκελος_αρχείων φάκελος_εξόδου
import sys, json, os
from openpyxl import load_workbook
S = {"M":"01 Μουσικοί","F":"02 Οικογένειες","O":"03 Όργανα","A":"04 Ηχογραφήσεις","V":"05 Βίντεο","P":"06 Φωτογραφίες","E":"07 Εκδηλώσεις","H":"08 Ιστορική διαδρομή","T":"09 Μαρτυρίες","N":"10 Νέα γενιά"}
xl, media, out = sys.argv[1:4]; wb = load_workbook(xl); errs = []
def rows(c):
    ws = wb[S[c]]; hs = [None if (x.value or "").startswith("🔒") else (x.value or "").lstrip("★✎ ").strip() for x in ws[1]]; res = []
    for r in range(2, ws.max_row + 1):
        if ws.cell(r, 2).value in (None, ""): continue
        d = {h: ws.cell(r, i + 1).value for i, h in enumerate(hs) if h and ws.cell(r, i + 1).value not in (None, "")}
        if d.get("Δημοσίευση (κενό = Ναι)") == "Όχι": continue
        d["id"] = f"{c}{r-1:03d}"; res.append(d)
    return res
R = {c: rows(c) for c in S}; N2I = {}
for c in S:
    m = {}
    for d in R[c]:
        n = d.get("Ονοματεπώνυμο") or d.get("Όνομα οικογένειας") or d.get("Όνομα οργάνου") or d.get("Τίτλος") or d.get("Λεζάντα"); d["_n"] = n
        if n in m: errs.append(f"Διπλό όνομα στο φύλλο {S[c]}: {n}")
        m[n] = d["id"]
    N2I[c] = m
def ids(d, prefixes, c):
    res = []
    for k, v in d.items():
        if any(k.startswith(p) for p in prefixes):
            i = N2I[c].get(v)
            if i: res.append(i)
            else: errs.append(f"{d['id']}: άγνωστο όνομα «{v}»")
    return res
mus = lambda d: ids(d, ("Μουσικός", "Σχετικός μουσικός", "Αφορά μουσικό"), "M")
one = lambda d, k, c: N2I[c].get(d.get(k)) if d.get(k) else None
def find(folder, pid, exts, need=True):
    for e in exts:
        for x in (e, e.upper()):
            if os.path.exists(f"{media}/{folder}/{pid}.{x}"): return f"{folder}/{pid}.{x}"
    if need: errs.append(f"Λείπει το αρχείο {folder}/{pid}")
    return ""
IMG = ["jpg", "jpeg", "png", "webp"]
photos = [dict(id=d["id"], name=d["_n"], year=d.get("Έτος"), place=d.get("Τόπος"), src=d.get("Φωτογράφος / πηγή"), file=find("img", d["id"], IMG), musicians=mus(d), evt=one(d, "Εκδήλωση", "E")) for d in R["P"]]
def cover(col, c, name):
    for d in R["P"]:
        if d.get(col) == name: return d["id"]
recs = [dict(id=d["id"], title=d["_n"], year=d.get("Έτος"), place=d.get("Τόπος"), musicians=mus(d), inst=ids(d, ("Όργανο",), "O"), evt=one(d, "Εκδήλωση", "E"), file=find("audio", d["id"], ["mp3", "m4a", "aac", "ogg", "wav"])) for d in R["A"]]
vids = [dict(id=d["id"], title=d["_n"], file=find("video", d["id"], ["mp4"], need=not d.get("Σύνδεσμος YouTube (για ίντερνετ και κινητά)")), link=d.get("Σύνδεσμος YouTube (για ίντερνετ και κινητά)"), musicians=mus(d), cover=cover("Εξώφυλλο βίντεο", "V", d["_n"])) for d in R["V"]]
events = [dict(id=d["id"], title=d["_n"], date=d.get("Ημερομηνία / περίοδος"), place=d.get("Τόπος"), text=d.get("Περιγραφή"), musicians=mus(d), cover=cover("Φωτογραφία εκδήλωσης", "E", d["_n"])) for d in R["E"]]
hist = [dict(id=d["id"], title=d["_n"], period=d.get("Περίοδος (π.χ. 1900–1930)"), text=d.get("Κείμενο"), musicians=mus(d)) for d in R["H"]]
tes = [dict(id=d["id"], title=d["_n"], narrator=one(d, "Αφηγητής", "M"), when=d.get("Ημερομηνία καταγραφής"), text=d.get("Κείμενο της μαρτυρίας"), musicians=mus(d)) for d in R["T"]]
newg = [dict(id=d["id"], title=d["_n"], text=d.get("Περιγραφή"), musicians=mus(d)) for d in R["N"]]
musicians = []
for d in R["M"]:
    i = d["id"]; ph = [p["id"] for p in photos if i in p["musicians"]]; prof = cover("Φωτογραφία προφίλ του μουσικού", "M", d["_n"])
    if not prof: errs.append(f"{d['_n']}: δεν έχει οριστεί φωτογραφία προφίλ (παίρνει την πρώτη)")
    collab = ids(d, ("Συνεργάτης",), "M")
    musicians.append(dict(id=i, name=d["_n"], born=d.get("Έτος γέννησης"), died=d.get("Έτος θανάτου (κενό αν ζει)"), period=d.get("Περίοδος δραστηριότητας"), origin=d.get("Τόπος καταγωγής"), groups=d.get("Μουσικά σχήματα (π.χ. Κομπανία Παπά)"), tag=d.get("Σύντομη φράση «σε μια ματιά»"), quote=d.get("Φράση του μουσικού (προαιρετική)"), bio=d.get("Βιογραφικό", ""),
        inst=ids(d, ("Όργανο",), "O"), fam=one(d, "Οικογένεια", "F"), collab=collab, photo=prof or (ph[0] if ph else ""), photos=ph,
        recs=[r["id"] for r in recs if i in r["musicians"]], vids=[v["id"] for v in vids if i in v["musicians"]], events=[e["id"] for e in events if i in e["musicians"]], tes=[t["id"] for t in tes if t["narrator"] == i or i in t["musicians"]]))
for m in musicians:   # οι συνεργασίες δείχνουν και προς τις δύο κατευθύνσεις
    for o in musicians:
        if m["id"] in o["collab"] and o["id"] not in m["collab"]: m["collab"].append(o["id"])
fams = [dict(id=d["id"], name=d["_n"], text=d.get("Περιγραφή"), members=[m["id"] for m in musicians if m["fam"] == d["id"]], cover=cover("Εξώφυλλο οικογένειας", "F", d["_n"])) for d in R["F"]]
insts = [dict(id=d["id"], name=d["_n"], cat=d.get("Κατηγορία"), text=d.get("Περιγραφή"), players=[m["id"] for m in musicians if d["id"] in m["inst"]], cover=cover("Φωτογραφία οργάνου", "O", d["_n"])) for d in R["O"]]
data = dict(musicians=musicians, families=fams, instruments=insts, recordings=recs, videos=vids, photos=photos, events=events, history=hist, testimonies=tes, newgen=newg)
os.makedirs(out, exist_ok=True)
js = json.dumps(data, ensure_ascii=False)
open(f"{out}/data.json", "w", encoding="utf-8").write(js); open(f"{out}/data.js", "w", encoding="utf-8").write("const DATA=" + js + ";")
open(f"{out}/report.txt", "w", encoding="utf-8").write("\n".join(errs) or "Κανένα λάθος.")
print("Εγγραφές:", {k: len(v) for k, v in data.items()}); print("Αναφορά:", errs or "κανένα λάθος")
