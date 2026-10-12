"""Instagram launch kit in the Pauta da Urna identity -> redes/instagram/*.png

- perfil-a.png / perfil-b.png: profile picture options (1080x1080, safe inside the circular crop)
- post-1..5.png: first post, a 5-slide carousel (1080x1350)
Numbers come from site/data.json (TSE, 1st round 2026, domestic electorate).

Usage: python redes/instagram.py
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
OUT = ROOT / "redes" / "instagram"
PAPEL, TINTA, TINTA2, CINZA = "#fdfcf9", "#191714", "#4f4a42", "#857e72"
VERMELHO, AMARELO, AMARELO_CLARO, REGRA = "#c81e2b", "#f5c400", "#fff1b3", "#e6e1d6"
CORRIGE, CONFIRMA = "#e2632b", "#1f8a4c"


def archivo(size, wdth=72, wght=900):
    f = ImageFont.truetype(str(FONTS / "Archivo-Variable.ttf"), size)
    axes = f.get_variation_axes()
    f.set_variation_by_axes([wdth if a["name"] in (b"Width", "Width") else wght for a in axes])
    return f


def serif(size, peso="Regular"):
    f = ImageFont.truetype(str(FONTS / "SourceSerif4-Variable.ttf"), size)
    f.set_variation_by_name(peso)
    return f


def mono(size, semibold=True):
    return ImageFont.truetype(str(FONTS / ("IBMPlexMono-SemiBold.ttf" if semibold else "IBMPlexMono-Regular.ttf")), size)


def quebra(d, texto, fonte, largura):
    linhas, linha = [], ""
    for p in texto.split():
        t = f"{linha} {p}".strip()
        if d.textlength(t, font=fonte) > largura and linha:
            linhas.append(linha)
            linha = p
        else:
            linha = t
    return linhas + [linha]


def bloco(d, xy, texto, fonte, cor, largura, entrelinha, marca=None):
    x, y = xy
    for linha in quebra(d, texto, fonte, largura):
        if marca:  # highlighter stroke under the line, like the site's .mark
            w = d.textlength(linha, font=fonte)
            asc, desc = fonte.getmetrics()
            d.rectangle([x - 6, y + asc * 0.55, x + w + 6, y + asc + desc * 0.3], fill=marca)
        d.text((x, y), linha, font=fonte, fill=cor)
        y += entrelinha
    return y


def urna(d, x, y, w, numero=None):
    """The voting-machine drawing from the site's hero, scaled to width w."""
    k = w / 320
    s = lambda v: v * k
    d.rounded_rectangle([x + s(4), y + s(18), x + s(316), y + s(244)], radius=s(16), fill="#e9e6dd", outline=TINTA, width=max(2, int(s(2))))
    d.rounded_rectangle([x + s(4), y + s(18), x + s(316), y + s(40)], radius=s(10), fill="#d9d5ca")
    d.rounded_rectangle([x + s(22), y + s(56), x + s(182), y + s(168)], radius=s(6), fill=TINTA)
    d.rectangle([x + s(30), y + s(64), x + s(174), y + s(160)], fill="#f4f3ee")
    d.text((x + s(40), y + s(76)), "NÃO VOTARAM", font=mono(int(s(9))), fill=CINZA)
    if numero:
        d.text((x + s(40), y + s(92)), numero, font=mono(int(s(19))), fill=VERMELHO)
    d.rectangle([x + s(40), y + s(124), x + s(162), y + s(131)], fill=AMARELO)
    d.text((x + s(40), y + s(140)), "1º TURNO · 2026", font=mono(int(s(9)), False), fill=TINTA2)
    teclas = "123456789"
    for i, n in enumerate(teclas + "0"):
        col, row = (i % 3, i // 3) if i < 9 else (1, 3)
        kx, ky = x + s(204 + col * 32), y + s(68 + row * 30)
        d.rounded_rectangle([kx, ky, kx + s(26), ky + s(22)], radius=s(4), fill=TINTA)
        d.text((kx + s(13), ky + s(11)), n, font=mono(int(s(12))), fill="#ffffff", anchor="mm")
    for rot, bg, fg, bx in (("BRANCO", "#ffffff", TINTA, 30), ("CORRIGE", CORRIGE, TINTA, 118), ("CONFIRMA", CONFIRMA, "#ffffff", 206)):
        d.rounded_rectangle([x + s(bx), y + s(196), x + s(bx + 84), y + s(226)], radius=s(5), fill=bg, outline=TINTA, width=max(1, int(s(1.2))))
        d.text((x + s(bx + 42), y + s(211)), rot, font=mono(int(s(10))), fill=fg, anchor="mm")


# ---------- profile pictures ----------
def perfil_a():
    """Paper, stacked wordmark, URNA in red, yellow rule: the site's header."""
    img = Image.new("RGB", (1080, 1080), PAPEL)
    d = ImageDraw.Draw(img)
    f1, f2 = archivo(250, wdth=66), archivo(330, wdth=66)
    for texto, fonte, cor, cy in (("PAUTA DA", f1, TINTA, 400), ("URNA", f2, VERMELHO, 640)):
        d.text((540, cy), texto, font=fonte, fill=cor, anchor="mm")
    d.rectangle([250, 800, 830, 830], fill=AMARELO)
    img.save(OUT / "perfil-a.png")


def perfil_b():
    """Red ground, white wordmark, yellow underline: reads at thumbnail size."""
    img = Image.new("RGB", (1080, 1080), VERMELHO)
    d = ImageDraw.Draw(img)
    d.text((540, 395), "PAUTA DA", font=archivo(230, wdth=66), fill="#ffffff", anchor="mm")
    d.text((540, 625), "URNA", font=archivo(330, wdth=66), fill="#ffffff", anchor="mm")
    d.rectangle([250, 790, 830, 822], fill=AMARELO)
    img.save(OUT / "perfil-b.png")


# ---------- carousel ----------
W, H, M = 1080, 1350, 90


def lamina(n):
    img = Image.new("RGB", (W, H), PAPEL)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 22], fill=AMARELO)
    fb = archivo(40)
    d.text((M, 70), "PAUTA DA", font=fb, fill=TINTA)
    d.text((M + d.textlength("PAUTA DA ", font=fb), 70), "URNA", font=fb, fill=VERMELHO)
    d.text((W - M, 74), f"{n}/5", font=mono(30), fill=CINZA, anchor="ra")
    return img, d


