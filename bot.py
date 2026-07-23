from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
PHRASES_FILE = ROOT / "phrases.json"
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
}


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def font_path() -> str:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
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
    for size in range(92, 45, -2):
        font = ImageFont.truetype(path, size=size)
        lines = wrap_lines(draw, text, font, 860)
        line_height = int(size * 1.18)
        total_height = len(lines) * line_height
        if len(lines) <= 9 and total_height <= 650:
            return font, lines, line_height
    font = ImageFont.truetype(path, size=46)
    return font, wrap_lines(draw, text, font, 860), 56


def distress_mask(mask: Image.Image, seed: int) -> Image.Image:
    rng = random.Random(seed)
    scratch = ImageDraw.Draw(mask)
    width, height = mask.size

    # Piccoli tagli e imperfezioni: simulano un carattere stampato/brush consumato.
    for _ in range(320):
        x = rng.randint(90, width - 90)
        y = rng.randint(120, height - 160)
        w = rng.randint(2, 12)
        h = rng.randint(1, 4)
        scratch.rectangle((x, y, x + w, y + h), fill=0)

    for _ in range(40):
        x = rng.randint(100, width - 100)
        y = rng.randint(140, height - 180)
        length = rng.randint(12, 45)
        scratch.line((x, y, x + length, y + rng.randint(-2, 2)), fill=0, width=1)
    return mask


def generate_image(text: str, phrase_id: int, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas = Image.new("RGB", (1080, 1080), (0, 0, 0))
    mask = Image.new("L", canvas.size, 0)
    draw = ImageDraw.Draw(mask)

    main_text = text.upper()
    font, lines, line_height = build_text_layout(main_text)
    total_height = len(lines) * line_height
    top = max(110, (900 - total_height) // 2)

    for index, line in enumerate(lines):
        box = draw.textbbox((0, 0), line, font=font)
        line_width = box[2] - box[0]
        x = (1080 - line_width) // 2
        y = top + index * line_height
        draw.text((x, y), line, font=font, fill=255, stroke_width=1, stroke_fill=255)

    mask = distress_mask(mask, phrase_id)
    ink = Image.new("RGB", canvas.size, (244, 244, 240))
    canvas.paste(ink, (0, 0), mask)

    handle_font = ImageFont.truetype(font_path(), size=34)
    handle_draw = ImageDraw.Draw(canvas)
    box = handle_draw.textbbox((0, 0), HANDLE, font=handle_font)
    handle_draw.text(((1080 - (box[2] - box[0])) // 2, 985), HANDLE, font=handle_font, fill=(215, 215, 210))

    canvas.save(output, "JPEG", quality=95, optimize=True)


def choose_phrase() -> dict[str, Any]:
    phrases: list[dict[str, Any]] = read_json(PHRASES_FILE, [])
    state: dict[str, Any] = read_json(STATE_FILE, {"used_ids": [], "last_published": None})
    used = set(state.get("used_ids", []))
    available = [phrase for phrase in phrases if phrase["id"] not in used]

    # Quando la banca è esaurita ricomincia un nuovo ciclo, evitando duplicati nello stesso ciclo.
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


def publish() -> None:
    pending = read_json(PENDING_FILE, None)
    if not pending:
        raise RuntimeError("Nessun pending.json trovato. Esegui prima il comando prepare.")

    ig_user_id = os.environ.get("IG_USER_ID", "").strip()
    access_token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    api_version = os.environ.get("META_API_VERSION", "v23.0").strip() or "v23.0"
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
