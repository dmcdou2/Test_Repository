"""Batch 1b Step 4: retry the two missing gauges up to 5x each, 2 min apart, uncompressed."""
import json, time
from polite import get
PENDING = {"08144500": None, "08153500": None}
for attempt in range(1, 6):
    for s in [k for k, v in PENDING.items() if v is None]:
        st, t, e = get("https://waterservices.usgs.gov/nwis/dv/", f"4b dv retry {attempt}",
                       {"format": "json", "sites": s, "parameterCd": "00060", "startDT": "2006-10-01", "endDT": "2026-10-02"},
                       timeout=180, headers={"Accept-Encoding": "identity"}, cache=False)
        ok = e is None and t.lstrip().startswith("{")
        if ok:
            try: json.loads(t)
            except ValueError as x: ok, e = False, f"JSON parse: {x}"
        print(time.strftime("%H:%M:%S"), s, attempt, "ok" if ok else (e or "")[:120], flush=True)
        if ok:
            PENDING[s] = attempt
    if all(v is not None for v in PENDING.values()) or attempt == 5:
        break
    time.sleep(120)
json.dump(PENDING, open("step4b_result.json", "w"))
print("done", PENDING, flush=True)
