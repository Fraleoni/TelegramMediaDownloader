import asyncio
import fnmatch
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

# Keyboard input support on Windows
try:
    import msvcrt
except ImportError:
    msvcrt = None

from rich.console import Console
from rich.markup import escape
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TransferSpeedColumn,
)
from telethon import TelegramClient, errors
from telethon.tl.types import (
    DocumentAttributeVideo,
    Message,
)

console = Console()

VIDEO_EXTENSIONS = (
    ".mp4", ".mov", ".mkv", ".avi", ".webm", ".wmv", ".flv", ".ogv",
    ".3gp", ".m4v", ".mts", ".m2ts", ".ts",
)
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic", ".heif", ".tiff")
DOCUMENT_EXTENSIONS = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".csv", ".odt", ".ods", ".odp")
ARCHIVE_EXTENSIONS = (".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso")
ALL_KNOWN_EXTENSIONS = VIDEO_EXTENSIONS + IMAGE_EXTENSIONS + DOCUMENT_EXTENSIONS + ARCHIVE_EXTENSIONS

# Categories used for filename prefixes, --media-type matching and category-only filters (e.g. resolution/size checks apply only to "video")
MEDIA_CATEGORIES = {
    "video": {
        "extensions": VIDEO_EXTENSIONS,
        "mime_prefixes": ("video/",),
    },
    "image": {
        "extensions": IMAGE_EXTENSIONS,
        "mime_prefixes": ("image/",),
    },
    "document": {
        "extensions": DOCUMENT_EXTENSIONS,
        "mime_prefixes": (
            "application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument",
            "application/vnd.ms-excel", "application/vnd.ms-powerpoint", "text/plain", "text/csv",
            "application/vnd.oasis.opendocument",
        ),
    },
    "archive": {
        "extensions": ARCHIVE_EXTENSIONS,
        "mime_prefixes": (
            "application/zip", "application/x-rar-compressed", "application/vnd.rar",
            "application/x-7z-compressed", "application/x-tar", "application/gzip",
            "application/x-bzip2", "application/x-xz", "application/x-iso9660-image",
        ),
    },
}

# Alias -> canonical category, used to parse the --media-type option
CATEGORY_ALIASES = {
    "video": "video", "videos": "video",
    "foto": "image", "photo": "image", "photos": "image", "image": "image", "images": "image", "immagini": "image",
    "documenti": "document", "documento": "document", "document": "document", "documents": "document", "docs": "document", "doc": "document",
    "archivi": "archive", "archivio": "archive", "archive": "archive", "archives": "archive",
}

CATEGORY_FILENAME_PREFIXES = {
    "video": "video",
    "image": "foto",
    "document": "doc",
    "archive": "archivio",
    "other": "file",
}


async def monitor_skip_key(cancel_event: asyncio.Event, stop_event: asyncio.Event):
    """
    Monitors keyboard input in a non-blocking background loop on Windows.
    Pressing 's', 'S', 'x', 'X' or ESC sets cancel_event.
    """
    if not msvcrt:
        return

    while not stop_event.is_set() and not cancel_event.is_set():
        if msvcrt.kbhit():
            try:
                ch = msvcrt.getch()
                # 's', 'S', 'x', 'X', or ESC (0x1B)
                if ch in (b"s", b"S", b"x", b"X", b"\x1b"):
                    cancel_event.set()
                    break
            except Exception:
                pass
        await asyncio.sleep(0.1)


def parse_size(size_str: Optional[str]) -> Optional[int]:
    """
    Parses a size string (e.g. '1.5GB', '500MB', '2G', 'none')
    and returns the size in bytes as an integer, or None if disabled.
    """
    if not size_str:
        return None

    cleaned = str(size_str).strip().lower()
    if cleaned in ("none", "null", "all", "0", ""):
        return None

    units = {
        "tb": 1024**4,
        "t": 1024**4,
        "gb": 1024**3,
        "g": 1024**3,
        "mb": 1024**2,
        "m": 1024**2,
        "kb": 1024,
        "k": 1024,
        "b": 1,
    }

    match = re.match(r"^([\d.]+)\s*([a-zA-Z]*)$", cleaned)
    if not match:
        raise ValueError(f"Formato dimensione non valido: '{size_str}'. Usa valori come '1.5GB', '500MB', '2GB' o 'none'.")

    val_str, unit = match.groups()
    try:
        val = float(val_str)
    except ValueError:
        raise ValueError(f"Formato dimensione non valido: '{size_str}'.")

    if not unit:
        mult = 1024**2  # Default to MB if only a number is provided
    else:
        mult = units.get(unit)
        if mult is None:
            raise ValueError(f"Unità di misura '{unit}' non supportata. Usa B, KB, MB, GB o TB.")

    return int(val * mult)


