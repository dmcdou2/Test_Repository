"""Batch 1 ranch-search data job. Probes each required service once (polite, 1 s gap,
UA ranch-search-job/1.0); records failures instead of filling gaps."""
import csv, json, time, zipfile, os, datetime, requests

UA = {"User-Agent": "ranch-search-job/1.0"}
ORIGIN = (-95.630, 29.784)
COUNTIES = ["Bandera","Blanco","Edwards","Gillespie","Kendall","Kerr","Kimble","Mason",
            "Medina","Menard","Real","Sutton","Uvalde"]
GAUGES = [("08195000","Frio River at Concan"),("08198000","Sabinal River near Sabinal"),
          ("08190000","Nueces River at Laguna"),("08190500","West Nueces River near Brackettville"),
          ("08165500","Guadalupe River at Hunt"),("08167000","Guadalupe River at Comfort"),
          ("08150000","Llano River near Junction"),("08151500","Llano River at Llano"),
          ("08178880","Medina River at Bandera"),("08144500","San Saba River at Menard"),
          ("08153500","Pedernales River near Johnson City"),("08171000","Blanco River at Wimberley")]
W = dict(lon0=-101.05, lon1=-97.50, lat0=28.98, lat1=31.18)
listings = [json.loads(l) for l in open("listings.jsonl")]
failures = []

def probe(step, url):
    """One GET; returns (response or None, error text)."""
    t = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        r = requests.get(url, headers=UA, timeout=30)
        if r.status_code == 200:
            return r, None
        err = f"HTTP {r.status_code}"
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
    failures.append(dict(step=step, url=url, time_utc=t, error=err))
    time.sleep(1)
    return None, err

def wcsv(name, header, rows):
    with open(name, "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)

# Step 1 / 2: parcels
PARCEL = "https://feature.geographic.texas.gov/arcgis/rest/services/Parcels/stratmap_land_parcels_48_most_recent/MapServer/0"
r, e1 = probe("1 parcel layer description", PARCEL + "?f=pjson")
assert r is None, "service reachable: full pipeline not implemented in failure-mode script"
note1 = f"not queried: layer description failed ({e1})"
wcsv("coverage.csv", ["county","parcel_count","data_date","status","note"],
     [[c, "", "", "unknown", note1] for c in COUNTIES])
json.dump({"type":"FeatureCollection","features":[]}, open("parcels.geojson","w"))
wcsv("parcel_matches.csv", ["listing_id","confidence","n_parcels","parcel_acres_total","acre_gap_pct","note"],
     [[l["id"], "none", 0, "", "", "parcel service unreachable; no candidates queried"] for l in listings])

# Step 3: OSRM — first route call fails -> stop step
l0 = listings[0]
r, e3 = probe("3 OSRM route (first call; step stopped)",
              f"https://router.project-osrm.org/route/v1/driving/{ORIGIN[0]},{ORIGIN[1]};{l0['lon']},{l0['lat']}?overview=false")
wcsv("drive_times.csv", ["listing_id","minutes","miles","snapped_lon","snapped_lat","snap_m","status"],
     [[l["id"],"","","","","", "not_run: OSRM unreachable (" + e3 + ")" if i else "failed: " + e3]
      for i, l in enumerate(listings)])
dx, dy = (W["lon1"]-W["lon0"])/20, (W["lat1"]-W["lat0"])/20
grid = [(round(W["lon0"]+(i+.5)*dx, 5), round(W["lat0"]+(j+.5)*dy, 5)) for j in range(20) for i in range(20)]
wcsv("drive_grid.csv", ["lon","lat","minutes","snapped_lon","snapped_lat","snap_m","status"],
     [[x, y, "", "", "", "", "not_run: OSRM unreachable"] for x, y in grid])

# Step 4: USGS
r, e4 = probe("4 USGS site service", "https://waterservices.usgs.gov/nwis/site/?format=rdb&sites="
              + ",".join(g[0] for g in GAUGES) + "&siteOutput=expanded")
wcsv("gauges.csv", ["site_no","site_name","name_source","lat","lon","days_of_record","pct_days_no_flow",
     "years_with_no_flow","longest_no_flow_streak_days","median_cfs","latest_date","latest_cfs",
     "latest_pctile","summary_20yr","status"],
     [[s, n, "job input (not verified)"] + [""]*11 + [f"not_run: USGS unreachable ({e4})"] for s, n in GAUGES])
wcsv("listing_gauges.csv", ["listing_id","site_no","site_name","river_match","distance_km","status"],
     [[l["id"],"","","","","not_run: gauge coordinates unavailable"] for l in listings])

# Step 5: market pull — probe each source once
for host in ["https://www.landwatch.com/","https://www.land.com/","https://www.landsoftexas.com/","https://www.har.com/"]:
    probe("5 market source", host)
wcsv("market_listings.csv", ["listing_id","name","county","acres","price","broker","broker_url","lat","lng",
     "water","topo","exotics","improvements","fence","irrigation","date_seen","source_url"], [])
wcsv("failures.csv", ["step","url","time_utc","error"], [[f[k] for k in ("step","url","time_utc","error")] for f in failures])
json.dump(failures, open("failures.json","w"), indent=1)
print(len(failures), "failures"); [print(f["step"], "|", f["error"][:160]) for f in failures]
