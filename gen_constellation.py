#!/usr/bin/env python3
"""Generate assets/constellation.svg from real GitHub contribution data."""

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

# Palette sampled from the profile's ceu.template.svg / bg.jpg theme:
# deep midnight blue through the recognizable blue-teal sky, white stars,
# and the same mint green used for “Thank you to every star that shines here.”
SKY_DARK = "#050A18"
SKY_MID = "#0D1B33"
SKY_BLUE = "#1F3A4D"
STAR_WHITE = "#FFFBEA"
STAR_GLOW = "#FFF4D6"
MINT = "#9FD3B0"
TEXT = "#FFF4D6"
MUTED = "#C2D3DF"


def jitter(date: str) -> int:
    return zlib.crc32(date.encode()) % 1000


def star_radius(count: int) -> float:
    return min(1.9 + (count ** 0.5) * 1.75, 12.0)


def build(cal: dict) -> str:
    days = [day for week in cal["weeks"] for day in week["contributionDays"]]
    total = cal["totalContributions"]
    active = [day for day in days if day["contributionCount"] > 0]
    if not active:
        raise SystemExit("no active days in data — nothing to plot")

    d0 = dt.date.fromisoformat(days[0]["date"])
    d1 = dt.date.fromisoformat(days[-1]["date"])
    span = max((d1 - d0).days, 1)

    def x_of(date: str) -> float:
        return PX0 + ((dt.date.fromisoformat(date) - d0).days / span) * (PX1 - PX0)

    def y_of(date: str) -> float:
        return PY0 + (jitter(date) / 1000) * (PY1 - PY0)

    stars = {
        day["date"]: (x_of(day["date"]), y_of(day["date"]), day["contributionCount"])
        for day in active
    }

    # Consecutive activity runs.
    runs, current = [], [active[0]["date"]]
    for previous, following in zip(active, active[1:]):
        if (dt.date.fromisoformat(following["date"]) - dt.date.fromisoformat(previous["date"])).days == 1:
            current.append(following["date"])
        else:
            runs.append(current)
            current = [following["date"]]
    runs.append(current)
    longest = max(runs, key=len)

    # Month markers.
    ticks = []
    month = d0.replace(day=1)
    while month <= d1:
        if month > d0:
            ticks.append(month)
        month = (month.replace(day=28) + dt.timedelta(days=4)).replace(day=1)

    top3 = sorted(active, key=lambda day: -day["contributionCount"])[:3]
    elements = []

    # Soft blue nebula, matching the blue of the profile background.
    elements.append(
        f'<ellipse cx="600" cy="220" rx="560" ry="86" fill=""{SKY_BLUE}"" '
        'opacity=".32" filter="url(#blur)" transform="rotate(-7 600 220)"/>'
    )

    for month in ticks:
        x = x_of(month.isoformat())
        elements.append(
            f'<line x1="{x:.0f}" y1="{PY0 - 14}" x2="{x:.0f}" y2="{PY1 + 10}" '
            f'stroke="{MINT}" stroke-opacity=".16"/>'
        )
        elements.append(
            f'<text x="{x:.0f}" y="{PY1 + 30}" text-anchor="middle" font-family="{MONO}" '
            f'font-size="13" font-weight="600" letter-spacing="1.6" fill="{MUTED}">'
            f'{month.strftime("%b").upper()}</text>'
        )

    # Connect consecutive active days. Mint highlights the longest run.
    for run in runs:
        if len(run) < 2:
            continue
        points = " ".join(f"{stars[date][0]:.1f},{stars[date][1]:.1f}" for date in run)
        color = MINT if run is longest else SKY_BLUE
        opacity = ".9" if run is longest else ".72"
        width = "2.5" if run is longest else "1.8"
        elements.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" '
            f'stroke-opacity="{opacity}" stroke-width="{width}" stroke-linecap="round" '
            'stroke-linejoin="round" stroke-dasharray="7 6">'
            '<animate attributeName="stroke-dashoffset" values="0;-52" dur="3s" '
            'repeatCount="indefinite"/></polyline>'
        )

    # White stars; larger contribution days get a clear warm-white halo.
    for index, (date, (x, y, count)) in enumerate(sorted(stars.items())):
        radius = star_radius(count)
        if count >= 8:
            elements.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius * 2.8:.1f}" '
                f'fill="{STAR_GLOW}" opacity=".38" filter="url(#blur)">'
                f'<animate attributeName="opacity" values=".28;.55;.28" '
                f'dur="{3.4 + (index % 3) * 1.1:.1f}s" repeatCount="indefinite"/></circle>'
            )
        elements.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{STAR_WHITE}" '
            'stroke="#FFFFFF" stroke-width=".8" stroke-opacity=".9">'
            f'<animate attributeName="opacity" values="1;.72;1" '
            f'dur="{2.1 + (index % 6) * .55:.1f}s" repeatCount="indefinite"/></circle>'
        )
        elements.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{max(radius * .35, 1):.1f}" '
            'fill="#FFFFFF" opacity=".96"/>'
        )

    # Mark and label the three busiest days.
    for day in top3:
        x, y, count = stars[day["date"]]
        label = dt.date.fromisoformat(day["date"]).strftime("%b %d").upper()
        elements.append(
            f'<path d="M{x - 15:.0f} {y:.0f}H{x + 15:.0f} M{x:.0f} {y - 15:.0f}V{y + 15:.0f}" '
            f'stroke="{STAR_GLOW}" stroke-width="1.5" stroke-opacity=".9"/>'
        )
        side = 1 if x < W - 190 else -1
        tx = x + side * 23
        anchor = "start" if side > 0 else "end"
        elements.append(
            f'<text x="{tx:.0f}" y="{y - 13:.0f}" text-anchor="{anchor}" '
            f'font-family="{MONO}" font-size="12" font-weight="700" fill="{TEXT}" '
            f'stroke="{SKY_DARK}" stroke-width="3" paint-order="stroke">{label} · {count}</text>'
        )

    longest_x = sum(stars[date][0] for date in longest) / len(longest)
    longest_y = min(stars[date][1] for date in longest)
    elements.append(
        f'<text x="{longest_x:.0f}" y="{max(longest_y - 24, 91):.0f}" text-anchor="middle" '
        f'font-family="{MONO}" font-size="12" font-weight="700" letter-spacing="1.2" '
        f'fill="{MINT}" stroke="{SKY_DARK}" stroke-width="3" paint-order="stroke">'
        f'LONGEST RUN · {len(longest)} DAYS</text>'
    )

    active_days = len(stars)
    streak_runs = sum(1 for run in runs if len(run) > 1)
    era = f"{span + 1} DAYS"

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">
  <title id="title">Constelação de contribuições: {total} contribuições em {active_days} dias ativos</title>
  <desc id="desc">Mapa de estrelas baseado na atividade real do GitHub. Estrelas brancas representam dias ativos, o azul vem do céu do perfil e o verde menta destaca a sequência mais longa.</desc>
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{SKY_DARK}"/>
      <stop offset="58%" stop-color="{SKY_MID}"/>
      <stop offset="100%" stop-color="{SKY_BLUE}"/>
    </linearGradient>
    <filter id="blur" x="-80%" y="-80%" width="260%" height="260%">
      <feGaussianBlur stdDeviation="13"/>
    </filter>
    <clipPath id="frame"><rect width="{W}" height="{H}" rx="20"/></clipPath>
  </defs>
  <g clip-path="url(#frame)" font-family="{FONT}">
    <rect width="{W}" height="{H}" fill="url(#sky)"/>
    {''.join(elements)}
    <text x="70" y="49" font-family="{MONO}" font-size="17" font-weight="700" letter-spacing="2.4" fill="{TEXT}">COMMIT CONSTELLATION</text>
    <text x="70" y="74" font-family="{MONO}" font-size="12" font-weight="600" letter-spacing="1.2" fill="{MUTED}">{total} CONTRIBUTIONS · {active_days} ACTIVE NIGHTS · {streak_runs} STREAK RUNS · {era}</text>
    <text x="{W / 2:.0f}" y="{H - 14}" text-anchor="middle" font-family="{MONO}" font-size="11" font-weight="600" letter-spacing="1.1" fill="{MINT}">EACH WHITE STAR = A DAY OF ACTIVITY · MINT = LONGEST STREAK</text>
    <rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="19" fill="none" stroke="{MINT}" stroke-opacity=".48"/>
    <rect x="0" y="{H - 4}" width="{W}" height="4" fill="{MINT}" opacity=".9"/>
  </g>
</svg>
'''


def main() -> None:
    calendar = json.loads(DATA.read_text(encoding="utf-8"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(calendar), encoding="utf-8")
    print(f"wrote {OUT.name} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