def format_bytes(size: int) -> str:
    """Formats bytes into human-readable string (e.g. 1.45 GB)."""
    if size >= 1024**3:
        return f"{size / (1024**3):.2f} GB"
    elif size >= 1024**2:
        return f"{size / (1024**2):.1f} MB"
    elif size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


def parse_resolution(res_str: Optional[str]) -> Optional[int]:
    """
    Parses a resolution string (e.g. '480p', '720p', '1080p', '4k', '2160', 'none')
    and returns the height in pixels as an integer, or None if disabled.
    """
    if not res_str:
        return None

    cleaned = str(res_str).strip().lower()
    if cleaned in ("none", "null", "all", "0", ""):
        return None

    if cleaned == "4k":
        return 2160
    if cleaned == "2k":
        return 1440

    # Remove trailing 'p' or other non-numeric suffix
    match = re.search(r"(\d+)", cleaned)
    if match:
        return int(match.group(1))

    raise ValueError(f"Formato risoluzione non valido: '{res_str}'. Usa valori come '480p', '720p', '1080p', '4k' o 'none'.")


def sanitize_filename(filename: str) -> str:
    """Sanitizes filename for the local operating system."""
    return re.sub(r'[<>:"/\\|?*]', "_", filename).strip()


def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncates string to max_length characters with ellipsis if longer."""
    if not text or len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def detect_media_category(mime_type: Optional[str], ext: Optional[str]) -> str:
    """Resolves a canonical media category from extension (priority) or MIME type, defaulting to 'other'."""
    ext_lower = (ext or "").lower()
    mime_lower = (mime_type or "").lower()

    for category, rules in MEDIA_CATEGORIES.items():
        if ext_lower and ext_lower in rules["extensions"]:
            return category

    for category, rules in MEDIA_CATEGORIES.items():
        if mime_lower and any(mime_lower.startswith(prefix) for prefix in rules["mime_prefixes"]):
            return category

    return "other"


def extract_media_info(message: Message) -> Tuple[bool, str, Optional[str], int, Optional[int], Optional[int], Optional[str]]:
    """
    Extracts media category, suggested filename, file size, width, height and mime type from a message.
    Returns: (is_media, category, filename, file_size, width, height, mime_type)
    """
    if not message.media or not message.file:
        return False, "other", None, 0, None, None, None

    file_info = message.file
    file_size = file_info.size or 0
    width = file_info.width
    height = file_info.height
    mime_type = file_info.mime_type
    filename = file_info.name

    is_video = bool(message.document) and any(
        isinstance(attr, DocumentAttributeVideo) for attr in message.document.attributes
    )
    category = "video" if is_video else detect_media_category(mime_type, file_info.ext)

    # If no explicit filename, generate one based on caption or message ID
    if not filename:
        ext = file_info.ext or ".bin"
        prefix = CATEGORY_FILENAME_PREFIXES.get(category, "file")

        if message.text:
            cleaned_text = sanitize_filename(message.text.strip().split("\n")[0])[:50]
            filename = f"{cleaned_text}_{message.id}{ext}"
        else:
            date_str = message.date.strftime("%Y%m%d_%H%M%S") if message.date else str(message.id)
            filename = f"{prefix}_{message.id}_{date_str}{ext}"
    else:
        filename = sanitize_filename(filename)

    return True, category, filename, file_size, width, height, mime_type


def parse_media_type_filter(value: Optional[str]) -> Optional[List[str]]:
    """Parses the --media-type option into a list of lowercase tokens, or None if no filtering is requested."""
    if not value:
        return None

    tokens = [t.strip().lower() for t in value.split(",") if t.strip()]
    if not tokens or any(t in ("all", "*") for t in tokens):
        return None

    return tokens


def media_matches_filter(
    category: str,
    mime_type: Optional[str],
    ext: Optional[str],
    tokens: Optional[List[str]],
) -> bool:
    """Checks whether a file's category/mime/extension matches any token from --media-type (category alias or MIME glob)."""
    if tokens is None:
        return True

    mime_lower = (mime_type or "").lower()
    ext_clean = (ext or "").lower().lstrip(".")

    for token in tokens:
        if token in ("all", "*"):
            return True
        if CATEGORY_ALIASES.get(token) == category:
            return True
        if mime_lower and fnmatch.fnmatch(mime_lower, token):
            return True
        if ext_clean and fnmatch.fnmatch(ext_clean, token.lstrip("*.")):
            return True

    return False


