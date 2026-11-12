#!/usr/bin/env python3
"""Gabarito 1:1 de corte boca-de-lobo (tubo sobre tubo) em PDF A4.

Uso:
    python3 gabarito_boca_lobo.py                       # Ø75 sobre Ø75 a 90°
    python3 gabarito_boca_lobo.py --ramal 60 --principal 75 --angulo 45
    python3 gabarito_boca_lobo.py --espessura 2         # ajuste pelo interior do ramal

Geometria: eixo principal = X, raio R. Ramal com raio r, eixo no plano XZ a angulo
alfa do principal. Ponto do ramal a angulo theta (0 = geratriz do lado do calcanhar):
    t(theta) = (sqrt(R^2 - r^2 sin^2 theta) + r cos theta cos alfa) / sin alfa
Profundidade de corte medida a partir da ponta do tubo: h = t - min(t).
O desenvolvimento usa sempre o perimetro EXTERIOR do ramal (onde se enrola o papel).
"""
import argparse
import math

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def perfil(R, r_corte, alfa_deg, n):
    a = math.radians(alfa_deg)
    t = []
    for i in range(n + 1):
        th = 2 * math.pi * i / n
        s = r_corte * math.sin(th)
        t.append((math.sqrt(max(R * R - s * s, 0.0)) + r_corte * math.cos(th) * math.cos(a)) / math.sin(a))
    tmin = min(t)
    return [v - tmin for v in t]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--principal", type=float, default=75.0, help="Ø exterior tubo principal [mm]")
    p.add_argument("--ramal", type=float, default=75.0, help="Ø exterior tubo a cortar [mm]")
    p.add_argument("--angulo", type=float, default=90.0, help="angulo entre eixos [graus]")
    p.add_argument("--espessura", type=float, default=0.0,
                   help="espessura do ramal [mm]; >0 = ajuste pelo diametro interior")
    p.add_argument("--saida", default="gabarito_75x75_90graus.pdf")
    a = p.parse_args()

    R = a.principal / 2
    r_ext = a.ramal / 2
    r_corte = r_ext - a.espessura
    if r_corte > R + 1e-9:
        raise SystemExit("Ramal maior que o principal: geometria impossivel.")

    perim = math.pi * a.ramal
    N = 720
    h = perfil(R, r_corte, a.angulo, N)
    hmax = max(h)

    W, H = landscape(A4)
    c = canvas.Canvas(a.saida, pagesize=(W, H))
    c.setTitle(f"Gabarito boca-de-lobo Ø{a.ramal:g} sobre Ø{a.principal:g} a {a.angulo:g}°")

    x0 = (W - perim * mm) / 2
    margem_ref = 20  # mm acima da cava mais funda
    y0 = H - 20 * mm - (hmax + margem_ref) * mm  # base = ponta do tubo

    # zona a remover (sombreado) e linha de corte
    c.setFillGray(0.85)
    path = c.beginPath()
    path.moveTo(x0, y0)
    for i, v in enumerate(h):
        path.lineTo(x0 + perim * i / N * mm, y0 + v * mm)
    path.lineTo(x0 + perim * mm, y0)
    path.close()
    c.drawPath(path, stroke=0, fill=1)
    c.setFillGray(0)

    c.setLineWidth(0.6)
    path = c.beginPath()
    path.moveTo(x0, y0 + h[0] * mm)
    for i, v in enumerate(h):
        path.lineTo(x0 + perim * i / N * mm, y0 + v * mm)
    c.drawPath(path, stroke=1, fill=0)

    # contorno da tira (comprimento = perimetro exterior)
    ytop = y0 + (hmax + margem_ref) * mm
    c.setLineWidth(0.3)
    c.rect(x0, y0, perim * mm, ytop - y0)

    # linha de referencia (alinhar perpendicular ao eixo)
    yref = y0 + (hmax + margem_ref / 2) * mm
    c.setDash(4, 2)
    c.line(x0, yref, x0 + perim * mm, yref)
    c.setDash()
    c.setFont("Helvetica", 7)
    c.drawString(x0 + 2 * mm, yref + 1.2 * mm, "linha de referência — esquadro ao eixo do tubo")

    # divisoes a cada 15°
    c.setFont("Helvetica", 6)
    for k in range(25):
        x = x0 + perim * k / 24 * mm
        v = h[k * N // 24]
        c.setDash(1, 1.5)
        c.line(x, y0, x, y0 + v * mm)
        c.setDash()
        c.drawCentredString(x, y0 - 3 * mm, f"{k*15}°")
    c.drawString(x0, y0 - 6.5 * mm, "0° / 180° = cavas (alinhar com o eixo do tubo principal);  90° / 270° = bicos")
    c.drawString(x0, y0 - 9.5 * mm, "Zona cinzenta = remover. Ponta do tubo na aresta inferior.")

    # tabela de cotas
    yt = y0 - 20 * mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x0, yt, f"Ø{a.ramal:g} sobre Ø{a.principal:g} · {a.angulo:g}° · perímetro {perim:.1f} mm · "
                         f"profundidade máx. {hmax:.1f} mm"
                 + (f" · ajuste pelo interior (e={a.espessura:g})" if a.espessura > 0 else " · ajuste pelo exterior"))
    c.setFont("Helvetica", 7.5)
    cols = 4
    for k in range(25):
        col, row = divmod(k, 7)
        x = x0 + col * 62 * mm
        y = yt - (6 + row * 4.2) * mm
        c.drawString(x, y, f"{k*15:>3}°  s = {perim*k/24:5.1f} mm  →  corte a {h[k*N//24]:4.1f} mm da ponta")
    _ = cols

    # barra de verificacao de escala
    yb = 14 * mm
    c.setLineWidth(0.8)
    c.line(x0, yb, x0 + 100 * mm, yb)
    for k in range(11):
        c.line(x0 + k * 10 * mm, yb, x0 + k * 10 * mm, yb + (2.5 if k % 5 else 4) * mm)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x0 + 103 * mm, yb, "100 mm — confirmar com régua. Imprimir a 100% (tamanho real), sem 'ajustar à página'.")

    c.showPage()
    c.save()
    print(f"OK {a.saida}: perimetro {perim:.2f} mm, profundidade max {hmax:.2f} mm")
    for k in range(0, 25, 1):
        print(f"{k*15:>3}°  s={perim*k/24:6.1f}  prof={h[k*N//24]:5.1f}")


if __name__ == "__main__":
    main()
