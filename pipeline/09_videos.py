"""Short videos sent by the project -> web-ready MP4s for the "Postar" tab.

Input: files in videos/entrada/ (not versioned) listed in videos/videos.csv:
    arquivo,titulo,grupo,pauta,autor,autorizado,afirma_dados,fontes
- autorizado must be "sim" (written permission from the author); otherwise the row is refused
- afirma_dados = "sim" requires at least one link in fontes (space-separated)

Output: site/videos/<id>.mp4 (H.264 9:16 up to 1080x1920, yuv420p, AAC, +faststart, ~3 Mbps, 1.5 s end card),
site/videos/<id>.jpg (poster) and site/videos.json (what the page lists).

Videos recorded by people are not AI-generated content, so they carry no AI label.
Usage: python pipeline/09_videos.py [--lista CSV] [--saida DIR]
"""
import csv
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ENTRADA = ROOT / "videos" / "entrada"
LISTA = ROOT / "videos" / "videos.csv"
FONTS = ROOT / "assets" / "fonts"
GRUPOS = {"idosos", "jovens", "base", "media", "superior", "todos"}
W, H, FPS = 1080, 1920, 30
PAPEL, TINTA, VERMELHO, AMARELO = "#fdfcf9", "#191714", "#c81e2b", "#f5c400"


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:48]


def probe(f):
    out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(f)],
                         capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    return {"w": int(v["width"]), "h": int(v["height"]), "dur": float(d["format"]["duration"]),
            "audio": any(s["codec_type"] == "audio" for s in d["streams"])}


def cartela(path, autor):
    """End card in the site's visual language: paper, yellow rule, red URL."""
    img = Image.new("RGB", (W, H), PAPEL)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 28], fill=AMARELO)
    disp = ImageFont.truetype(str(FONTS / "Archivo-Variable.ttf"), 120)
    disp.set_variation_by_name("Black")
    mono = ImageFont.truetype(str(FONTS / "IBMPlexMono-SemiBold.ttf"), 44)
    d.text((90, 700), "PAUTA DA", font=disp, fill=TINTA)
    d.text((90, 830), "URNA", font=disp, fill=VERMELHO)
    d.text((90, 1010), "Dados, pautas e onde agir", font=mono, fill=TINTA)
    d.text((90, 1070), "na sua cidade.", font=mono, fill=TINTA)
    d.text((90, 1250), "pautadaurna.com.br", font=mono, fill=VERMELHO)
    if autor:
        d.text((90, 1720), f"Vídeo: {autor}"[:40], font=mono, fill="#4f4a42")
    img.save(path)


def processa(row, saida):
    src = ENTRADA / row["arquivo"]
    info = probe(src)
    vid = f"{slug(row['titulo']) or slug(src.stem)}-{hashlib.sha1(src.read_bytes()).hexdigest()[:6]}"
    mp4, jpg, card = saida / f"{vid}.mp4", saida / f"{vid}.jpg", saida / f"{vid}-cartela.png"
    cartela(card, row["autor"].strip())
    fit = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={PAPEL},"
           f"fps={FPS},format=yuv420p,setsar=1")
    audio0 = "[0:a]aresample=48000,aformat=channel_layouts=stereo[a0]" if info["audio"] else \
        f"anullsrc=r=48000:cl=stereo,atrim=0:{info['dur']}[a0]"
    fc = (f"[0:v]{fit}[v0];[1:v]fps={FPS},format=yuv420p,setsar=1,trim=0:1.5,setpts=PTS-STARTPTS[v1];"
          f"{audio0};anullsrc=r=48000:cl=stereo,atrim=0:1.5[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-loop", "1", "-t", "1.5", "-i", str(card),
                    "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-preset", "medium", "-profile:v", "high", "-b:v", "3M", "-maxrate", "3.5M",
                    "-bufsize", "6M", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(mp4)], check=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(min(1.0, info["dur"] / 2)), "-i", str(mp4),
                    "-frames:v", "1", "-vf", "scale=540:-2", "-q:v", "4", str(jpg)], check=True)
    card.unlink()
    out = probe(mp4)
    return {"id": vid, "titulo": row["titulo"].strip(), "grupo": row["grupo"].strip(),
            "pauta": int(row["pauta"]) if row.get("pauta", "").strip().isdigit() else None,
            "autor": row["autor"].strip(), "fontes": row.get("fontes", "").split(),
            "duracao": round(out["dur"], 1), "mb": round(mp4.stat().st_size / 1e6, 1),
            "arquivo": f"videos/{mp4.name}", "capa": f"videos/{jpg.name}"}


def main():
    global LISTA
    if "--lista" in sys.argv:
        LISTA = Path(sys.argv[sys.argv.index("--lista") + 1])
    saida = Path(sys.argv[sys.argv.index("--saida") + 1]) if "--saida" in sys.argv else ROOT / "site" / "videos"
    saida.mkdir(parents=True, exist_ok=True)
    publicados, recusados = [], []
    with open(LISTA, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            nome = row.get("arquivo", "").strip()
            if not nome or nome.startswith("#"):
                continue
            motivo = None
            if row.get("autorizado", "").strip().lower() != "sim":
                motivo = "sem autorização do autor"
            elif row.get("grupo", "").strip() not in GRUPOS:
                motivo = f"grupo inválido: {row.get('grupo')}"
            elif row.get("afirma_dados", "").strip().lower() == "sim" and not row.get("fontes", "").strip():
                motivo = "afirma dados sem fonte"
            elif not (ENTRADA / nome).exists():
                motivo = "arquivo não encontrado em videos/entrada/"
            if motivo:
                recusados.append((nome, motivo))
                continue
            v = processa(row, saida)
            publicados.append(v)
            print(f"ok  {nome} -> {v['arquivo']} ({v['duracao']} s, {v['mb']} MB)")
    for nome, motivo in recusados:
        print(f"recusado  {nome}: {motivo}")
    (saida.parent / "videos.json").write_text(json.dumps(publicados, ensure_ascii=False, indent=1))
    print(f"{len(publicados)} publicados, {len(recusados)} recusados -> {saida.parent / 'videos.json'}")


if __name__ == "__main__":
    main()
