#!/usr/bin/env python3
"""Corta-tubos em C para conduta corrugada VMC Ø75 (HEATPEX 75/63) — modelo paramétrico.

Gera STL para impressão 3D (PETG/ASA):
  meia_A.stl        metade com alojamento da lâmina (cara de junta para cima)
  meia_B.stl        metade tampa
  teste_encaixe.stl anel com nervura + 7 pentes de passo (7,0-10,0), para validar medidas

Conceito: o corpo é dividido no plano de corte. A lâmina trapezoidal de x-ato
(61 x 19 x 0,6 mm) fica entalada entre as duas metades, num rebaixo da metade A, e
3 parafusos M3 fecham o conjunto. Duas nervuras com o perfil do O-ring de vedação
entram nos vales vizinhos (±1 passo)
e mantêm o corte perpendicular. Encaixa-se o tubo lateralmente, a ponta da lâmina
fura o vale e depois roda-se a ferramenta no sentido da seta.

Eixo do tubo = Z. Plano de corte z = 0. Abertura do C virada para -Y, lâmina em +Y.
Uso:  python3 corta_tubos.py --crista 75.6 --vale 65.2 --interior 62.5 --passo 8.3
"""
import argparse
import math
import os

import numpy as np
from manifold3d import CrossSection, JoinType, Manifold, OpType

SEG = 256


def args():
    p = argparse.ArgumentParser()
    # --- medidas do tubo: CONFIRMAR COM PAQUÍMETRO ---
    p.add_argument("--crista", type=float, default=76.0, help="Ø exterior nas cristas [mm]")
    p.add_argument("--vale", type=float, default=65.5, help="Ø exterior no fundo do vale [mm]")
    p.add_argument("--interior", type=float, default=62.5, help="Ø interior (parede lisa) [mm]")
    p.add_argument("--passo", type=float, default=8.0, help="passo do corrugado [mm] (medir 10 passos / 10)")
    # --- ferramenta ---
    p.add_argument("--folga", type=float, default=0.4, help="folga radial nas cristas [mm]")
    p.add_argument("--parede", type=float, default=5.0, help="espessura radial do anel [mm]")
    p.add_argument("--abraco", type=float, default=210.0, help="ângulo abraçado pelo C [°]")
    p.add_argument("--oring", type=float, default=4.0, help="corda do O-ring de vedação que assenta no vale [mm]")
    p.add_argument("--folga_oring", type=float, default=0.2, help="folga por lado da nervura no vale [mm]")
    p.add_argument("--sobrecorte", type=float, default=0.6, help="quanto a ponta passa o Ø interior [mm]")
    # --- lâmina trapezoidal standard ---
    p.add_argument("--lam_comp", type=float, default=61.0)
    p.add_argument("--lam_alt", type=float, default=19.0)
    p.add_argument("--lam_costas", type=float, default=39.0, help="comprimento das costas [mm]")
    p.add_argument("--lam_esp", type=float, default=0.6, help="profundidade do rebaixo [mm]")
    p.add_argument("--lam_ang", type=float, default=20.0, help="inclinação do gume face à tangente [°]")
    p.add_argument("--saida", default=os.path.dirname(os.path.abspath(__file__)))
    return p.parse_args()


# ---------------------------------------------------------------- utilitários 2D
def pol(cs_pts):
    return CrossSection([cs_pts])


def c_perfil(rin, rout, abraco, chanfro=3.0):
    """Secção em C (XY), abertura centrada em -Y, chanfro de entrada no lado interior."""
    h = math.radians((360 - abraco) / 2)
    a0, a1 = -math.pi / 2 + h, 3 * math.pi / 2 - h
    d = chanfro / rin
    pts = []
    for i in range(SEG + 1):
        a = a0 + (a1 - a0) * i / SEG
        pts.append((rout * math.cos(a), rout * math.sin(a)))
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
# ---------------------------------------------------------------- pentes de passo
PASSOS_TESTE = [7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0]
SEG7 = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd",
        "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg"}