def rodape(d, fonte_dado="TSE, 1º turno 2026"):
    d.line([M, H - 175, W - M, H - 175], fill=REGRA, width=2)
    d.text((M, H - 150), f"Fonte: {fonte_dado}", font=mono(24, False), fill=TINTA2)
    d.text((M, H - 112), "Conteúdo produzido com apoio de IA", font=mono(24, False), fill=TINTA2)
    d.text((M, H - 70), "pautadaurna.com.br", font=archivo(42, wdth=80, wght=800), fill=VERMELHO)


def carrossel(t):
    abst = f"{t['abst'] / 1e6:.1f}".replace(".", ",")
    margem = f"{t['margem'] / 1e6:.1f}".replace(".", ",")
    razao = round(t["abst"] / t["margem"])

    img, d = lamina(1)  # the number
    d.text((M, 230), "1º TURNO · 4 DE OUTUBRO DE 2026", font=mono(30), fill=CINZA)
    d.text((M - 6, 285), f"{abst} milhões", font=archivo(170, wdth=64), fill=VERMELHO)
    y = bloco(d, (M, 500), "de pessoas não foram votar.", archivo(84, wdth=70, wght=800), TINTA, W - 2 * M, 92)
    y = bloco(d, (M, y + 60), f"A diferença entre os dois primeiros foi de {margem} milhões de votos.", serif(54), TINTA, W - 2 * M, 72, marca=AMARELO)
    d.text((M, y + 70), "Arraste para o lado →", font=mono(34), fill=VERMELHO)
    rodape(d)
    img.save(OUT / "post-1.png")

    img, d = lamina(2)  # the ratio, drawn
    d.text((M - 8, 190), f"{razao}", font=archivo(420, wdth=62), fill=VERMELHO)
    d.text((M + d.textlength(f"{razao}", font=archivo(420, wdth=62)) + 10, 420), "×", font=archivo(160, wdth=70), fill=VERMELHO)
    y = bloco(d, (M, 680), "ausentes para cada voto de diferença.", archivo(80, wdth=70, wght=800), TINTA, W - 2 * M, 88)
    r, gap, x0, y0 = 26, 16, M, y + 50
    for i in range(razao):  # one dot per abstainer...
        cx = x0 + r + (i % 8) * (2 * r + gap)
        cy = y0 + r + (i // 8) * (2 * r + gap)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=CINZA)
    vx, vy = x0 + r + 7 * (2 * r + gap), y0 + r + 1 * (2 * r + gap)  # ...and the one vote of difference
    d.ellipse([vx - r, vy - r, vx + r, vy + r], fill=VERMELHO)
    d.text((M, y0 + 2 * (2 * r + gap) + 26), "Quem faltou pode decidir o 2º turno, dia 25/10.", font=serif(42), fill=TINTA2)
    rodape(d)
    img.save(OUT / "post-2.png")

    img, d = lamina(3)  # where they are
    y = bloco(d, (M, 210), "Onde estão os que não votaram?", archivo(92, wdth=70, wght=900), TINTA, W - 2 * M, 98)
    for i, (num, txt) in enumerate((("01", "Na sua cidade e na sua região"), ("02", "No seu bairro"), ("03", "Na escola onde votam"))):
        yy = y + 50 + i * 100
        d.text((M, yy), num, font=mono(40), fill=VERMELHO)
        d.text((M + 90, yy - 8), txt, font=serif(52, "SemiBold"), fill=TINTA)
    urna(d, (W - 470) // 2, y + 300, 470, numero=f"{t['abst']:,}".replace(",", "."))
    d.text((W // 2, y + 670), "5.571 municípios · 94 mil locais de votação", font=mono(30), fill=TINTA2, anchor="ma")
    rodape(d, "TSE e IBGE")
    img.save(OUT / "post-3.png")

    img, d = lamina(4)  # ready to post
    y = bloco(d, (M, 210), "E o que dizer a eles: pronto para postar.", archivo(88, wdth=70, wght=900), TINTA, W - 2 * M, 96)
    itens = (("Imagens e carrosséis", "com os números da sua cidade, para Instagram, TikTok e WhatsApp."),
             ("Pautas por grupo", "idosos, jovens, trabalhadores: o que importa para cada um, Lula e Flávio lado a lado."),
             ("Envio direto", "o vídeo ou a imagem vão pelo WhatsApp com um toque."))
    y += 40
    for tit, txt in itens:
        d.rectangle([M, y, M + 12, y + 150], fill=AMARELO)
        d.text((M + 40, y), tit, font=archivo(52, wdth=80, wght=800), fill=TINTA)
        bloco(d, (M + 40, y + 66), txt, serif(38), TINTA2, W - 2 * M - 40, 48)
        y += 220
    rodape(d, "pautadaurna.com.br")
    img.save(OUT / "post-4.png")

    img, d = lamina(5)  # call to action
    y = bloco(d, (M, 230), "Escolha a sua cidade e comece.", archivo(120, wdth=66, wght=900), TINTA, W - 2 * M, 124)
    d.rectangle([M, y + 50, W - M, y + 190], fill=AMARELO)
    d.text((W // 2, y + 120), "pautadaurna.com.br", font=archivo(78, wdth=76, wght=900), fill=VERMELHO, anchor="mm")
    y = bloco(d, (M, y + 260), "Dia 25/10 tem 2º turno. Cada ausente que volta conta.", serif(50), TINTA, W - 2 * M, 66)
    d.rectangle([M, y + 40, M + 8, y + 150], fill=VERMELHO)
    bloco(d, (M + 34, y + 44), "Este projeto tem lado: pela democracia, com Lula. Os números vêm do TSE e do IBGE.", serif(36), TINTA2, W - 2 * M - 34, 48)
    rodape(d, "TSE, 1º turno 2026")
    img.save(OUT / "post-5.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data = json.loads((ROOT / "site" / "data.json").read_text())
    perfil_a()
    perfil_b()
    carrossel({"abst": data["total"]["abst"], "margem": data["margem_br"]})
    # preview of how the profile picture reads in the circle at feed size
    prev = Image.new("RGB", (560, 300), PAPEL)
    for i, nome in enumerate(("perfil-a.png", "perfil-b.png")):
        im = Image.open(OUT / nome).resize((220, 220))
        mask = Image.new("L", (220, 220), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, 220, 220], fill=255)
        prev.paste(im, (40 + i * 280, 40), mask)
    prev.save(OUT / "_previa-perfil.png")
    print("ok:", sorted(p.name for p in OUT.glob("*.png")))


if __name__ == "__main__":
    main()
