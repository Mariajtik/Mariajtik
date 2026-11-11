import os, json, math, random, urllib.request

U, META = "Mariajtik", 20

def api(p):
    r = urllib.request.Request("https://api.github.com/" + p, headers={
        "Authorization": "Bearer " + os.environ.get("GH_TOKEN", ""), "User-Agent": "gerar"})
    return json.load(urllib.request.urlopen(r))

stars = sum(r["stargazers_count"] for r in api(f"users/{U}/repos?per_page=100"))
fol = api(f"users/{U}")["followers"]

# Capricornus: (nome, RA em horas, Dec em graus, raio, rótulo)
CAP = [
    ("Algedi", 20.30, -12.5, 3.4, "Algedi"),
    ("Dabih", 20.35, -14.8, 3.6, "Dabih"),
    ("psi", 20.77, -25.3, 3.0, ""),
    ("omega", 20.85, -26.9, 2.8, ""),
    ("zeta", 21.44, -22.4, 3.0, ""),
    ("epsilon", 21.62, -19.5, 2.8, ""),
    ("kappa", 21.78, -18.9, 2.6, ""),
    ("delta", 21.78, -16.1, 4.0, "Deneb Algedi"),
    ("gamma", 21.67, -16.7, 3.4, "Nashira"),
    ("iota", 21.10, -16.8, 3.0, ""),
]
N = len(CAP)
lit = min(stars, N)
meta = (fol // META + 1) * META
prog = (fol - (meta - META)) / META

pts = [(round(430 + (21.04 - ra) * 312), round(270 - (dec + 19.7) * 22)) for _, ra, dec, _, _ in CAP]

outline = "M" + " L".join(f"{x} {y}" for x, y in pts) + "Z"
segs = [(i - 1, i) for i in range(1, lit)]
if lit >= N:
    segs.append((N - 1, 0))
lines = "".join(
    f'<path class="ln" pathLength="1" d="M{pts[a][0]} {pts[a][1]} L{pts[b][0]} {pts[b][1]}" style="animation-delay:{k*.35:.2f}s"/>'
    for k, (a, b) in enumerate(segs))

def star(x, y, r, d):
    return (f'<g class="ig" style="animation-delay:{d:.2f}s">'
            f'<circle cx="{x}" cy="{y}" r="{r*5}" fill="url(#sg)"/>'
            f'<path d="M{x-r*4} {y} H{x+r*4} M{x} {y-r*4} V{y+r*4}" stroke="#FFF4D6" stroke-width=".7" opacity=".7"/>'
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="#FFFBEA"/></g>')

dots, labels = "", ""
for i in range(lit):
    x, y = pts[i]; r = CAP[i][3]
    dots += star(x, y, r, i * .35)
    if CAP[i][4]:
        labels += f'<text class="lb" x="{x+12}" y="{y-10}" style="animation-delay:{i*.35+.5:.2f}s">{CAP[i][4]}</text>'

ghosts = ""
for i in range(lit, N):
    x, y = pts[i]
    if i == lit:
        ghosts += f'<circle class="next" cx="{x}" cy="{y}" r="9"/><circle cx="{x}" cy="{y}" r="2" fill="#FF6B5E"/>'
    else:
        ghosts += f'<circle class="gh" cx="{x}" cy="{y}" r="6"/><circle cx="{x}" cy="{y}" r="1.4" fill="#FF6B5E" opacity=".6"/>'

rnd = random.Random(7)
bg = ""
for _ in range(260):
    x, y = rnd.uniform(0, 1000), rnd.uniform(0, 440)
    r = rnd.choice([.5, .6, .7, .8, 1, 1.2, 1.6])
    o = rnd.uniform(.3, .9)
    tw = f' class="tw" style="animation-delay:{rnd.uniform(0,6):.1f}s"' if rnd.random() < .12 else ""
    bg += f'<circle{tw} cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#FFF4D6" opacity="{o:.2f}"/>'
dust = ""
for _ in range(140):
    t = rnd.uniform(0, 1)
    x = 80 + t * 640 + rnd.gauss(0, 45)
    y = 40 + t * 330 + rnd.gauss(0, 45)
    dust += f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rnd.choice([.5,.6,.8])}" fill="#CFE0FF" opacity="{rnd.uniform(.3,.7):.2f}"/>'

if lit >= N:
    titulo, sub = "Capricórnio completo", "Obrigada a cada estrela que brilha aqui."
elif stars == 0:
    titulo, sub = "Capricórnio, à espera", "Seja quem acende a primeira estrela."
else:
    titulo, sub = f"Capricórnio: {lit} de {N} estrelas", f"Faltam {N-lit} para completar a constelação."

CSS = """
.ig{transform-box:fill-box;transform-origin:center;animation:ig .9s ease-out both}
.ln{fill:none;stroke:#9FD3B0;stroke-width:1.3;stroke-linecap:round;stroke-dasharray:1;stroke-dashoffset:1;animation:draw .7s ease-out both;opacity:.85}
.out{fill:none;stroke:#9FD3B0;stroke-width:1;stroke-dasharray:2 8;opacity:.28}
.gh{fill:none;stroke:#FF6B5E;stroke-width:1.2;stroke-dasharray:2 3;opacity:.5}
.next{fill:none;stroke:#FF6B5E;stroke-width:1.8;stroke-dasharray:3 3;transform-box:fill-box;transform-origin:center;animation:nx 1.8s ease-in-out infinite}
.tw{animation:tw 4s ease-in-out infinite}
.lb{font-family:Georgia,serif;font-size:13px;font-style:italic;fill:#FFF4D6;opacity:0;animation:rise 1s ease-out forwards}
.fade{animation:rise 1.2s ease-out .4s both}
.moonglow{transform-box:fill-box;transform-origin:center;animation:pulse 7s ease-in-out infinite}
@keyframes ig{0%{transform:scale(0);opacity:0}60%{transform:scale(1.5);opacity:1}100%{transform:scale(1);opacity:1}}
@keyframes draw{to{stroke-dashoffset:0}}
@keyframes tw{0%,100%{opacity:.15}50%{opacity:1}}
@keyframes pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.08)}}
@keyframes nx{0%,100%{transform:scale(1);opacity:.5}50%{transform:scale(1.6);opacity:1}}
@keyframes rise{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
"""

svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 560" width="100%" role="img" aria-label="Céu noturno com a constelação de Capricórnio. Cada estrela dada no repositório acende uma estrela da constelação.">
<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#050A18"/><stop offset=".6" stop-color="#0D1B33"/><stop offset="1" stop-color="#1F3A4D"/></linearGradient>
<radialGradient id="sg"><stop offset="0" stop-color="#FFD66B" stop-opacity=".55"/><stop offset="1" stop-color="#FFD66B" stop-opacity="0"/></radialGradient>
<radialGradient id="glow"><stop offset="0" stop-color="#FFF4D6" stop-opacity=".5"/><stop offset="1" stop-color="#FFF4D6" stop-opacity="0"/></radialGradient>
<radialGradient id="moon" cx=".38" cy=".35" r=".75"><stop offset="0" stop-color="#FFFEF6"/><stop offset=".7" stop-color="#EFE5C6"/><stop offset="1" stop-color="#CFC4A0"/></radialGradient>
<filter id="b40" x="-50%" y="-50%" width="200%"
