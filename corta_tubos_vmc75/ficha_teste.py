#!/usr/bin/env python3
"""Gera ficha_teste.pdf — procedimento e registo do teste de encaixe (v0.1)."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

st = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=st["Heading1"], fontSize=15, spaceAfter=4, textColor=colors.HexColor("#145a81"))
H2 = ParagraphStyle("h2", parent=st["Heading2"], fontSize=11, spaceBefore=8, spaceAfter=4, textColor=colors.HexColor("#145a81"))
P = ParagraphStyle("p", parent=st["BodyText"], fontSize=8.8, leading=11.5)
C = ParagraphStyle("c", parent=P, fontSize=8.3, leading=10.5)

GRID = TableStyle([
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9aa7b0")),
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f0f5")),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
])


def tab(rows, widths):
    t = Table([[Paragraph(str(c), C) for c in r] for r in rows], colWidths=[w * mm for w in widths])
    t.setStyle(GRID)
    return t


doc = SimpleDocTemplate("ficha_teste.pdf", pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
                        topMargin=14 * mm, bottomMargin=14 * mm,
                        title="Ficha de teste — corta-tubos VMC Ø75")
s = []
s.append(Paragraph("Ficha de teste — Corta-tubos VMC Ø75 (HEATPEX 75/63) · v0.1", H1))
s.append(Paragraph("Data: ____/____/______ &nbsp;&nbsp; Operador: ____________________ &nbsp;&nbsp; "
                   "Impressora: ____________________ &nbsp;&nbsp; Material: [  ] PETG [  ] ASA", P))

s.append(Paragraph("1. Medições do tubo (antes de imprimir · ~5 min)", H2))
s.append(Paragraph("Use um troço <b>direito e sem esticar</b>. Para os diâmetros, o perímetro é mais fiável "
                   "do que o paquímetro, porque o tubo corrugado ovaliza: Ø = perímetro / π.", P))
s.append(Spacer(1, 3))
s.append(tab([
    ["Grandeza", "Método", "Assumido", "Medido", "Ø calculado"],
    ["Ø crista", "Tira de papel à volta das cristas; marcar e medir o perímetro", "76,0", "P = ______ mm", "______"],
    ["Ø vale", "Linha de costura no fundo de um vale; marcar e medir", "65,5", "P = ______ mm", "______"],
    ["Ø interior", "Paquímetro na ponta do tubo, em 2 direcções a 90°", "62,5", "______ / ______", "média ______"],
    ["Passo", "Régua sobre 10 ondas (vale a vale) ÷ 10", "8,0", "L10 = ______ mm", "p = ______"],
    ["Lâmina", "Comprimento × altura × espessura", "61 × 19 × 0,6", "____ × ____ × ____", "—"],
], [22, 74, 20, 32, 30]))

s.append(Paragraph("2. Impressão do teste", H2))
s.append(tab([
    ["Ficheiro", "Conteúdo", "Definições"],
    ["teste_encaixe.stl", "Anel em C com nervura (meia ferramenta, sem lâmina) + 7 pentes de passo "
     "7,0 / 7,5 / 8,0 / 8,5 / 9,0 / 9,5 / 10,0 mm", "Camada 0,2 · 4 perímetros · 30 % de enchimento · "
     "sem suportes · peças já orientadas · área de 177 × 101 mm"],
], [34, 76, 68]))

s.append(Paragraph("3. Critérios de aceitação", H2))
s.append(tab([
    ["#", "Ensaio", "Critério OK", "OK", "NOK", "Observação"],
    ["1", "Pentes de passo", "Os 8 dentes de um pente entram todos nos vales em simultâneo. Passo real = valor do pente", "[  ]", "[  ]", "pente: ______"],
    ["2", "Encaixe lateral", "Entra de lado à mão, com clique, sem ferramentas e sem esmagar o tubo", "[  ]", "[  ]", ""],
    ["3", "Folga radial", "Roda 360° sem prender; não abana (folga ≤ 0,5 mm)", "[  ]", "[  ]", ""],
    ["4", "Nervura no vale", "A nervura assenta no vale e impede o anel de deslizar ao longo do tubo", "[  ]", "[  ]", ""],
    ["5", "Robustez", "10 encaixes e remoções sem fissuras nas pontas do C", "[  ]", "[  ]", ""],
    ["6", "Remoção", "Sai de lado sem deformar permanentemente o tubo", "[  ]", "[  ]", ""],
], [7, 26, 81, 10, 11, 43]))

s.append(Paragraph("4. Acções correctivas", H2))
s.append(tab([
    ["Sintoma", "Parâmetro a corrigir"],
    ["Encaixe demasiado duro / pontas fissuram", "--abraco 200 (menos abraço) ou --folga 0.6"],
    ["Encaixe solto / sai sozinho", "--abraco 220 ou --folga 0.2"],
    ["Abana radialmente", "--crista com o valor medido; --folga 0.2"],
    ["Nervura não entra no vale", "--vale com o valor medido; --nervura 1.4"],
    ["Nenhum pente encaixa", "Medir L10 com régua; usar --passo L10/10 e reimprimir só o teste"],
], [80, 98]))

s.append(Paragraph("5. Resultado", H2))
s.append(Paragraph("[  ] <b>Aprovado</b>: gerar a versão final com as medidas reais e imprimir meia_A + meia_B. "
                   "<br/>[  ] <b>Reprovado</b>: aplicar as acções correctivas e repetir o teste."
                   "<br/><br/>Comando: <font face='Courier'>python3 corta_tubos.py --crista ___ --vale ___ "
                   "--interior ___ --passo ___</font>", P))
doc.build(s)
print("OK ficha_teste.pdf")
