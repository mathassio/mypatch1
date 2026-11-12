#!/usr/bin/env python3
"""Corta-tubos em C para conduta corrugada VMC Ø75 (HEATPEX 75/63) — modelo paramétrico.

Gera os STL da ferramenta pronta a usar (PETG/ASA):
  meia_A.stl   metade com rebaixo da lâmina e escareados M3
  meia_B.stl   metade tampa com porcas M3

Conceito
  * Corpo em C, encaixe lateral, dividido no plano de corte em duas metades.
  * Lâmina trapezoidal de x-ato standard (61 x 19 x 0,6) entalada num rebaixo da metade A;
    3 parafusos M3 + porca fecham o conjunto.
  * Guia anular no MESMO vale onde a lâmina corta (2,5 mm na ponta, 3 mm abaixo da crista,
    flancos a ~50° até ao anel): localiza o corte no vale sem depender do passo do corrugado.
  * O anel apoia nas cristas dos dois lados do vale e mantém o corte perpendicular.

Eixo do tubo = Z. Plano de corte z = 0. Abertura do C virada para -Y, lâmina em +Y.
Uso:  python3 corta_tubos.py [--crista 76 --interior 62.5 --guia_larg 2.5 --guia_prof 3]
"""
import argparse
import math
import os

import numpy as np
from manifold3d import CrossSection, JoinType, Manifold

SEG = 256


def args():
    p = argparse.ArgumentParser()
    # --- tubo ---
    p.add_argument("--crista", type=float, default=75.5, help="Ø exterior nas cristas [mm] (75-76 conforme marca)")
    p.add_argument("--interior", type=float, default=62.5, help="Ø interior [mm]")
    # --- guia no vale ---
    p.add_argument("--guia_larg", type=float, default=2.5, help="largura da ponta da guia [mm]")
    p.add_argument("--guia_prof", type=float, default=3.0, help="profundidade da guia abaixo da crista [mm]")
    # --- corpo ---
    p.add_argument("--folga", type=float, default=0.4, help="folga radial nas cristas [mm]")
    p.add_argument("--parede", type=float, default=5.0, help="espessura radial do anel [mm]")
    p.add_argument("--meia_esp", type=float, default=7.5, help="espessura de cada metade [mm]")
    p.add_argument("--abraco", type=float, default=210.0, help="ângulo abraçado pelo C [°]")
    p.add_argument("--sobrecorte", type=float, default=0.6, help="quanto a ponta passa o Ø interior [mm]")
    # --- lâmina trapezoidal standard ---
    p.add_argument("--lam_comp", type=float, default=61.0)
    p.add_argument("--lam_alt", type=float, default=19.0)
    p.add_argument("--lam_costas", type=float, default=39.0, help="comprimento das costas [mm]")
    p.add_argument("--lam_esp", type=float, default=0.6, help="profundidade do rebaixo [mm]")
    p.add_argument("--lam_ang", type=float, default=20.0, help="inclinação do gume face à tangente [°]")
    p.add_argument("--saida", default=os.path.dirname(os.path.abspath(__file__)))
    return p.parse_args()


# ---------------------------------------------------------------- utilitários
def pol(pts):
    return CrossSection([pts])


def c_perfil(rin, rout, abraco, chanfro=3.0):
    """Secção em C (XY), abertura centrada em -Y, chanfro de entrada no lado interior."""
    h = math.radians((360 - abraco) / 2)
    a0, a1 = -math.pi / 2 + h, 3 * math.pi / 2 - h
    d = chanfro / rin
    pts = [(rout * math.cos(a0 + (a1 - a0) * i / SEG), rout * math.sin(a0 + (a1 - a0) * i / SEG))
           for i in range(SEG + 1)]
    pts.append(((rin + chanfro) * math.cos(a1), (rin + chanfro) * math.sin(a1)))
    for i in range(SEG + 1):
        a = (a1 - d) + ((a0 + d) - (a1 - d)) * i / SEG
        pts.append((rin * math.cos(a), rin * math.sin(a)))
    pts.append(((rin + chanfro) * math.cos(a0), (rin + chanfro) * math.sin(a0)))
    return pol(pts)


def lamina_local(a):
    m = (a.lam_comp - a.lam_costas) / 2
    return [(0, 0), (a.lam_comp, 0), (a.lam_comp - m, a.lam_alt), (m, a.lam_alt)]


def para_global(pts, tip, ang):
    c, s = math.cos(ang), math.sin(ang)
    return [(tip[0] + u * c - v * s, tip[1] + u * s + v * c) for u, v in pts]


def extr(cs, z0, z1):
    return Manifold.extrude(cs, z1 - z0).translate((0, 0, z0))