def texto7(txt, h=5.0, e=0.9):
    """Texto em 7 segmentos (só dígitos e ponto), canto inferior esquerdo em (0,0)."""
    w = h * 0.55
    seg = {"a": (0, h - e, w, e), "b": (w - e, h / 2, e, h / 2), "c": (w - e, 0, e, h / 2),
           "d": (0, 0, w, e), "e": (0, 0, e, h / 2), "f": (0, h / 2, e, h / 2), "g": (0, h / 2 - e / 2, w, e)}
    peças, x = [], 0.0
    for ch in txt:
        if ch == ".":
            peças.append(CrossSection.square((e, e)).translate((x, 0)))
            x += e + 0.9
            continue
        for sname in SEG7[ch]:
            sx, sy, sw, sh = seg[sname]
            peças.append(CrossSection.square((sw, sh)).translate((x + sx, sy)))
        x += w + 1.0
    return CrossSection.batch_boolean(peças, OpType.Add)


def pente(P, larg, dentes=8, alt=4.5, base=8.0, esp=2.4):
    """Pente plano: 8 dentes a passo P (7 passos acumulados), etiqueta em relevo."""
    comp = (dentes - 1) * P + 12
    cs = [CrossSection.square((comp, base))]
    for i in range(dentes):  # dente com perfil de O-ring (ponta arredondada)
        x = 6 + i * P
        cs.append(CrossSection.batch_hull([CrossSection.square((larg, 1)).translate((x - larg / 2, base - 0.5)),
                                           CrossSection.circle(larg / 2, 32).translate((x, base + alt - larg / 2))]))
    corpo = extr(CrossSection.batch_boolean(cs, OpType.Add), 0, esp)
    etiqueta = extr(texto7(f"{P:.1f}", 5.0, 0.9).translate((2.5, 1.5)), esp, esp + 0.6)
    return corpo + etiqueta


