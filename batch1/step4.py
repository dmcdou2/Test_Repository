import csv, json, math, datetime, statistics, bisect
from polite import get
from gaugesel import hav
sel = json.load(open("gauge_sel.json"))
META = sel["meta"]; SITES = sel["named"] + sel["extra"]
TODAY = "2026-10-02"
NOFLOW = 0.1
out, fails = [], []
def wy(d): return d.year + 1 if d.month >= 10 else d.year
for s in SITES:
    st, t, e = get("https://waterservices.usgs.gov/nwis/dv/", "4 dv", {"format": "json", "sites": s, "parameterCd": "00060",
                   "startDT": "2006-10-01", "endDT": TODAY}, timeout=180, headers={"Accept-Encoding": "identity"})
    row = dict(site_no=s, site_name=META[s]["name"], lat=META[s]["lat"], lon=META[s]["lon"], selection="named" if s in sel["named"] else "extra_nearest")
    if e:
        fails.append((s, e)); out.append({**row, "status": "failed: " + e[:200]}); continue
    ts = json.loads(t)["value"]["timeSeries"]
    # keep the primary daily-mean series (statistic 00003); if several, use the longest
    ts = [x for x in ts if any(o["value"] == "00003" for o in x["variable"]["options"]["option"] if o.get("optionCode"))] or ts
    if not ts:
        out.append({**row, "status": "no daily-mean series returned"}); continue
    best = max(ts, key=lambda x: len(x["values"][0]["value"]))
    nd = best["variable"]["noDataValue"]
    vals = []
    for v in best["values"][0]["value"]:
        try: q = float(v["value"])
        except ValueError: continue
        if q == nd or q < 0: continue
        vals.append((datetime.date.fromisoformat(v["dateTime"][:10]), q, ",".join(v.get("qualifiers", []))))
    if not vals:
        out.append({**row, "status": "series empty"}); continue
    vals.sort()
    dry = [q <= NOFLOW for _, q, _ in vals]
    longest = cur = 0
    prev = None
    for (d, q, _), z in zip(vals, dry):
        cur = cur + 1 if z and prev and (d - prev).days == 1 and cur else (1 if z else 0)
        longest = max(longest, cur); prev = d
    wys = sorted({wy(d) for d, _, _ in vals})
    dry_wys = sorted({wy(d) for (d, _, _), z in zip(vals, dry) if z})
    ld, lq, lqual = vals[-1]
    wk = ld.isocalendar()[1]
    hist = sorted(q for d, q, _ in vals[:-1] if d.isocalendar()[1] == wk)
    pct = round(100 * (bisect.bisect_left(hist, lq) + 0.5 * (bisect.bisect_right(hist, lq) - bisect.bisect_left(hist, lq))) / len(hist), 1) if hist else ""
    pnf = round(100 * sum(dry) / len(vals), 2)
    med = round(statistics.median(q for _, q, _ in vals), 2)
    out.append({**row, "first_date": vals[0][0].isoformat(), "days_of_record": len(vals), "pct_days_no_flow": pnf,
                "years_with_no_flow": len(dry_wys), "water_years_covered": len(wys), "longest_no_flow_streak_days": longest,
                "median_cfs": med, "latest_date": ld.isoformat(), "latest_cfs": lq, "latest_qualifiers": lqual,
                "latest_pctile": pct, "latest_week_n": len(hist),
                "summary_20yr": f"WY{wys[0]}-WY{wys[-1]}: {len(vals)} days, no flow (<= {NOFLOW} cfs) on {pnf}% of days in {len(dry_wys)} of {len(wys)} water years, longest dry spell {longest} d, median {med} cfs; latest {lq} cfs on {ld} = {pct} pctile for ISO week {wk}",
                "status": "ok"})
cols = ["site_no", "site_name", "selection", "lat", "lon", "first_date", "days_of_record", "pct_days_no_flow", "years_with_no_flow",
        "water_years_covered", "longest_no_flow_streak_days", "median_cfs", "latest_date", "latest_cfs", "latest_qualifiers",
        "latest_pctile", "latest_week_n", "summary_20yr", "status"]
with open("gauges.csv", "w", newline="") as f:
    w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(out)

# listing -> gauge
RIVER = {  # river known from listing name / URL / map, with basis
    "fmm": ("Llano", "listing name 'on the Llano'"),
    "dun": ("San Saba", "'River Ranch' in Menard County; San Saba is the river through Menard (map)"),
    "boh": ("Guadalupe", "'River Ranch', URL 'e-comfort'; Guadalupe flows through Comfort (map)"),
}
ok = [g for g in out if g["status"] == "ok"]
L = [json.loads(l) for l in open("listings.jsonl")]
with open("listing_gauges.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["listing_id", "site_no", "site_name", "river_match", "distance_km", "river_basis"])
    for l in L:
        dist = lambda g: hav(l["lat"], l["lon"], g["lat"], g["lon"])
        pool, match, basis = ok, "nearest", "river not stated in listing"
        if l["id"] in RIVER:
            rv, basis = RIVER[l["id"]]
            same = [g for g in ok if g["site_name"].startswith(rv + " Rv")]
            if same: pool, match = same, "same_river"
            else: basis += "; no same-river gauge with data (failed download), nearest used"
        g = min(pool, key=dist)
        w.writerow([l["id"], g["site_no"], g["site_name"], match, round(dist(g), 1), basis])
json.dump(fails, open("step4_meta.json", "w"))
print(fails)
for g in out: print(g["site_no"], g["status"], g.get("days_of_record"), g.get("pct_days_no_flow"), g.get("latest_date"), g.get("latest_cfs"), g.get("latest_pctile"))
