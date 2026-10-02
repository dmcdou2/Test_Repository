"""Polite HTTP: one request at a time, >=1 s between calls to the same host,
UA ranch-search-job/1.0. Raw bodies cached under RAW (outside the bundle).
Every call is appended to calls.jsonl so budgets and failures can be audited."""
import json, os, time, hashlib, datetime, urllib.parse, requests

UA = {"User-Agent": "ranch-search-job/1.0"}
RAW = os.environ.get("RAW_DIR", "/tmp/claude-0/-home-user-Test-Repository/c2729f85-8bb1-5f0a-b560-aeba3a23ea41/scratchpad/raw")
os.makedirs(RAW, exist_ok=True)
_last = {}

def get(url, step, params=None, timeout=60, cache=True, headers=None):
    """Return (status, text, error). error is None on HTTP 200."""
    full = url + ("?" + urllib.parse.urlencode(params) if params else "")
    key = hashlib.sha1(full.encode()).hexdigest()
    path = os.path.join(RAW, key)
    if cache and os.path.exists(path):
        d = json.load(open(path))
        return d["status"], d["text"], d["error"]
    host = urllib.parse.urlparse(url).netloc
    wait = 1.0 - (time.time() - _last.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    status, text, err = None, "", None
    try:
        r = requests.get(full, headers={**UA, **(headers or {})}, timeout=timeout)
        status, text = r.status_code, r.text
        if r.status_code != 200:
            err = f"HTTP {r.status_code}: {r.text[:200]!r}"
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
    _last[host] = time.time()
    with open(os.path.join(os.path.dirname(__file__), "calls.jsonl"), "a") as f:
        f.write(json.dumps(dict(t=datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
                                step=step, host=host, url=full[:500], status=status, error=err)) + "\n")
    if err is None or (status and status < 500 and status != 429):
        json.dump(dict(status=status, text=text, error=err), open(path, "w"))
    return status, text, err
