#!/usr/bin/env python3
"""Gabaritos 1:1 para derivação tubo sobre tubo (ex.: VMC Ø75) em PDF A4.

Por cada ângulo gera 2 páginas:
  1. Ramal  - corte boca-de-lobo na ponta do tubo derivado (ajuste pelo Ø exterior).
  2. Furo   - abertura a recortar no tubo principal (= passagem interior do ramal).

Uso:
    python3 gabarito_boca_lobo.py                          # Ø75/Ø75, 90° e 45°, parede 2 mm
    python3 gabarito_boca_lobo.py --angulos 90 --espessura 1.8
    python3 gabarito_boca_lobo.py --ramal 60 --principal 75 --angulos 45

Geometria: principal com eixo X e raio R; ramal de raio r com eixo no plano XZ a ângulo
alfa. Ponto do ramal a ângulo theta (0 = geratriz do lado do ângulo agudo):
    y = r sin(theta),  z = sqrt(R^2 - y^2)
    t = (z + r cos(theta) cos(alfa)) / sin(alfa)      # posição ao longo do eixo do ramal
    x = z cot(alfa) + r cos(theta) / sin(alfa)         # posição ao longo do eixo do principal
    s = R asin(y / R)                                  # arco no principal a partir do topo
"""
import argparse
import math

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

N = 720
W, H = landscape(A4)


def pontos(R, r, alfa_deg):
    a = math.radians(alfa_deg)
    out = []
    for i in range(N + 1):
        th = 2 * math.pi * i / N
        y = r * math.sin(th)
        z = math.sqrt(max(R * R - y * y, 0.0))
        t = (z + r * math.cos(th) * math.cos(a)) / math.sin(a)
        x = z / math.tan(a) + r * math.cos(th) / math.sin(a)
        s = R * math.asin(max(-1.0, min(1.0, y / R)))
        out.append((t, x, s))
    return out


def barra_escala(c, x0):
    yb = 12 * mm
    c.setLineWidth(0.8)
    c.line(x0, yb, x0 + 100 * mm, yb)
    for k in range(11):
        c.line(x0 + k * 10 * mm, yb, x0 + k * 10 * mm, yb + (2.5 if k % 5 else 4) * mm)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x0 + 103 * mm, yb, "100 mm — confirmar com régua. Imprimir a 100% (tamanho real), sem 'ajustar à página'.")


