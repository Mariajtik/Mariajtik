#!/usr/bin/env python3
"""Generate assets/constellation.svg — one star per day of real commit activity.

The data (tools/constellation-data.json) is fetched from GitHub's GraphQL
contributions calendar. Refresh the data and re-run to redraw the sky.
"""
import datetime as dt
import json
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "tools" / "constellation-data.json"
OUT = ROOT / "assets" / "constellation.svg"

W, H = 1200, 440
PX0, PX1 = 70, 1140
PY0, PY1 = 96, 356
FONT = "Inter, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
MONO = "'JetBrains Mono', 'SF Mono', Menlo, Consolas, monospace"

# Profile palette: blue sky, warm-white stars, and the mint from the profile art.
SKY_TOP = "#0F1B2D"
SKY_MID = "#16263B"
SKY_BOTTOM = "#1F3A4D"
SKY_BLUE = "#2B5368"
STAR_WHITE = "#FFFBEA"
STAR_GLOW = "#FFF4D6"
MINT = "#9FD3B0"
TEXT = "#F4F7FA"
MUTED = "#C2D3DF"


def jitter(date: str) -> int:
    return zlib.crc32(date.encode()) % 1000


def star_radius(count: int) -> float:
    # Slightly larger than before, capped at 12px as requested.
    return min(2.4 + (count ** 0.5) * 2.0, 12.0)


