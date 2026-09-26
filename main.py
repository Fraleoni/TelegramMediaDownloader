import asyncio
from datetime import datetime
from typing import Optional

import typer
from rich.console import Console

from client import get_telegram_client
from config import DEFAULT_DOWNLOAD_PATH, validate_credentials
from downloader import download_channel_media

app = typer.Typer(
    help="Telegram Media Downloader - Scarica video e altri file (foto, documenti, archivi...) da canali Telegram con filtri per data, quantità e pattern nome file.",
    add_completion=False,
)
console = Console()


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parses date string in YYYY-MM-DD or YYYY-MM-DD HH:MM:SS format."""
    if not date_str:
        return None

    formats = ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%d/%m/%Y %H:%M:%S"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    raise typer.BadParameter(
        f"Formato data non valido: '{date_str}'. Usa YYYY-MM-DD o 'YYYY-MM-DD HH:MM:SS'."
    )


@app.command()
def download(
    channel: str = typer.Option(
        ...,
        "--channel",
        "-c",
        help="Username del canale (es. @nomecanale), link (t.me/...), o ID.",
        prompt="Inserisci l'username o link del canale Telegram",
    ),
    start_date: Optional[str] = typer.Option(
        None,
        "--start-date",
        "-d",
        help="Data di inizio da cui scaricare i video (es. 2024-01-01 o '2024-01-01 00:00:00').",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-l",
        help="Numero massimo di video da scaricare.",
    ),
    pattern: Optional[str] = typer.Option(
        None,
        "--pattern",
        "-p",
        help="Pattern per filtrare nome file o testo descrizione/caption (es. '*tutorial*.mp4', '*guida*', '*.pdf').",
    ),
    media_type: Optional[str] = typer.Option(
        "all",
        "--media-type",
        "-t",
        help=(
            "Categorie e/o pattern MIME dei file da scaricare, separati da virgola: video, foto, documenti, archivi, "
            "oppure pattern come 'image/*' o 'application/pdf' (default: 'all' = tutti i formati)."
        ),
    ),
    output: str = typer.Option(
        DEFAULT_DOWNLOAD_PATH,
        "--output",
        "-o",
        help="Cartella di destinazione dei download.",
    ),
    search_caption: bool = typer.Option(
        True,
        "--search-caption/--no-search-caption",
        help="Cerca il pattern sia nel nome del file che nella descrizione/caption del post (default: True).",
    ),
    check_size: bool = typer.Option(
        False,
        "--check-size/--no-check-size",
        help="Verifica anche la dimensione del file oltre al nome per considerare il file duplicato (default: False, salta solo per nome).",
    ),
    min_res: Optional[str] = typer.Option(
        "480p",
        "--min-res",
        help="Risoluzione minima del video (es. '480p', '720p', '1080p', 'none' per disattivare; default: '480p').",
    ),
    max_res: Optional[str] = typer.Option(
        "1080p",
        "--max-res",
        help="Risoluzione massima del video (es. '720p', '1080p', '4k', 'none' per disattivare; default: '1080p').",
    ),
    max_size: Optional[str] = typer.Option(
        "1.5GB",
        "--max-size",
        help="Dimensione massima del video da scaricare (es. '500MB', '1.5GB', '2GB', 'none' per disattivare; default: '1.5GB').",
    ),
    reverse: bool = typer.Option(
        True,
        "--reverse/--no-reverse",
        help="Scarica dal più vecchio al più recente a partire da start-date (default: True).",
    ),
    extra_args: Optional[list[str]] = typer.Argument(
        None,
        hidden=True,
        help="Cattura eventuali argomenti extra non previsti.",
    ),
):
    """
    Scarica video e altri file da un canale Telegram specificato con filtri avanzati.
    """
    if extra_args:
        console.print(
            "\n[bold red]Errore: ricevuti argomenti extra non previsti da terminale:[/bold red]\n"
            f"  [yellow]{' '.join(extra_args)}[/yellow]\n\n"
            "[bold cyan]Causa probabile:[/bold cyan]\n"
            "Il terminale (PowerShell o Bash) ha espanso il carattere asterisco [bold]`*`[/bold] nell'elenco dei file presenti nella cartella corrente.\n\n"
            "[bold green]Come risolvere:[/bold green]\n"
            "• Se vuoi scaricare tutti i file, [bold]ometti del tutto il parametro -p[/bold] (default: tutti i file).\n"
            "• Se usi un pattern con asterischi in PowerShell, racchiudilo tra apici singoli, es: [bold]-p '*pattern*'[/bold] oppure [bold]-p '*'[/bold].\n"
        )
        raise typer.Exit(code=1)

    try:
        validate_credentials()
    except ValueError as e:
        console.print(f"[bold red]{e}[/bold red]")
        raise typer.Exit(code=1)

    parsed_start_date = parse_date(start_date)

    async def runner():
        client = get_telegram_client()
        await client.start()
        try:
            await download_channel_media(
                client=client,
                channel=channel,
                start_date=parsed_start_date,
                limit=limit,
                pattern=pattern,
                output_dir=output,
                search_caption=search_caption,
                reverse=reverse,
                check_size=check_size,
                min_res=min_res,
                max_res=max_res,
                max_size=max_size,
                media_type=media_type,
            )
        finally:
            await client.disconnect()

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Esecuzione interrotta dall'utente.[/bold yellow]")


if __name__ == "__main__":
    app()
