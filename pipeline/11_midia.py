"""Copies the curated Acervo da Vitória files into the site as WhatsApp-ready media -> site/midia/.

Why: sharing the raw file (MP4/JPG attached in WhatsApp, via the browser's share sheet) needs the file on our own
origin; Google Drive does not allow cross-site downloads. Files are not versioned in git: the GitHub Actions workflow
builds them with a cache, and only new items are downloaded.

- videos: H.264 + AAC, up to 720 px wide, bitrate chosen to stay under ~15 MB, +faststart
- images: JPG up to 1080 px wide
Writes site/midia/index.json ({id: {arquivo, mb}}); 04_export.py merges it into the page, so site/acervo.json
(versioned) does not change when media is rebuilt.

Usage: python pipeline/11_midia.py [--limite N]
"""
import json
import subprocess
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "raw" / "acervo"
OUT = ROOT / "site" / "midia"
ALVO_MB = 15


def baixa(fid):
    dest = CACHE / fid
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    s = requests.Session()
    r = s.get("https://drive.usercontent.google.com/download", params={"id": fid, "export": "download", "confirm": "t"},
              stream=True, timeout=120)
    r.raise_for_status()
    if "text/html" in r.headers.get("content-type", ""):
        raise RuntimeError("Drive returned a page instead of the file (private or rate-limited)")
    tmp = dest.with_suffix(".part")
    with open(tmp, "wb") as f:
        for chunk in r.iter_content(1 << 20):
            f.write(chunk)
    tmp.rename(dest)
    return dest


def duracao(f):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                         capture_output=True, text=True, check=True).stdout.strip()
    return float(out or 0)


def converte_video(src, dst):
    dur = max(1.0, duracao(src))
    kbps = int(min(1800, max(350, (ALVO_MB * 8 * 1000) / dur - 96)))  # total budget minus 96 kbps of audio
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src),
                    "-vf", "scale='min(720,iw)':-2:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-preset", "medium",
                    "-b:v", f"{kbps}k", "-maxrate", f"{int(kbps * 1.4)}k", "-bufsize", f"{kbps * 2}k",
                    "-c:a", "aac", "-b:a", "96k", "-ac", "2", "-movflags", "+faststart", str(dst)], check=True)


def converte_imagem(src, dst):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", "scale='min(1080,iw)':-2",
                    "-frames:v", "1", "-q:v", "3", str(dst)], check=True)


def main():
    limite = int(sys.argv[sys.argv.index("--limite") + 1]) if "--limite" in sys.argv else None
    CACHE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    f = ROOT / "site" / "acervo.json"
    acv = json.loads(f.read_text())
    feitos = falhas = 0
    indice = {}
    for v in acv["itens"][:limite]:
        video = v["mime"].startswith("video/")
        dst = OUT / f"{v['id']}.{'mp4' if video else 'jpg'}"
        try:
            if not dst.exists():
                src = baixa(v["id"])
                (converte_video if video else converte_imagem)(src, dst)
            indice[v["id"]] = {"arquivo": f"midia/{dst.name}", "mb": round(dst.stat().st_size / 1e6, 1)}
            feitos += 1
        except Exception as e:  # keep going; the item simply has no local file
            falhas += 1
            print(f"falhou {v['id']} ({v['titulo'][:40]}): {e}")
    (OUT / "index.json").write_text(json.dumps(indice, separators=(",", ":")))
    total = sum(p.stat().st_size for p in OUT.iterdir()) / 1e6
    print(f"midia: {feitos} prontos, {falhas} falhas · site/midia = {total:.0f} MB")


if __name__ == "__main__":
    main()