def construir(a):
    Rb = a.crista / 2 + a.folga             # furo nas cristas
    Ro = Rb + a.parede                       # exterior do anel
    w = a.oring - 2 * a.folga_oring          # largura da nervura (perfil de O-ring)
    Rn = a.vale / 2 + 0.4                    # ponta da nervura: 0,4 mm acima do fundo do vale
    r_tip = a.interior / 2 - a.sobrecorte    # ponta da lâmina
    zt = a.passo + w / 2                     # meia espessura (nervura rente à face exterior)

    # anel em C de cada metade (z de 0 a zt; espelha-se para a metade B)
    anel = extr(c_perfil(Rb, Ro, a.abraco), 0, zt)
    # nervura com perfil de O-ring: meia-cana Ø w centrada no vale a ±1 passo, revolvida no arco do C
    rc = Rn + w / 2
    perfil = CrossSection.batch_hull([CrossSection.circle(w / 2, 64).translate((rc, a.passo)),
                                      CrossSection.square((Rb + 0.3 - rc, w)).translate((rc, a.passo - w / 2))])
    h0 = -90 + (360 - a.abraco) / 2
    nerv = Manifold.revolve(perfil, SEG, a.abraco).rotate((0, 0, h0))
    nerv = nerv ^ extr(c_perfil(Rn, Rb + 0.3, a.abraco, 3.0), 0, zt)

    # lâmina: ponta no topo (x=0), gume inclinado lam_ang em relação à tangente
    ang = math.radians(a.lam_ang)
    tip = (0.0, r_tip)
    lam_l = lamina_local(a)
    lam = pol(para_global(lam_l, tip, ang))
    bolso = lam.offset(0.2, JoinType.Miter)

    # parafusos M3 (coordenadas locais da lâmina: u ao longo do gume, v para as costas)
    m = (a.lam_comp - a.lam_costas) / 2
    furos_l = [(2.0, 14.0), (a.lam_comp / 2, a.lam_alt + 6.5), (a.lam_comp - 2.0, 14.0)]
    furos = para_global(furos_l, tip, ang)
    for x, y in furos:
        assert math.hypot(x, y) > Rb + 2.5, "furo M3 a invadir o furo do tubo"

    # alojamento = invólucro da lâmina + parafusos + topo do anel
    pts = [p for p in para_global(lam_l, tip, ang)]
    blocos = [pol(pts).offset(6.0, JoinType.Round)]
    blocos += [CrossSection.circle(5.5, 48).translate(f) for f in furos]
    topo = [(Ro * math.cos(t), Ro * math.sin(t)) for t in np.linspace(math.radians(55), math.radians(125), 20)]
    blocos.append(pol([(0, 0)] + topo).offset(0.01))
    aloj2d = CrossSection.batch_hull(blocos)
    aloj = extr(aloj2d, 0, zt) - Manifold.cylinder(3 * zt, Rb, Rb, SEG).translate((0, 0, -zt))

    meia = anel + aloj + nerv

    # furação M3: passagem 3,4; cabeça Ø6 x 3,2 (A); porca 5,5 sextavada x 2,6 (B)
    fur = Manifold()
    cab = Manifold()
    porca = Manifold()
    for x, y in furos:
        fur += Manifold.cylinder(3 * zt, 1.7, 1.7, 32).translate((x, y, -zt))
        cab += Manifold.cylinder(3.3, 3.1, 3.1, 40).translate((x, y, zt - 3.2))
        porca += Manifold.cylinder(2.7, 3.25, 3.25, 6).translate((x, y, zt - 2.6))
    meia = meia - fur

    # seta do sentido de rotação gravada na face exterior (0,6 mm)
    cx, cy = para_global([(a.lam_comp / 2 - 2, a.lam_alt / 2)], tip, ang)[0]
    seta = pol([(-9, -1.2), (3, -1.2), (3, -3.5), (9, 0), (3, 3.5), (3, 1.2), (-9, 1.2)])
    seta = seta.translate((cx, cy))  # aponta +X no topo = sentido horário visto pela face A
    grav = extr(seta, zt - 0.6, zt + 1)

    A = meia - cab - extr(bolso, -1, a.lam_esp) - grav
    B = meia - porca
    lam3d = extr(lam, 0, a.lam_esp)

    # posições de impressão: face exterior na mesa, junta para cima
    A_print = A.mirror((0, 0, 1)).translate((0, 0, zt))
    B_print = B.mirror((0, 0, 1)).translate((0, 0, zt))

    # teste: anel sem alojamento (crista, vale, encaixe) + pentes de passo 7,0..10,0
    teste_anel = (anel + nerv).mirror((0, 0, 1)).translate((0, 0, zt))
    pentes = Manifold()
    for k, P in enumerate(PASSOS_TESTE):
        pentes += pente(P, w).translate((Ro + 8, Ro - 14 - k * 14.5, 0))
    teste = teste_anel + pentes

    info = dict(Rb=Rb, Ro=Ro, Rn=Rn, nervura=w, r_tip=r_tip, zt=zt, furos=furos,
                parafuso_M3=f"M3x{math.floor((2 * zt - 3.2) / 2) * 2}",
                pen=(a.vale / 2) - r_tip)
    return A, B, lam3d, A_print, B_print, teste, info


def main():
    a = args()
    A, B, lam3d, A_p, B_p, teste, info = construir(a)
    out = a.saida
    stl(A_p, os.path.join(out, "meia_A.stl"))
    stl(B_p, os.path.join(out, "meia_B.stl"))
    stl(teste, os.path.join(out, "teste_encaixe.stl"))
    # montagem (B espelhada para z<0) só para visualizar
    stl(A + B.mirror((0, 0, 1)) , os.path.join(out, "_montagem_vis.stl"))
    stl(lam3d, os.path.join(out, "_lamina_vis.stl"))
    for k, v in info.items():
        print(k, v)
    for nome, m in (("A", A_p), ("B", B_p), ("teste", teste)):
        bb = m.bounding_box()
        print(nome, "vol %.1f cm3" % (m.volume() / 1000), "bbox", [round(x, 1) for x in bb],
              "genus", m.genus(), "status", m.status())


if __name__ == "__main__":
    main()
