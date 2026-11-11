#!/usr/bin/env python3
"""Apply the profile repository palette and accessible contrast to the SVG."""
from pathlib import Path

svg_path = Path(__file__).resolve().parents[1] / "assets" / "constellation.svg"
svg = svg_path.read_text(encoding="utf-8")

# The SVG generator's pale background was paired with light text, making the
# labels almost impossible to read. Switch to the profile's navy/mint/coral
# palette and keep text bright against the dark background.
replacements = {
    "#BCE8BA": "#0F1B2D",  # navy
    "#C1E8FF": "#16263B",  # blue-navy
    "#F9FBFB": "#101C2E",  # deep navy
    "#eef4ff": "#F4F7FA",  # high-contrast text
    "#7d95b5": "#B6C7D9",  # secondary text
    "#5c7595": "#AFC2D4",  # month/footer labels
    "#8fb3dd": "#AFC2D4",  # grid/frame
    "#7d95c9": "#9FD3B0",  # mint stars
    "#67e8f9": "#8EDCF2",  # sky-blue stars
    "#f5f3ff": "#FF8A80",  # coral flares
    "#c4b5fd": "#FF6B5E",  # coral streak highlight
    "#e9d5ff": "#FFE4DF",  # bright warm labels
    "#818cf8": "#9FD3B0",  # mint nebula
}

for old, new in replacements.items():
    svg = svg.replace(old, new)

svg_path.write_text(svg, encoding="utf-8")
print(f"Updated constellation palette: {svg_path}")
