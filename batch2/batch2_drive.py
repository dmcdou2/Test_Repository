import json, time, csv, sys, requests

ORIGIN = (29.784, -95.630)     # (lat, lon) — Batch 1 ORIGIN (I-10 at Eldridge Pkwy, exit 753)
OSRM = "https://router.project-osrm.org/route/v1/driving/{},{};{},{}?overview=false"
rows = json.load(open("listings.json"))
out = []
for i, r in enumerate(rows, 1):
    url = OSRM.format(ORIGIN[1], ORIGIN[0], r["lon"], r["lat"])
    rec = dict(id=r["id"], name=r["name"], county=r["county"], lat=r["lat"], lon=r["lon"], pin=r["pin"])
    for attempt in range(4):
        try:
            j = requests.get(url, timeout=30, headers={"User-Agent": "ranch-search-job/1.0"}).json()
            if j.get("code") == "Ok":
                route = j["routes"][0]
                rec.update(min=round(route["duration"] / 60, 1),
                           mi=round(route["distance"] * 0.000621371, 1),
                           snap=round(j["waypoints"][1].get("distance", 0)))   # metres from pin to nearest road
                break
            rec["error"] = j.get("code", "unknown")
        except Exception as e:
            rec["error"] = str(e)[:80]
        time.sleep(3 * (attempt + 1))
    out.append(rec)
    print(f"{i:3d}/{len(rows)} {r['name'][:38]:38s} {rec.get('min','ERR')} min", file=sys.stderr)
    time.sleep(1.1)   # be polite to the public router

json.dump(dict(origin=ORIGIN, router="router.project-osrm.org", run=time.strftime("%Y-%m-%d"), results=out),
          open("drive_times.json", "w"), indent=1)
with open("drive_times.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["id", "name", "county", "min", "mi", "snap_m", "pin", "error"])
    for r in out: w.writerow([r["id"], r["name"], r["county"], r.get("min"), r.get("mi"), r.get("snap"), r["pin"], r.get("error", "")])
ok = sum(1 for r in out if "min" in r)
print(f"done: {ok} routed, {len(out) - ok} failed", file=sys.stderr)