def pagina_ramal(c, a, alfa):
    R, r = a.principal / 2, a.ramal / 2
    perim = math.pi * a.ramal
    t = [p[0] for p in pontos(R, r, alfa)]
    tmin = min(t)
    h = [v - tmin for v in t]
    hmax = max(h)

    x0 = (W - perim * mm) / 2
    margem = 15
    y0 = H - 18 * mm - (hmax + margem) * mm
    X = lambda i: x0 + perim * i / N * mm

    c.setFillGray(0.85)
    p = c.beginPath()
    p.moveTo(x0, y0)
    for i, v in enumerate(h):
        p.lineTo(X(i), y0 + v * mm)
    p.lineTo(x0 + perim * mm, y0)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    c.setFillGray(0)

    c.setLineWidth(0.6)
    p = c.beginPath()
    p.moveTo(x0, y0 + h[0] * mm)
    for i, v in enumerate(h):
        p.lineTo(X(i), y0 + v * mm)
    c.drawPath(p, stroke=1, fill=0)

    c.setLineWidth(0.3)
    c.rect(x0, y0, perim * mm, (hmax + margem) * mm)
    yref = y0 + (hmax + margem / 2) * mm
    c.setDash(4, 2)
    c.line(x0, yref, x0 + perim * mm, yref)
    c.setDash()
    c.setFont("Helvetica", 7)
    c.drawString(x0 + 2 * mm, yref + 1.2 * mm, "linha de referência — esquadro ao eixo do tubo")

    c.setFont("Helvetica", 6)
    for k in range(25):
        c.setDash(1, 1.5)
        c.line(X(k * N // 24), y0, X(k * N // 24), y0 + h[k * N // 24] * mm)
        c.setDash()
        c.drawCentredString(X(k * N // 24), y0 - 3 * mm, f"{k*15}°")
    c.setFont("Helvetica", 7)
    nota0 = "0° = cava mais funda, lado do ângulo agudo (montante)" if alfa != 90 else "0° / 180° = cavas, alinhar com o eixo do principal"
    c.drawString(x0, y0 - 6.5 * mm, f"{nota0};  90° / 270° = bicos (assentam nos flancos do principal).")
    c.drawString(x0, y0 - 9.5 * mm, "Zona cinzenta = remover. Aresta inferior = ponta do tubo. Ajuste pelo Ø exterior.")

    yt = y0 - 17 * mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x0, yt, f"1/2 RAMAL · Ø{a.ramal:g} sobre Ø{a.principal:g} · {alfa:g}° · "
                         f"tira = perímetro {perim:.1f} mm · corte máx. {hmax:.1f} mm")
    c.setFont("Helvetica", 7.2)
    for k in range(25):
        col, row = divmod(k, 7)
        c.drawString(x0 + col * 62 * mm, yt - (5 + row * 3.8) * mm,
                     f"{k*15:>3}°  s = {perim*k/24:5.1f} mm  →  corte a {h[k*N//24]:4.1f} mm da ponta")
    barra_escala(c, x0)
    c.showPage()


def pagina_furo(c, a, alfa):
    R = a.principal / 2
    ri = a.ramal / 2 - a.espessura
    pts = pontos(R, ri, alfa)
    xs = [p[1] for p in pts]
    ss = [p[2] for p in pts]
    perim = math.pi * a.principal
    xc = R / math.tan(math.radians(alfa))  # eixo do ramal cruza o topo do principal

    larg = perim + 0  # tira em volta do principal (fecha sobre si = posição certa)
    alt = (max(xs) - min(xs)) + 30
    x0 = (W - larg * mm) / 2
    y0 = H - 18 * mm - alt * mm
    ymid = y0 + alt / 2 * mm
    xmid = x0 + larg / 2 * mm
    xoff = (max(xs) + min(xs)) / 2
    # eixo do principal na vertical da folha? Não: tira enrolada -> horizontal = perímetro (s),
    # vertical = ao longo do eixo do principal (x).
    P = lambda x, s: (xmid + s * mm, ymid + (x - xoff) * mm)

    c.setLineWidth(0.3)
    c.rect(x0, y0, larg * mm, alt * mm)
    c.setDash(4, 2)
    c.line(xmid, y0, xmid, y0 + alt * mm)
    c.setDash()
    c.setFont("Helvetica", 7)
    c.drawString(xmid + 1.5 * mm, y0 + alt * mm - 4 * mm, "geratriz de topo (alinhar ao longo do tubo)")
    c.drawString(x0 + 2 * mm, y0 + alt * mm - 4 * mm, "vertical da folha = eixo do principal  ·  tira com o perímetro: fechar à volta do tubo")

    c.setFillGray(0.85)
    p = c.beginPath()
    p.moveTo(*P(xs[0], ss[0]))
    for x, s in zip(xs, ss):
        p.lineTo(*P(x, s))
    p.close()
    c.setLineWidth(0.6)
    c.drawPath(p, stroke=1, fill=1)
    c.setFillGray(0)

    cx, cy = P(xc, 0)
    c.setLineWidth(0.4)
    c.line(cx - 4 * mm, cy, cx + 4 * mm, cy)
    c.line(cx, cy - 4 * mm, cx, cy + 4 * mm)
    c.drawString(cx + 1.5 * mm, cy + 1.5 * mm, "eixo do ramal")
    if alfa != 90:
        c.drawString(x0 + 2 * mm, y0 + alt * mm - 8 * mm, "↑ montante: o ramal inclina-se para este lado")
        c.drawString(x0 + 2 * mm, y0 + 3 * mm, "↓ jusante: lado do extractor (sentido do ar no principal)")

    yt = y0 - 8 * mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x0, yt, f"2/2 FURO NO PRINCIPAL · Ø{a.principal:g} · ramal {alfa:g}° · Ø interior ramal "
                         f"{2*ri:g} (parede {a.espessura:g})")
    c.setFont("Helvetica", 7.5)
    c.drawString(x0, yt - 5 * mm, f"Comprimento do furo (eixo): {max(xs)-min(xs):.1f} mm   ·   "
                                  f"Largura no arco: {max(ss)-min(ss):.1f} mm   ·   "
                                  f"Largura em corda: {2*ri:.1f} mm")
    c.drawString(x0, yt - 9 * mm, "Zona cinzenta = recortar. Rebarbar por dentro; vedar com silicone/fita alumínio.")
    barra_escala(c, x0)
    c.showPage()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--principal", type=float, default=75.0, help="Ø exterior tubo principal [mm]")
    p.add_argument("--ramal", type=float, default=75.0, help="Ø exterior tubo derivado [mm]")
    p.add_argument("--angulos", type=float, nargs="+", default=[90.0, 45.0], help="ângulos entre eixos [°]")
    p.add_argument("--espessura", type=float, default=2.0, help="parede do ramal [mm] (define o furo)")
    p.add_argument("--saida", default="gabarito_VMC_75x75.pdf")
    a = p.parse_args()
    if a.ramal > a.principal:
        raise SystemExit("Ramal maior que o principal: geometria impossível.")

    c = canvas.Canvas(a.saida, pagesize=(W, H))
    c.setTitle(f"Gabaritos derivação Ø{a.ramal:g} sobre Ø{a.principal:g}")
    for alfa in a.angulos:
        pagina_ramal(c, a, alfa)
        pagina_furo(c, a, alfa)
    c.save()
    print("OK", a.saida)


if __name__ == "__main__":
    main()
