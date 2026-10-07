"""Second pass on rows flagged only by 'dead/sold words near top': record the matched phrase
with context, and look for a status marker outside nav menus. Same UA/pacing as linkcheck.py."""
import csv, re, time, requests
from linkcheck_common import UA, DEAD
R = [r for r in csv.DictReader(open("linkcheck.csv")) if "dead/sold words near top" in r["flags"]]
out = []
for r in R:
    rec = dict(id=r["id"], url=r["url"])
    try:
        body = requests.get(r["url"], headers={"User-Agent": UA, "Accept": "text/html"}, timeout=25).text[:400000]
        nonav = re.sub(r"<(nav|header|footer)\b.*?</\1>", " ", body, flags=re.S | re.I)
        txt = lambda h: re.sub(r"\s+", " ", re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", h, flags=re.S))
        full, main = txt(body), txt(nonav)
        m = DEAD.search(full[:1500])
        rec["matched"] = m.group(0) if m else ""
        rec["context"] = full[max(0, m.start() - 50): m.end() + 50].strip() if m else ""
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S | re.I)
        rec["h1"] = txt(h1.group(1)).strip()[:80] if h1 else ""
        st = re.search(r"(status|listing status)\W{0,20}(active|for sale|sold|under contract|pending|off[- ]market)", main, re.I)
        badge = re.search(r"\b(SOLD|UNDER CONTRACT|SALE PENDING|PENDING)\b", main[:3000])
        rec["status_marker"] = st.group(0)[:60] if st else (badge.group(0) if badge else "")
        m2 = DEAD.search(main[:1500])
        rec["dead_words_outside_nav"] = m2.group(0) if m2 else ""
    except Exception as e:
        rec["matched"] = "ERR " + str(e)[:80]
    out.append(rec)
    time.sleep(1.0)
with open("linkcheck_triage.csv", "w", newline="") as f:
    w = csv.DictWriter(f, ["id", "url", "matched", "context", "h1", "status_marker", "dead_words_outside_nav"]); w.writeheader(); w.writerows(out)
