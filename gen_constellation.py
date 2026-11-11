#!/usr/bin/env python3
"""Generate assets/constellation.svg from real GitHub contribution data."""

import datetime as dt
import json
import zlib
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "tools" / "constellation-data.json"
OUT = ROOT / "assets" / "constellation.svg"

W, H = 1200, 440
PX0, PX1 = 70, 1140
PY0, PY1 = 96, 356
FONT = "Inter, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
MONO = "'JetBrains Mono', 'SF Mono', Menlo, Consolas, monospace"

def jitter(date: str) -> int:
    return zlib.crc32(date.encode()) % 1000

def star_radius(count: int) -> float:
    return min(1.9 + (count ** 0.5) * 1.75, 12.0)

def tier(count: int) -> str:
    if count >= 20:
        return "#f5f3ff"
    if count >= 8:
        return "#67e8f9"
    return "#7d95c9"

def build(cal: dict) -> str:
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    total = cal["totalContributions"]
    active = [d for d in days if d["contributionCount"] > 0]
    if not active:
        raise SystemExit("no active days in data — nothing to plot")

    d0 = dt.date.fromisoformat(days[0]["date"])
    d1 = dt.date.fromisoformat(days[-1]["date"])
    span = max((d1 - d0).days, 1)

    def x_of(date: str) -> float:
        return PX0 + ((dt.date.fromisoformat(date) - d0).days / span) * (PX1 - PX0)

    def y_of(date: str) -> float:
        return PY0 + (jitter(date) / 1000) * (PY1 - PY0)

    stars = {d["date"]: (x_of(d["date"]), y_of(d["date"]), d["contributionCount"]) for d in active}

    runs, cur = [], [active[0]["date"]]
    for prev, nxt in zip(active, active[1:]):
        if (dt.date.fromisoformat(nxt["date"]) - dt.date.fromisoformat(prev["date"])).days == 1:
            cur.append(nxt["date"])
        else:
            runs.append(cur)
            cur = [nxt["date"]]
    runs.append(cur)
    longest = max(runs, key=len)

    ticks = []
    first = d0.replace(day=1)
    m = first
    while m <= d1:
        if m > d0:
            ticks.append(m)
        m = (m.replace(day=28) + dt.timedelta(days=4)).replace(day=1)

    top3 = sorted(active, key=lambda d: -d["contributionCount"])[:3]

    el = []
    el.append('    <g><animateTransform attributeName="transform" type="translate" values="0 0;26 -8;0 0" dur="22s" repeatCount="indefinite"/><ellipse cx="600" cy="220" rx="560" ry="86" fill="#818cf8" opacity=".07" filter="url(#cblur)" transform="rotate(-7 600 220)"><animate attributeName="opacity" values=".07;.12;.07" dur="9s" repeatCount="indefinite"/></ellipse></g>')

    for m in ticks:
        x = x_of(m.isoformat())
        el.append(f'    <line x1="{x:.0f}" y1="{PY0 - 14}" x2="{x:.0f}" y2="{PY1 + 10}" stroke="#9FD3B0" stroke-opacity=".10"/>')
        el.append(f'    <text x="{x:.0f}" y="{PY1 + 30}" text-anchor="middle" font-family="{MONO}" font-size="14" font-weight="600" letter-spacing="1.6" fill="#5c7595">{m.strftime("%b").upper()}</text>')

    for run in runs:
        if len(run) < 2:
            continue
        pts = " ".join(f"{stars[d][0]:.1f},{stars[d][1]:.1f}" for d in run)
        hot = run is longest
        el.append(f'    <polyline points="{pts}" fill="none" stroke="{"#c4b5fd" if hot else "#22d3ee"}" stroke-opacity="{".8" if hot else ".3"}" stroke-width="{2.2 if hot else 1.2}" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="{"9 7" if hot else "5 9"}"><animate attributeName="stroke-dashoffset" values="0;{"-64" if hot else "-56"}" dur="{2.2 if hot else 3.0}s" repeatCount="indefinite"/></polyline>')

    for i, (date, (x, y, c)) in enumerate(sorted(stars.items())):
        r = star_radius(c)
        colour = tier(c)
        if c >= 8:
            el.append(f'    <circle cx="{x:.1f}" cy="{y:.1f}" r="{r * 2.4:.1f}" fill="{colour}" opacity=".16" filter="url(#cblur)"><animate attributeName="opacity" values=".16;.28;.16" dur="{3.4 + (i % 3) * 1.1:.1f}s" begin="{(i % 5) * .5:.1f}s" repeatCount="indefinite"/></circle>')
        el.append(f'    <circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{colour}" fill-opacity=".95"><animate attributeName="opacity" values="1;.62;1" dur="{2.1 + (i % 6) * .55:.1f}s" begin="{(i % 8) * .37:.1f}s" repeatCount="indefinite"/></circle>')
        el.append(f'    <circle cx="{x:.1f}" cy="{y:.1f}" r="{max(r * .38, 1):.1f}" fill="#ffffff" opacity=".9"><animate attributeName="opacity" values=".9;.5;.9" dur="{2.1 + (i % 6) * .55:.1f}s" begin="{(i % 8) * .37:.1f}s" repeatCount="indefinite"/></circle>')

    for k, d in enumerate(top3):
        x, y, c = stars[d["date"]]
        lab = dt.date.fromisoformat(d["date"]).strftime("%b %d").upper()
        el.append(f'    <g stroke="#F4F7FA" stroke-opacity=".8" stroke-width="1.2"><line x1="{x - 18:.0f}" y1="{y:.0f}" x2="{x - 9:.0f}" y2="{y:.0f}"/><line x1="{x + 9:.0f}" y1="{y:.0f}" x2="{x + 18:.0f}" y2="{y:.0f}"/><line x1="{x:.0f}" y1="{y - 18:.0f}" x2="{x:.0f}" y2="{y - 9:.0f}"/><line x1="{x:.0f}" y1="{y + 9:.0f}" x2="{x:.0f}" y2="{y + 18:.0f}"/></g>')
        el.append(f'    <circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="none" stroke="#f5f3ff" stroke-opacity=".7" stroke-width="1.2"><animate attributeName="r" values="6;30" dur="4.6s" begin="{k * 1.5:.1f}s" repeatCount="indefinite"/><animate attributeName="stroke-opacity" values=".7;0" dur="4.6s" begin="{k * 1.5:.1f}s" repeatCount="indefinite"/></circle>')
        side = 1 if x < W - 190 else -1
        tx = x + side * 26
        el.append(f'    <text x="{tx:.0f}" y="{y - 12:.0f}" text-anchor="{"start" if side > 0 else "end"}" font-family="{MONO}" font-size="10.5" font-weight="700" letter-spacing=".6" fill="#F4F7FA">{lab} · {c}</text>')

    lx = sum(stars[d][0] for d in longest) / len(longest)
    ly = min(stars[d][1] for d in longest)
    el.append(f'    <text x="{lx:.0f}" y="{ly - 26:.0f}" text-anchor="middle" font-family="{MONO}" font-size="10.5" font-weight="700" letter-spacing="1.4" fill="#F4F7FA">LONGEST RUN · {len(longest)} NIGHTS</text>')

    n_stars, n_runs = len(stars), sum(1 for r in runs if len(r) > 1)
    era = f"{span + 1} DAYS"

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="ct cd">
  <title id="ct">Commit constellation: {total} contributions across {n_stars} active days across the recorded era</title>
  <desc id="cd">A star map where each star is one day of real commit activity, sized by volume, with lines connecting consecutive days and the longest streak highlighted.</desc>
  <defs>
    <linearGradient id="cbg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#16263B"/>
      <stop offset="55%" stop-color="#16263B"/>
      <stop offset="100%" stop-color="#16263B"/>
    </linearGradient>
    <filter id="cblur" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="16"/></filter>
  </defs>
  <g font-family="{FONT}">
    <rect width="{W}" height="{H}" fill="url(#cbg)"/>
{chr(10).join(el)}
    <text x="70" y="52" font-family="{MONO}" font-size="15" font-weight="700" letter-spacing="2.6" fill="#eef4ff">COMMIT CONSTELLATION</text>
    <text x="70" y="72" font-family="{MONO}" font-size="10.5" font-weight="600" letter-spacing="1.6" fill="#7d95b5">{total} CONTRIBUTIONS · {n_stars} ACTIVE NIGHTS · {n_runs} STREAK RUNS · {era}</text>
    <text x="{W / 2:.0f}" y="{H - 16}" text-anchor="middle" font-family="{MONO}" font-size="10" font-weight="600" letter-spacing="1.3" fill="#5c7595">EACH STAR = ONE DAY I SHIPPED · SIZE = VOLUME</text>
  </g>
</svg>
'''

def main() -> None:
    cal = json.loads(DATA.read_text())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(cal), encoding="utf-8")
    print(f"wrote {OUT.name} ({OUT.stat().st_size:,} bytes)")

if __name__ == "__main__":
    main()
