from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
PHRASES_FILE = ROOT / "phrases.json"
OVERRIDES_FILE = ROOT / "phrases_overrides.json"
STATE_FILE = ROOT / "state.json"
PENDING_FILE = ROOT / "pending.json"
PUBLISHED_LOG = ROOT / "published.jsonl"
GENERATED_DIR = ROOT / "generated"
HANDLE = "@STOPFALLINGDOWN"

HASHTAGS: dict[str, list[str]] = {
    "distacco": ["#frasi", "#pensieri", "#distacco", "#lasciareandare", "#pace", "#riflessioni", "#stopfallingdown"],
    "amore": ["#frasi", "#amore", "#relazioni", "#sentimenti", "#pensieri", "#riflessioni", "#stopfallingdown"],
    "fiducia": ["#frasi", "#fiducia", "#verita", "#tradimento", "#relazioni", "#pensieri", "#stopfallingdown"],
    "crescita": ["#frasi", "#crescita", "#consapevolezza", "#amorproprio", "#pensieri", "#riflessioni", "#stopfallingdown"],
    "solitudine": ["#frasi", "#solitudine", "#pensieri", "#emozioni", "#riflessioni", "#vita", "#stopfallingdown"],
    "ricordi": ["#frasi", "#ricordi", "#nostalgia", "#pensieri", "#emozioni", "#riflessioni", "#stopfallingdown"],
    "rispetto": ["#frasi", "#rispetto", "#amorproprio", "#relazioni", "#pensieri", "#riflessioni", "#stopfallingdown"],
    "verita": ["#frasi", "#verita", "#sincerita", "#fiducia", "#pensieri", "#riflessioni", "#stopfallingdown"],
    "ripartenza": ["#frasi", "#ripartire", "#rinascita", "#crescita", "#forza", "#pensieri", "#stopfallingdown"],
    "confini": ["#frasi", "#confini", "#amorproprio", "#rispetto", "#consapevolezza", "#pensieri", "#stopfallingdown"],
    "tradimento": ["#frasi", "#tradimento", "#bugie", "#fiducia", "#relazioni", "#pensieri", "#stopfallingdown"],
    "lealta": ["#frasi", "#lealta", "#rispetto", "#fiducia", "#relazioni", "#pensieri", "#stopfallingdown"],
    "vuoto": ["#frasi", "#vuoto", "#solitudine", "#pensieri", "#emozioni", "#dolore", "#stopfallingdown"],
}


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_phrases() -> list[dict[str, Any]]:
    phrases: list[dict[str, Any]] = read_json(PHRASES_FILE, [])
    if OVERRIDES_FILE.exists():
        overrides: list[dict[str, Any]] = read_json(OVERRIDES_FILE, [])
        by_id = {int(item["id"]): item for item in phrases}
        for item in overrides:
            by_id[int(item["id"])] = item
        phrases = [by_id[key] for key in sorted(by_id)]
    return phrases


def font_path() -> str:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    raise FileNotFoundError("Nessun font TrueType compatibile trovato nel runner.")