def tier(count: int) -> str:
    # Every active day is shown as a warm-white star, like gerar.py.
    return STAR_WHITE


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

    # Consecutive-night runs.
    runs, cur = [], [active[0]["date"]]
    for prev, nxt in zip(active, active[1:]):
        if (dt.date.fromisoformat(nxt["date"]) - dt.date.fromisoformat(prev["date"])).days == 1:
            cur.append(nxt["date"])
        else:
            runs.append(cur)
            cur = [nxt["date"]]
    runs.append(cur)
    longest = max(runs, key=len)

    # Month ticks.
    ticks = []
    month = d0.replace(day=1)
    while month <= d1:
        if month > d0:
            ticks.append(month)
        month = (month.replace(day=28) + dt.timedelta(days=4)).replace(day=1)

    top3 = sorted(active, key=lambda d: -d["contributionCount"])[:3]
    el = []

    # Blue nebula and two comets.
    el.append(
        f'<g><animateTransform attributeName="transform" type="translate" values="0 0;26 -8;0 0" dur="22s" repeatCount="indefinite"/>'
        f'<ellipse cx="600" cy="220" rx="560" ry="86" fill="{SKY_BLUE}" opacity=".20" '
        'filter="url(#cblur)" transform="rotate(-7 600 220)">'
        '<animate attributeName="opacity" values=".16;.28;.16" dur="9s" repeatCount="indefinite"/>'
        '</ellipse></g>'
    )
    el.append(
        '<g opacity="0"><animate attributeName="opacity" values="0;.9;.9;0" keyTimes="0;.08;.75;1" dur="12s" begin="2.5s" repeatCount="indefinite"/>'
        f'<line x1="-64" y1="312" x2="-22" y2="300" stroke="{STAR_GLOW}" stroke-width="1.6" stroke-linecap="round" stroke-opacity=".9"/>'
        f'<circle cx="-22" cy="300" r="2.6" fill="{STAR_WHITE}"/>'
        '<animateTransform attributeName="transform" type="translate" values="0 0;1330 -130" dur="12s" begin="2.5s" repeatCount="indefinite"/></g>'
    )
    el.append(
        '<g opacity="0"><animate attributeName="opacity" values="0;.8;.8;0" keyTimes="0;.08;.75;1" dur="15s" begin="9s" repeatCount="indefinite"/>'
        f'<line x1="1268" y1="330" x2="1226" y2="318" stroke="{MINT}" stroke-width="1.4" stroke-linecap="round" stroke-opacity=".9"/>'
        f'<circle cx="1226" cy="318" r="2.2" fill="{STAR_WHITE}"/>'
        '<animateTransform attributeName="transform" type="translate" values="0 0;-1440 -150" dur="15s" begin="9s" repeatCount="indefinite"/></g>'
    )

    # Month gridlines and labels.
    for month in ticks:
        x = x_of(month.isoformat())
        el.append(
            f'<line x1="{x:.0f}" y1="{PY0 - 14}" x2="{x:.0f}" y2="{PY1 + 10}" '
            f'stroke="{MINT}" stroke-opacity=".16"/>'
        )
        el.append(
            f'<text x="{x:.0f}" y="{PY1 + 30}" text-anchor="middle" font-family="{MONO}" '
            f'font-size="12" font-weight="600" letter-spacing="1.6" fill="{MUTED}">'
            f'{month.strftime("%b").upper()}</text>'
        )

    # Streak lines: blue for runs, mint for the longest run.
    for run in runs:
        if len(run) < 2:
            continue
        points = " ".join(f"{stars[d][0]:.1f},{stars[d][1]:.1f}" for d in run)
        hot = run is longest
        stroke = MINT if hot else SKY_BLUE
        opacity = ".88" if hot else ".72"
        width = "2.5" if hot else "1.8"
        dash = "9 7" if hot else "5 9"
        offset = "-64" if hot else "-56"
        duration = "2.2" if hot else "3.0"
        el.append(
            f'<polyline points="{points}" fill="none" stroke="{stroke}" stroke-opacity="{opacity}" '
            f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="{dash}">'
            f'<animate attributeName="stroke-dashoffset" values="0;{offset}" dur="{duration}s" '
            'repeatCount="indefinite"/></polyline>'
        )

    # Warm-white stars; brighter days receive a breathing halo.
    for i, (date, (x, y, count)) in enumerate(sorted(stars.items())):
        radius = star_radius(count)
        colour = tier(count)
        if count >= 8:
            el.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius * 2.4:.1f}" fill="{STAR_GLOW}" opacity=".28" filter="url(#cblur)">'
                f'<animate attributeName="opacity" values=".22;.42;.22" dur="{3.4 + (i % 3) * 1.1:.1f}s" '
                f'begin="{(i % 5) * .5:.1f}s" repeatCount="indefinite"/></circle>'
            )
        el.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{colour}" fill-opacity=".98">'
            f'<animate attributeName="opacity" values="1;.72;1" dur="{2.1 + (i % 6) * .55:.1f}s" '
            f'begin="{(i % 8) * .37:.1f}s" repeatCount="indefinite"/></circle>'
        )
        el.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{max(radius * .38, 1):.1f}" fill="#FFFFFF" opacity=".96">'
            f'<animate attributeName="opacity" values=".96;.65;.96" dur="{2.1 + (i % 6) * .55:.1f}s" '
            f'begin="{(i % 8) * .37:.1f}s" repeatCount="indefinite"/></circle>'
        )

    # Cross flares and labels on the three busiest days.
    for k, day in enumerate(top3):
        x, y, count = stars[day["date"]]
        label = dt.date.fromisoformat(day["date"]).strftime("%b %d").upper()
        el.append(
            f'<g stroke="{STAR_GLOW}" stroke-opacity=".9" stroke-width="1.4">'
            f'<line x1="{x - 18:.0f}" y1="{y:.0f}" x2="{x - 9:.0f}" y2="{y:.0f}"/>'
            f'<line x1="{x + 9:.0f}" y1="{y:.0f}" x2="{x + 18:.0f}" y2="{y:.0f}"/>'
            f'<line x1="{x:.0f}" y1="{y - 18:.0f}" x2="{x:.0f}" y2="{y - 9:.0f}"/>'
            f'<line x1="{x:.0f}" y1="{y + 9:.0f}" x2="{x:.0f}" y2="{y + 18:.0f}"/></g>'
        )
        el.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="none" stroke="{STAR_GLOW}" stroke-opacity=".8" stroke-width="1.2">'
            f'<animate attributeName="r" values="6;30" dur="4.6s" begin="{k * 1.5:.1f}s" repeatCount="indefinite"/>'
            f'<animate attributeName="stroke-opacity" values=".8;0" dur="4.6s" begin="{k * 1.5:.1f}s" repeatCount="indefinite"/></circle>'
        )
        side = 1 if x < W - 190 else -1
        tx = x + side * 26
        anchor = "start" if side > 0 else "end"
        el.append(
            f'<text x="{tx:.0f}" y="{y - 12:.0f}" text-anchor="{anchor}" font-family="{MONO}" '
            f'font-size="12" font-weight="700" letter-spacing=".6" fill="{TEXT}">{label} · {count}</text>'
        )

    # Longest-run annotation.
    lx = sum(stars[d][0] for d in longest) / len(longest)
    ly = min(stars[d][1] for d in longest)
    el.append(
        f'<text x="{lx:.0f}" y="{max(ly - 26, 88):.0f}" text-anchor="middle" font-family="{MONO}" '
        f'font-size="12" font-weight="700" letter-spacing="1.4" fill="{MINT}">'
        f'LONGEST RUN · {len(longest)} DAYS</text>'
    )

    n_stars = len(stars)
    n_runs = sum(1 for run in runs if len(run) > 1)
    era = f"{span + 1} DAYS"
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="ct cd">
  <title id="ct">Commit constellation: {total} contributions across {n_stars} active days</title>
  <desc id="cd">A star map where each warm-white star is one day of real GitHub contribution activity; the blue sky matches the profile background and mint marks the longest streak.</desc>
  <defs>
    <linearGradient id="cbg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{SKY_TOP}"/>
      <stop offset="55%" stop-color="{SKY_MID}"/>
      <stop offset="100%" stop-color="{SKY_BOTTOM}"/>
    </linearGradient>
    <linearGradient id="crail" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{SKY_BLUE}"/>
      <stop offset="50%" stop-color="{STAR_WHITE}"/>
      <stop offset="100%" stop-color="{MINT}"/>
    </linearGradient>
    <filter id="cblur" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="16"/></filter>
    <clipPath id="cframe"><rect width="{W}" height="{H}" rx="20"/></clipPath>
  </defs>
  <g clip-path="url(#cframe)" font-family="{FONT}">
    <rect width="{W}" height="{H}" fill="url(#cbg)"/>
{chr(10).join(el)}
    <text x="70" y="52" font-family="{MONO}" font-size="15" font-weight="700" letter-spacing="2.6" fill="{TEXT}">COMMIT CONSTELLATION</text>
    <text x="70" y="72" font-family="{MONO}" font-size="11" font-weight="600" letter-spacing="1.4" fill="{MUTED}">{total} CONTRIBUTIONS · {n_stars} ACTIVE NIGHTS · {n_runs} STREAK RUNS · {era}</text>
    <text x="{W / 2:.0f}" y="{H - 16}" text-anchor="middle" font-family="{MONO}" font-size="11" font-weight="600" letter-spacing="1.2" fill="{MINT}">EACH WHITE STAR = ONE DAY OF ACTIVITY · MINT = LONGEST STREAK</text>
    <rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="19" fill="none" stroke="{MINT}" stroke-opacity=".42"/>
    <rect x="0" y="{H - 5}" width="{W}" height="5" rx="2.5" fill="url(#crail)"/>
  </g>
</svg>
'''


def main() -> None:
    cal = json.loads(DATA.read_text(encoding="utf-8"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(cal), encoding="utf-8")
    print(f"wrote {OUT.name} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