def matches_pattern(
    filename: str,
    pattern: Optional[str],
    caption: Optional[str] = None,
    search_caption: bool = True,
) -> bool:
    """
    Checks if filename or caption matches the given pattern.
    If pattern contains a known media extension (e.g. '*tutorial*.mp4', '*guida*.pdf'),
    it also extracts the stem to search inside the caption.
    """
    if not pattern:
        return True

    pattern_lower = pattern.lower().strip()

    # 1. Match against filename
    if fnmatch.fnmatch(filename.lower(), pattern_lower):
        return True

    # 2. Match against caption/description
    if search_caption and caption:
        caption_lower = caption.lower()

        # Direct wildcard match on caption
        if fnmatch.fnmatch(caption_lower, pattern_lower):
            return True

        # Extract keyword stem by stripping known media extensions
        pattern_stem = pattern_lower
        for ext in ALL_KNOWN_EXTENSIONS:
            if pattern_stem.endswith(ext):
                pattern_stem = pattern_stem[: -len(ext)]
                break

        # Check wildcard without extension on caption
        if pattern_stem and fnmatch.fnmatch(caption_lower, f"*{pattern_stem.strip('*')}*"):
            return True

        # Check substring match on caption
        clean_keyword = pattern_stem.replace("*", "").replace("?", "").strip()
        if clean_keyword and clean_keyword in caption_lower:
            return True

    return False