def wrap_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = word if not current else f"{current} {word}"
        box = draw.textbbox((0, 0), test, font=font)
        if box[2] - box[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def build_text_layout(text: str) -> tuple[ImageFont.FreeTypeFont, list[str], int]:
    probe = Image.new("L", (1080, 1080), 0)
    draw = ImageDraw.Draw(probe)
    path = font_path()
    for size in range(94, 43, -2):
        font = ImageFont.truetype(path, size=size)
        lines = wrap_lines(draw, text, font, 900)
        line_height = int(size * 1.28)
        if len(lines) <= 8 and len(lines) * line_height <= 670:
            return font, lines, line_height
    font = ImageFont.truetype(path, size=44)
    return font, wrap_lines(draw, text, font, 900), 56


def composite_glow(canvas: Image.Image, mask: Image.Image, color: tuple[int, int, int], blur: float, alpha: int) -> Image.Image:
    glow_mask = mask.filter(ImageFilter.GaussianBlur(blur))
    if alpha < 255:
        glow_mask = glow_mask.point(lambda p: p * alpha // 255)
    layer = Image.new("RGBA", canvas.size, (*color, 0))
    layer.putalpha(glow_mask)
    return Image.alpha_composite(canvas, layer)


def generate_image(text: str, phrase_id: int, output: Path) -> None:
    del phrase_id  # mantenuto nella firma per compatibilità
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas = Image.new("RGBA", (1080, 1080), (0, 0, 0, 255))

    font, lines, line_height = build_text_layout(text.upper())
    text_mask = Image.new("L", canvas.size, 0)
    draw = ImageDraw.Draw(text_mask)
    total_height = len(lines) * line_height
    top = max(145, (900 - total_height) // 2)

    for index, line in enumerate(lines):
        box = draw.textbbox((0, 0), line, font=font)
        x = (1080 - (box[2] - box[0])) // 2
        y = top + index * line_height
        draw.text((x, y), line, font=font, fill=255)

    # Glow rosso su più livelli: alone largo, medio e vicino al tubo neon.
    canvas = composite_glow(canvas, text_mask, (255, 0, 0), 30, 75)
    canvas = composite_glow(canvas, text_mask, (255, 0, 0), 14, 135)
    canvas = composite_glow(canvas, text_mask, (255, 15, 15), 5, 220)

    core = Image.new("RGBA", canvas.size, (255, 70, 70, 0))
    core.putalpha(text_mask)
    canvas = Image.alpha_composite(canvas, core)

    # Firma piccola e discreta, anch'essa neon.
    handle_font = ImageFont.truetype(font_path(), size=34)
    handle_mask = Image.new("L", canvas.size, 0)
    handle_draw = ImageDraw.Draw(handle_mask)
    box = handle_draw.textbbox((0, 0), HANDLE, font=handle_font)
    hx = (1080 - (box[2] - box[0])) // 2
    hy = 965
    handle_draw.text((hx, hy), HANDLE, font=handle_font, fill=220)
    canvas = composite_glow(canvas, handle_mask, (255, 0, 0), 10, 120)
    handle_core = Image.new("RGBA", canvas.size, (255, 65, 65, 0))
    handle_core.putalpha(handle_mask)
    canvas = Image.alpha_composite(canvas, handle_core)

    canvas.convert("RGB").save(output, "JPEG", quality=95, optimize=True)


def choose_phrase() -> dict[str, Any]:
    phrases = load_phrases()
    state: dict[str, Any] = read_json(STATE_FILE, {"used_ids": [], "last_published": None})
    used = set(state.get("used_ids", []))
    available = [phrase for phrase in phrases if phrase["id"] not in used]
    if not available:
        state["used_ids"] = []
        write_json(STATE_FILE, state)
        available = phrases
    if not available:
        raise RuntimeError("La banca frasi è vuota.")
    return random.SystemRandom().choice(available)


def caption_for(phrase: dict[str, Any]) -> str:
    tags = HASHTAGS.get(phrase.get("category", ""), HASHTAGS["crescita"])
    return f'{phrase["text"]}\n\n{HANDLE}\n\n{" ".join(tags)}'


def prepare(dry_run: bool = False) -> None:
    if PENDING_FILE.exists() and not dry_run:
        pending = read_json(PENDING_FILE, {})
        print(f"Post già in attesa: frase #{pending.get('phrase_id')}. Verrà ritentata la pubblicazione.")
        return

    phrase = choose_phrase()
    if dry_run:
        output = GENERATED_DIR / "dry-run.jpg"
        generate_image(phrase["text"], int(phrase["id"]), output)
        print(f"Dry run generato: {output.relative_to(ROOT)} — frase #{phrase['id']}")
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    output = GENERATED_DIR / f"post-{int(phrase['id']):04d}-{timestamp}.jpg"
    generate_image(phrase["text"], int(phrase["id"]), output)

    pending = {
        "phrase_id": phrase["id"],
        "category": phrase.get("category"),
        "text": phrase["text"],
        "caption": caption_for(phrase),
        "image_path": str(output.relative_to(ROOT)).replace("\\", "/"),
        "prepared_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(PENDING_FILE, pending)
    print(f"Preparato post con frase #{phrase['id']}: {pending['image_path']}")


def current_git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def graph_post(url: str, data: dict[str, str]) -> dict[str, Any]:
    response = requests.post(url, data=data, timeout=90)
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(f"Risposta Meta non JSON ({response.status_code}): {response.text[:500]}") from exc
    if not response.ok or "error" in payload:
        raise RuntimeError(f"Errore Meta API ({response.status_code}): {json.dumps(payload, ensure_ascii=False)}")
    return payload


def graph_get(url: str, params: dict[str, str]) -> dict[str, Any]:
    response = requests.get(url, params=params, timeout=90)
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(f"Risposta Meta non JSON ({response.status_code}): {response.text[:500]}") from exc
    if not response.ok or "error" in payload:
        raise RuntimeError(f"Errore Meta API ({response.status_code}): {json.dumps(payload, ensure_ascii=False)}")
    return payload


def wait_for_container(base: str, creation_id: str, access_token: str) -> None:
    for attempt in range(1, 31):
        status = graph_get(
            f"{base}/{creation_id}",
            {
                "fields": "status_code,status",
                "access_token": access_token,
            },
        )
        status_code = str(status.get("status_code", "")).upper()
        status_text = str(status.get("status", ""))
        print(f"Stato container {creation_id}: {status_code or 'SCONOSCIUTO'} {status_text}")

        if status_code == "FINISHED":
            return
        if status_code in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"Container Instagram non pubblicabile: {json.dumps(status, ensure_ascii=False)}")
        if attempt < 30:
            time.sleep(5)

    raise RuntimeError("Timeout: il container Instagram non è diventato FINISHED entro 150 secondi.")


def publish() -> None:
    pending = read_json(PENDING_FILE, None)
    if not pending:
        raise RuntimeError("Nessun pending.json trovato. Esegui prima il comando prepare.")

    ig_user_id = os.environ.get("IG_USER_ID", "").strip()
    access_token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    api_version = os.environ.get("META_API_VERSION", "v25.0").strip() or "v25.0"
    repository = os.environ.get("GITHUB_REPOSITORY", "eletwave/stopfallingdown-bot").strip()

    if not ig_user_id or not access_token:
        raise RuntimeError("Mancano i secrets IG_USER_ID e/o IG_ACCESS_TOKEN.")

    sha = current_git_sha()
    image_path = pending["image_path"]
    image_url = f"https://raw.githubusercontent.com/{repository}/{sha}/{image_path}"
    base = f"https://graph.facebook.com/{api_version}"

    container = graph_post(
        f"{base}/{ig_user_id}/media",
        {
            "image_url": image_url,
            "caption": pending["caption"],
            "access_token": access_token,
        },
    )
    creation_id = str(container["id"])
    wait_for_container(base, creation_id, access_token)

    result = graph_post(
        f"{base}/{ig_user_id}/media_publish",
        {
            "creation_id": creation_id,
            "access_token": access_token,
        },
    )
    instagram_media_id = str(result["id"])

    state = read_json(STATE_FILE, {"used_ids": [], "last_published": None})
    used_ids = list(state.get("used_ids", []))
    if pending["phrase_id"] not in used_ids:
        used_ids.append(pending["phrase_id"])
    state["used_ids"] = used_ids
    state["last_published"] = {
        "phrase_id": pending["phrase_id"],
        "instagram_media_id": instagram_media_id,
        "image_path": image_path,
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(STATE_FILE, state)

    with PUBLISHED_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(state["last_published"], ensure_ascii=False) + "\n")

    PENDING_FILE.unlink(missing_ok=True)
    print(f"Pubblicato su Instagram: media id {instagram_media_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Automazione Instagram @stopfallingdown")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare", help="Sceglie una frase e genera la grafica")
    prepare_parser.add_argument("--dry-run", action="store_true", help="Genera solo generated/dry-run.jpg")
    subparsers.add_parser("publish", help="Pubblica il post preparato tramite Instagram API")

    args = parser.parse_args()
    if args.command == "prepare":
        prepare(dry_run=args.dry_run)
    elif args.command == "publish":
        publish()


if __name__ == "__main__":
    main()
