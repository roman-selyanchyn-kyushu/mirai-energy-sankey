"""Download METI stte_<FY>.xlsx for a range of fiscal years, politely.

enecho.meti.go.jp sits behind an AWS WAF that answers a burst of requests with
HTTP 202 + x-amzn-waf-action: challenge and a zero-byte body. One request every
DELAY seconds stays under it; a challenge triggers a longer back-off and a plain
retry, never an attempt to defeat the check.

Usage:  python3 fetch_jp.py <first_fy> <last_fy>
Already-valid files are skipped, so the script is safe to re-run.
"""
import os, sys, time, urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
REF = "https://www.enecho.meti.go.jp/statistics/total_energy/results.html"
URL = "https://www.enecho.meti.go.jp/statistics/total_energy/xls/stte_{}.xlsx"
HERE = os.path.dirname(os.path.abspath(__file__))
DELAY, BACKOFF, TRIES = 40, 420, 8


def valid(path):
    """A real .xlsx is a zip archive; a WAF challenge is an empty body."""
    if not os.path.exists(path) or os.path.getsize(path) < 100_000:
        return False
    with open(path, "rb") as fh:
        return fh.read(2) == b"PK"


def fetch(year):
    path = os.path.join(HERE, f"stte_{year}.xlsx")
    if valid(path):
        return "cached", os.path.getsize(path)
    req = urllib.request.Request(URL.format(year), headers={"User-Agent": UA, "Referer": REF})
    for attempt in range(TRIES):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                body = r.read()
                if r.headers.get("x-amzn-waf-action") or len(body) < 100_000:
                    raise RuntimeError(f"challenged (HTTP {r.status}, {len(body)} bytes)")
                with open(path, "wb") as fh:
                    fh.write(body)
                if not valid(path):
                    os.remove(path)
                    raise RuntimeError("body was not a zip archive")
                return "ok", len(body)
        except Exception as e:
            if attempt == TRIES - 1:
                return f"FAILED: {e}", 0
            time.sleep(BACKOFF * (attempt + 1))
    return "FAILED", 0


def main():
    a, b = int(sys.argv[1]), int(sys.argv[2])
    years = [y for y in range(a, b + 1)]
    for i, y in enumerate(years):
        status, size = fetch(y)
        print(f"FY{y}  {status:52}{size:>10,}", flush=True)
        if status == "cached":
            continue
        if i != len(years) - 1:
            time.sleep(DELAY)


if __name__ == "__main__":
    main()