async def download_channel_media(
    client: TelegramClient,
    channel: str,
    start_date: Optional[datetime] = None,
    limit: Optional[int] = None,
    pattern: Optional[str] = None,
    output_dir: str = "./downloads",
    search_caption: bool = True,
    reverse: bool = True,
    check_size: bool = False,
    min_res: Optional[str] = "480p",
    max_res: Optional[str] = "1080p",
    max_size: Optional[str] = "1.5GB",
    media_type: Optional[str] = "all",
):
    """
    Downloads media (video, foto, documenti, archivi, ...) from a specified Telegram channel matching filter criteria.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    min_res_val = parse_resolution(min_res)
    max_res_val = parse_resolution(max_res)
    max_size_val = parse_size(max_size)
    media_type_tokens = parse_media_type_filter(media_type)

    console.print(f"[cyan]Risoluzione del canale:[/cyan] [bold]{channel}[/bold]")
    try:
        entity = await client.get_entity(channel)
        channel_title = getattr(entity, "title", channel)
        console.print(f"[green]Connesso al canale:[/green] [bold]{channel_title}[/bold]\n")
    except Exception as e:
        console.print(f"[red]Errore nel trovare il canale '{channel}': {e}[/red]")
        return

    # Normalize start_date with UTC timezone if provided
    if start_date and start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=timezone.utc)

    console.print("[bold yellow]Inizio scansione messaggi...[/bold yellow]")
    if start_date:
        console.print(f"  • Data inizio: [bold]{start_date.strftime('%Y-%m-%d %H:%M:%S UTC')}[/bold]")
    if pattern:
        caption_hint = " (ricerca su nome file e descrizione)" if search_caption else " (solo nome file)"
        console.print(f"  • Filtro pattern: [bold]{pattern}[/bold]{caption_hint}")
    if limit:
        console.print(f"  • Limite file da scaricare: [bold]{limit}[/bold]")

    media_type_info = media_type if media_type_tokens is None and media_type else ", ".join(media_type_tokens) if media_type_tokens else "Tutti"
    console.print(f"  • Tipo di file: [bold]{media_type_info}[/bold]")
    res_info = f"Min: {min_res_val}p" if min_res_val else "Min: Nessuno"
    res_info += f", Max: {max_res_val}p" if max_res_val else ", Max: Nessuno"
    console.print(f"  • Risoluzione consentita (solo video): [bold]{res_info}[/bold]")
    max_size_info = format_bytes(max_size_val) if max_size_val else "Nessuna"
    console.print(f"  • Dimensione massima consentita (solo video): [bold]{max_size_info}[/bold]")
    console.print(f"  • Controllo dimensione duplicati: [bold]{'Attivo' if check_size else 'Disattivato (solo nome file)'}[/bold]")
    console.print(f"  • Cartella output: [bold]{output_path.resolve()}[/bold]")
    console.print(f"  • Ordine: [bold]{'Dal più vecchio al più recente' if reverse else 'Dal più recente al più vecchio'}[/bold]\n")

    downloaded_count = 0
    skipped_count = 0
    scanned_count = 0
    last_scanned_date = None

    # Configure Telethon iter_messages
    iter_kwargs = {}
    if reverse:
        iter_kwargs["reverse"] = True
        if start_date:
            iter_kwargs["offset_date"] = start_date
    else:
        iter_kwargs["reverse"] = False
        if start_date:
            # When newest first, we only process until start_date
            pass

    scan_status = console.status("[cyan]Scansione messaggi in corso... (0 esaminati)[/cyan]")
    scan_status.start()

    try:
        async for message in client.iter_messages(entity, **iter_kwargs):
            scanned_count += 1
            if message.date:
                last_scanned_date = message.date

            date_str = last_scanned_date.strftime('%Y-%m-%d %H:%M:%S') if last_scanned_date else "N/D"
            scan_status.update(
                f"[cyan]Scansione messaggi...[/cyan] [bold cyan]{scanned_count}[/bold cyan] esaminati "
                f"| [bold magenta]Data ult. msg: {date_str}[/bold magenta] "
                f"([green]{downloaded_count}[/green] scaricati, [yellow]{skipped_count}[/yellow] saltati)"
            )

            if not reverse and start_date and message.date < start_date:
                # We reached messages older than start_date in reverse=False mode
                scan_status.stop()
                console.print(f"[yellow]Raggiunta data limite. Scansione completata (Ultimo messaggio: {date_str}).[/yellow]")
                break

            is_media, category, filename, file_size, width, height, mime_type = extract_media_info(message)
            if not is_media or not filename:
                continue

            if not media_matches_filter(category, mime_type, Path(filename).suffix, media_type_tokens):
                continue

            caption = message.text or ""
            if not matches_pattern(filename, pattern, caption=caption, search_caption=search_caption):
                continue

            is_video = category == "video"

            # Resolution filter (video only): consider min(width, height) as effective vertical resolution
            effective_res = None
            if is_video and width and height:
                effective_res = min(width, height)
            elif is_video and height:
                effective_res = height
            elif is_video and width:
                effective_res = width

            if effective_res is not None:
                if min_res_val and effective_res < min_res_val:
                    skipped_count += 1
                    scan_status.stop()
                    console.print(
                        f"[dim][Saltato (msg #{scanned_count}) - risoluzione {effective_res}p inferiore a min {min_res_val}p][/dim] "
                        f"[dim white]{filename}[/dim white]"
                    )
                    if caption.strip():
                        console.print(f"  [italic yellow]Descrizione:[/italic yellow] [dim]{escape(caption.strip())}[/dim]")
                    scan_status.start()
                    continue
                if max_res_val and effective_res > max_res_val:
                    skipped_count += 1
                    scan_status.stop()
                    console.print(
                        f"[dim][Saltato (msg #{scanned_count}) - risoluzione {effective_res}p superiore a max {max_res_val}p][/dim] "
                        f"[dim white]{filename}[/dim white]"
                    )
                    if caption.strip():
                        console.print(f"  [italic yellow]Descrizione:[/italic yellow] [dim]{escape(caption.strip())}[/dim]")
                    scan_status.start()
                    continue

            # Maximum file size filter (video only)
            if is_video and max_size_val and file_size > max_size_val:
                skipped_count += 1
                scan_status.stop()
                console.print(
                    f"[dim][Saltato (msg #{scanned_count}) - dimensione {format_bytes(file_size)} superiore a max {format_bytes(max_size_val)}][/dim] "
                    f"[dim white]{filename}[/dim white]"
                )
                if caption.strip():
                    console.print(f"  [italic yellow]Descrizione:[/italic yellow] [dim]{escape(caption.strip())}[/dim]")
                scan_status.start()
                continue

            target_file = output_path / filename

            # Duplicate checking logic
            is_already_downloaded = False
            if target_file.exists():
                if check_size:
                    if target_file.stat().st_size == file_size:
                        is_already_downloaded = True
                    else:
                        # Size differs: apply suffix to avoid overwriting distinct file
                        target_file = output_path / f"{target_file.stem}_{message.id}{target_file.suffix}"
                        if target_file.exists() and target_file.stat().st_size == file_size:
                            is_already_downloaded = True
                else:
                    is_already_downloaded = True

            if is_already_downloaded:
                skipped_count += 1
                scan_status.stop()
                console.print(f"[dim][Saltato (msg #{scanned_count}) - già presente #{skipped_count}][/dim] [dim white]{target_file.name}[/dim white]")
                if caption.strip():
                    console.print(f"  [italic yellow]Descrizione:[/italic yellow] [dim]{escape(caption.strip())}[/dim]")
                scan_status.start()
                continue

            scan_status.stop()

            display_name = truncate_text(target_file.name, 50)
            msg_date_str = message.date.strftime("%Y-%m-%d %H:%M")
            res_tag = f" - {width}x{height} ({effective_res}p)" if (width and height and effective_res) else ""
            console.print(
                f"\n[bold blue]({downloaded_count + 1}/{limit or '∞'}) Download (msg #{scanned_count}):[/bold blue] "
                f"[bold white]{display_name}[/bold white] "
                f"[dim]({msg_date_str}{res_tag} - ID: {message.id})[/dim]"
            )
            if caption.strip():
                console.print(f"  [italic yellow]Descrizione:[/italic yellow] [dim]{escape(caption.strip())}[/dim]")
            if msvcrt:
                console.print("  [dim cyan](Premi [bold]S[/bold] o [bold]ESC[/bold] per annullare questo download e passare al prossimo senza conteggiarlo)[/dim cyan]")

            # Use a temporary .part file during download to avoid corrupted or incomplete files
            temp_file = output_path / f"{target_file.name}.part"
            if temp_file.exists():
                temp_file.unlink(missing_ok=True)

            # Setup events for keyboard cancellation
            cancel_event = asyncio.Event()
            stop_key_monitor = asyncio.Event()
            key_monitor_task = asyncio.create_task(monitor_skip_key(cancel_event, stop_key_monitor))
            download_aborted = False
            download_success = False

            # Progress bar setup
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task_id = progress.add_task(f"[cyan]{display_name}", total=file_size)

                def progress_callback(current, total):
                    progress.update(task_id, completed=current, total=total)

                while True:
                    try:
                        dl_task = asyncio.create_task(
                            client.download_media(
                                message,
                                file=str(temp_file),
                                progress_callback=progress_callback,
                            )
                        )
                        cancel_waiter = asyncio.create_task(cancel_event.wait())

                        done, pending = await asyncio.wait(
                            [dl_task, cancel_waiter],
                            return_when=asyncio.FIRST_COMPLETED,
                        )

                        if cancel_waiter in done:
                            # User pressed skip key
                            dl_task.cancel()
                            try:
                                await dl_task
                            except (asyncio.CancelledError, Exception):
                                pass
                            download_aborted = True
                            break
                        else:
                            cancel_waiter.cancel()
                            # dl_task completed successfully
                            await dl_task
                            download_success = True
                            break
                    except errors.FloodWaitError as e:
                        console.print(f"[yellow]Rate limit Telegram (FloodWait). Attendo {e.seconds} secondi...[/yellow]")
                        await asyncio.sleep(e.seconds)
                    except Exception as e:
                        console.print(f"[red]Errore durante il download del file {target_file.name}: {e}[/red]")
                        break

            # Stop key monitor task
            stop_key_monitor.set()
            try:
                await key_monitor_task
            except Exception:
                pass

            if download_aborted or not download_success:
                if temp_file.exists():
                    temp_file.unlink(missing_ok=True)
                if download_aborted:
                    console.print(
                        f"[yellow]Download di '{target_file.name}' annullato dall'utente (non conteggiato). "
                        f"File parziale eliminato.[/yellow]"
                    )
                scan_status.start()
                continue

            # Rename .part file to target file upon 100% successful completion
            if temp_file.exists():
                temp_file.replace(target_file)
                downloaded_count += 1

            if limit and downloaded_count >= limit:
                console.print(f"\n[green]Raggiunto il limite di {limit} file scaricati.[/green]")
                break

            scan_status.start()
    finally:
        scan_status.stop()

    last_date_info = f" (fino al {last_scanned_date.strftime('%Y-%m-%d %H:%M:%S')})" if last_scanned_date else ""
    console.print(
        f"\n[bold green]Operazione completata![/bold green]\n"
        f"  • Nuovi file scaricati: [bold green]{downloaded_count}[/bold green]\n"
        f"  • File già presenti saltati: [bold yellow]{skipped_count}[/bold yellow]\n"
        f"  • Totale messaggi scansionati: [bold]{scanned_count}[/bold]{last_date_info}"
    )
