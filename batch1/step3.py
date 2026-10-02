import csv, json
from polite import get
O = (-95.630, 29.784)
BASE = "https://router.project-osrm.org"
M2MI = 1 / 1609.344
L = [json.loads(l) for l in open("listings.jsonl")]
fails, stopped = [], None
rows = []
for l in L:
    if stopped:
        rows.append([l["id"], "", "", "", "", "", f"not_run: step stopped ({stopped})"]); continue
    s, t, e = get(f"{BASE}/route/v1/driving/{O[0]},{O[1]};{l['lon']},{l['lat']}", "3 route", {"overview": "false"})
    d = json.loads(t) if t and t.startswith("{") else {}
    if e or d.get("code") != "Ok":
        msg = e or f"{d.get('code')}: {d.get('message')}"
        fails.append((l["id"], msg)); rows.append([l["id"], "", "", "", "", "", "failed: " + msg])
        if s in (429, None) or (s and s >= 500):
            stopped = msg
        continue
    r, wp = d["routes"][0], d["waypoints"][1]
    rows.append([l["id"], round(r["duration"] / 60, 1), round(r["distance"] * M2MI, 1),
                 round(wp["location"][0], 6), round(wp["location"][1], 6), round(wp["distance"], 1), "ok"])
with open("drive_times.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["listing_id", "minutes", "miles", "snapped_lon", "snapped_lat", "snap_m", "status"]); w.writerows(rows)

# grid: 20x20 cell centres
lon0, lon1, lat0, lat1 = -101.05, -97.50, 28.98, 31.18
dx, dy = (lon1 - lon0) / 20, (lat1 - lat0) / 20
grid = [(round(lon0 + (i + .5) * dx, 5), round(lat0 + (j + .5) * dy, 5)) for j in range(20) for i in range(20)]
grows = []
for k in range(0, 400, 99 if False else 80):  # 5 requests of 80 points (<=99 each)
    chunk = grid[k:k + 80]
    if stopped:
        grows += [[x, y, "", "", "", "", f"not_run: step stopped ({stopped})"] for x, y in chunk]; continue
    coords = ";".join(f"{x},{y}" for x, y in [O] + chunk)
    s, t, e = get(f"{BASE}/table/v1/driving/{coords}", "3 table",
                  {"sources": "0", "destinations": ";".join(str(i) for i in range(1, len(chunk) + 1))})
    d = json.loads(t) if t and t.startswith("{") else {}
    if e or d.get("code") != "Ok":
        msg = e or f"{d.get('code')}: {d.get('message')}"
        fails.append((f"grid {k}", msg)); grows += [[x, y, "", "", "", "", "failed: " + msg] for x, y in chunk]
        if s in (429, None) or (s and s >= 500):
            stopped = msg
        continue
    for (x, y), dur, wp in zip(chunk, d["durations"][0], d["destinations"]):
        grows.append([x, y, round(dur / 60, 1) if dur is not None else "",
                      round(wp["location"][0], 6), round(wp["location"][1], 6), round(wp["distance"], 1),
                      "ok" if dur is not None else "no_route"])
with open("drive_grid.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["lon", "lat", "minutes", "snapped_lon", "snapped_lat", "snap_m", "status"]); w.writerows(grows)
json.dump({"fails": fails, "stopped": stopped}, open("step3_meta.json", "w"), indent=1)
print(fails, stopped)
