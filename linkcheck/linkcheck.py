import json, time, csv, re, sys, requests

UA = ("Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
DEAD = re.compile(r"(not found|no longer available|page (cannot|can't) be found|404|"
                  r"listing (has )?(expired|been removed)|property (is )?(sold|no longer)|"
                  r"off[- ]market|under contract|sale pending|sold)", re.I)
rows = json.load(open("urls.json"))
out = []
for i, r in enumerate(rows, 1):
    rec = dict(id=r["id"], name=r["name"], broker=r["broker"], url=r["url"])
    try:
        resp = requests.get(r["url"], headers={"User-Agent": UA, "Accept": "text/html"},
                            timeout=25, allow_redirects=True)
        body = resp.text[:200000]
        m = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
        title = re.sub(r"\s+", " ", m.group(1)).strip()[:120] if m else ""
        flags = []
        if resp.status_code != 200: flags.append(f"http {resp.status_code}")
        if resp.url.rstrip("/") != r["url"].rstrip("/"): flags.append("redirected")
        if DEAD.search(title): flags.append("title: " + title[:60])
        # soft-404: short page or dead words in the first visible text
        text = re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", body, flags=re.S)
        text = re.sub(r"\s+", " ", text)[:4000]
        if len(text) < 300: flags.append("thin page")
        if resp.status_code == 200 and DEAD.search(text[:1500]) and "sold" not in title.lower():
            flags.append("dead/sold words near top")
        rec.update(status=resp.status_code, final_url=resp.url, title=title, flags="; ".join(flags))
    except Exception as e:
        rec.update(status="ERR", final_url="", title="", flags=str(e)[:100])
    out.append(rec)
    print(f"{i:3d}/{len(rows)} {rec['status']!s:4} {r['name'][:36]:36s} {rec['flags']}", file=sys.stderr)
    time.sleep(1.0)

with open("linkcheck.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["id", "name", "broker", "url", "status", "final_url", "title", "flags"])
    w.writeheader(); w.writerows(out)
bad = [o for o in out if o["flags"]]
print(f"done: {len(out)} checked, {len(bad)} flagged", file=sys.stderr)