def stl(man, path):
    mesh = man.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3].astype(np.float32)
    t = np.asarray(mesh.tri_verts)
    tri = v[t]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    rec = np.zeros(len(t), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"], rec["v"] = n, tri
    with open(path, "wb") as f:
        f.write(b"corta-tubos VMC".ljust(80, b" "))
        f.write(np.uint32(len(t)).tobytes())
        f.write(rec.tobytes())


# ---------------------------------------------------------------- modelo
def construir(a):
    Rb = a.crista / 2 + a.folga             # furo nas cristas
    Ro = Rb + a.parede                       # exterior do anel
    w = a.guia_larg
    Rn = a.crista / 2 - a.guia_prof          # ponta da guia
    r_tip = a.interior / 2 - a.sobrecorte    # ponta da lâmina
    zt = a.meia_esp                          # face exterior de cada metade

    anel = extr(c_perfil(Rb, Ro, a.abraco), 0, zt)

    # guia anular centrada no plano de corte: ponta arredondada Ø w, flancos ~50° até ao anel
    rc = Rn + w / 2
    ch = 2.1                                  # avanço do flanco: largura extra na raiz da guia
    perfil = CrossSection.batch_hull([
        CrossSection.circle(w / 2, 64).translate((rc, 0)),
        pol([(rc + 0.35, -w / 2), (Rb + 0.3, -w / 2 - ch), (Rb + 0.3, w / 2 + ch), (rc + 0.35, w / 2)]),
    ])
    h0 = -90 + (360 - a.abraco) / 2
    guia = Manifold.revolve(perfil, SEG, a.abraco).rotate((0, 0, h0))
    guia = guia ^ extr(c_perfil(Rn, Rb + 0.3, a.abraco, 3.0), 0, zt)   # só z>=0 + chanfro de entrada

    # lâmina: ponta no topo (x=0), gume inclinado lam_ang em relação à tangente
    ang = math.radians(a.lam_ang)
    tip = (0.0, r_tip)
    lam_l = lamina_local(a)
    lam = pol(para_global(lam_l, tip, ang))
    bolso = lam.offset(0.2, JoinType.Miter)

    # parafusos M3 (coordenadas locais da lâmina: u ao longo do gume, v para as costas)
    furos = para_global([(2.0, 14.0), (a.lam_comp / 2, a.lam_alt + 6.5), (a.lam_comp - 2.0, 14.0)], tip, ang)
    for x, y in furos:
        assert math.hypot(x, y) > Rb + 2.5, "furo M3 a invadir o furo do tubo"

    # alojamento = invólucro da lâmina + parafusos + topo do anel
    blocos = [lam.offset(6.0, JoinType.Round)]
    blocos += [CrossSection.circle(5.5, 48).translate(f) for f in furos]
    topo = [(Ro * math.cos(t), Ro * math.sin(t)) for t in np.linspace(math.radians(55), math.radians(125), 20)]
    blocos.append(pol([(0, 0)] + topo))
    aloj = extr(CrossSection.batch_hull(blocos), 0, zt) - Manifold.cylinder(3 * zt, Rb, Rb, SEG).translate((0, 0, -zt))

    meia = anel + aloj + guia

    # furação M3: passagem Ø3,4; escareado Ø6,2 na A; porca sextavada 5,5 x 2,6 na B
    L_paraf = 2 * math.floor((2 * zt - 3.2) / 2)       # comprimento comercial (par) que cabe
    cb = 2 * zt - L_paraf - 0.6                         # ponta fica 0,6 dentro da face B -> 2 mm de rosca na porca
    fur, cab, porca = Manifold(), Manifold(), Manifold()
    for x, y in furos:
        fur += Manifold.cylinder(3 * zt, 1.7, 1.7, 32).translate((x, y, -zt))
        cab += Manifold.cylinder(cb + 0.1, 3.1, 3.1, 40).translate((x, y, zt - cb))
        porca += Manifold.cylinder(2.7, 3.25, 3.25, 6).translate((x, y, zt - 2.6))
    meia = meia - fur

    # seta do sentido de rotação gravada na face exterior da A (0,6 mm)
    cx, cy = para_global([(a.lam_comp / 2 - 2, a.lam_alt / 2)], tip, ang)[0]
    seta = pol([(-9, -1.2), (3, -1.2), (3, -3.5), (9, 0), (3, 3.5), (3, 1.2), (-9, 1.2)]).translate((cx, cy))
    grav = extr(seta, zt - 0.6, zt + 1)

    A = meia - cab - extr(bolso, -1, a.lam_esp) - grav
    B = meia - porca
    lam3d = extr(lam, 0, a.lam_esp)

    # impressão: face exterior na mesa, junta (e rebaixo) para cima
    A_print = A.mirror((0, 0, 1)).translate((0, 0, zt))
    B_print = B.mirror((0, 0, 1)).translate((0, 0, zt))

    info = dict(furo_cristas=2 * Rb, ponta_guia_Ø=2 * Rn, ponta_lamina_Ø=2 * r_tip,
                lamina_exposta_mm=Rn - r_tip, espessura_total=2 * zt,
                parafuso=f"M3x{L_paraf} DIN 912 + porca (escareado {cb:.1f} mm)")
    return A, B, lam3d, A_print, B_print, info


def main():
    a = args()
    A, B, lam3d, A_p, B_p, info = construir(a)
    out = a.saida
    stl(A_p, os.path.join(out, "meia_A.stl"))
    stl(B_p, os.path.join(out, "meia_B.stl"))
    # prato único: A em cima, B em baixo (cabe numa mesa de 180 x 180)
    bA, bB = A_p.bounding_box(), B_p.bounding_box()
    prato = A_p + B_p.translate((0, bA[1] - bB[4] - 6, 0))
    bp = prato.bounding_box()
    prato = prato.translate((-(bp[0] + bp[3]) / 2, -(bp[1] + bp[4]) / 2, 0))
    stl(prato, os.path.join(out, "prato_A_B.stl"))
    bp = prato.bounding_box()
    print(f"prato_A_B: {bp[3]-bp[0]:.0f} x {bp[4]-bp[1]:.0f} mm")
    stl(A + B.mirror((0, 0, 1)), os.path.join(out, "_montagem_vis.stl"))
    stl(lam3d, os.path.join(out, "_lamina_vis.stl"))
    for k, v in info.items():
        print(f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}")
    for nome, m in (("A", A_p), ("B", B_p)):
        bb = m.bounding_box()
        print(nome, "vol %.1f cm3" % (m.volume() / 1000), "bbox", [round(x, 1) for x in bb],
              "genus", m.genus(), "status", m.status())


if __name__ == "__main__":
    main()
