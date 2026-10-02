import json, math, collections
def rdb(p):
    L = [l.rstrip("\n").split("\t") for l in open(p) if not l.startswith("#")]
    h = L[0]; return [dict(zip(h, r)) for r in L[2:] if len(r) == len(h)]
def hav(a, b, c, d):
    p = math.pi / 180; x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))
if __name__ == "__main__":
  named = {r["site_no"]: r for r in rdb("sites_named.rdb")}
  bbox = {r["site_no"]: r for r in rdb("sites_bbox.rdb")}
  allg = {**bbox, **named}
  L = [json.loads(l) for l in open("listings.jsonl")]
  near = collections.Counter()
  for l in L:
      s = min(allg, key=lambda k: hav(l["lat"], l["lon"], float(allg[k]["dec_lat_va"]), float(allg[k]["dec_long_va"])))
      if s not in named: near[s] += 1
  extra = [s for s, _ in near.most_common(8)]
  for s, n in near.most_common(): print(s, n, allg[s]["station_nm"], s in extra)
  print("not in active bbox list:", [s for s in named if s not in bbox])
  json.dump({"named": list(named), "extra": extra, "meta": {k: {"name": v["station_nm"], "lat": float(v["dec_lat_va"]), "lon": float(v["dec_long_va"])} for k, v in allg.items()}}, open("gauge_sel.json", "w"), indent=1)
