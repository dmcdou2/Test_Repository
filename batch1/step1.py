import csv, json, datetime
from polite import get

LAYER = "https://feature.geographic.texas.gov/arcgis/rest/services/Parcels/stratmap_land_parcels_48_most_recent/MapServer/0"
COUNTIES = ["Bandera","Blanco","Edwards","Gillespie","Kendall","Kerr","Kimble","Mason",
            "Medina","Menard","Real","Sutton","Uvalde"]
fails = []
s, t, e = get(LAYER, "1 layer", {"f": "pjson"})
fields = [f["name"] for f in json.loads(t)["fields"]]

counts, used_name = {}, {}
for c in COUNTIES:
    n = None
    for name in (c, c.upper()):
        s, t, e = get(LAYER + "/query", "1 count", {"where": f"county='{name}'", "returnCountOnly": "true", "f": "json"})
        if e:
            fails.append(("1 count " + name, e)); break
        n = json.loads(t).get("count")
        if n:
            used_name[c] = name; break
    counts[c] = n

# one grouped statistics query for data dates (date_acq, tax_year, source)
names = [used_name[c] for c in COUNTIES if c in used_name]
stats = [{"statisticType": "max", "onStatisticField": "date_acq", "outStatisticFieldName": "max_date"},
         {"statisticType": "max", "onStatisticField": "tax_year", "outStatisticFieldName": "max_tax_year"},
         {"statisticType": "count", "onStatisticField": "objectid", "outStatisticFieldName": "n"}]
s, t, e = get(LAYER + "/query", "1 date stats", {"where": "county IN (" + ",".join(f"'{n}'" for n in names) + ")",
              "outStatistics": json.dumps(stats), "groupByFieldsForStatistics": "county,source", "f": "json"})
dates = {}
if e:
    fails.append(("1 date stats", e))
else:
    d = json.loads(t)
    if "error" in d:
        fails.append(("1 date stats", json.dumps(d["error"])[:300]))
    for ft in d.get("features", []):
        a = ft["attributes"]
        md = a["max_date"]
        if isinstance(md, (int, float)):
            md = datetime.datetime.utcfromtimestamp(md / 1000).date().isoformat()
        dates.setdefault(a["county"].title(), []).append((md, a["max_tax_year"], a["source"], a["n"]))

with open("coverage.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["county", "parcel_count", "data_date", "tax_year", "source", "county_value_in_layer", "status"])
    for c in COUNTIES:
        dl = sorted(dates.get(c, []), key=lambda x: -(x[3] or 0))
        dd = dl[0] if dl else ("", "", "", "")
        st = "present" if counts[c] else ("missing" if counts[c] == 0 else "unknown (query failed)")
        w.writerow([c, counts[c] if counts[c] is not None else "", dd[0] or "", dd[1] or "", dd[2] or "", used_name.get(c, ""), st])
json.dump({"fields": fields, "fails": fails, "dates_raw": dates}, open("step1_meta.json", "w"), indent=1, default=str)
print(open("coverage.csv").read()); print(fails)
