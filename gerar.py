import os, json, random, urllib.request

U, META = "Mariajtik", 20

def api(p):
    r = urllib.request.Request("https://api.github.com/" + p, headers={
        "Authorization": "Bearer " + os.environ.get("GH_TOKEN", ""), "User-Agent": "gerar"})
    return json.load(urllib.request.urlopen(r, timeout=20))

stars = sum(r["stargazers_count"] for r in api(f"users/{U}/repos?per_page=100"))
fol = api(f"users/{U}")["followers"]

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
    x, y = pts[i]
    dots += star(x, y, CAP[i][3], i * .35)
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

svg = open("ceu.template.svg", encoding="utf-8").read()
troca = {"__DUST__": dust, "__BG__": bg, "__RING__": f"{prog*100:.1f}", "__FOL__": str(fol),
         "__META__": str(meta), "__OUTLINE__": outline, "__LINES__": lines, "__GHOSTS__": ghosts,
         "__DOTS__": dots, "__LABELS__": labels, "__TITULO__": titulo, "__SUB__": sub}
for k, v in troca.items():
    svg = svg.replace(k, v)

open("ceu.svg", "w", encoding="utf-8").write(svg)
# FIM
