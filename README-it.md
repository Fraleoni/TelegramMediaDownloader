# Telegram Media Downloader

🇬🇧 [Read in English](README.md)

Tool automatico in Python per il download intelligente di file multimediali (video, foto, documenti, archivi, ...) da canali Telegram con filtri avanzati per data, tipo di file, pattern di nome file e limite di download.

---

## 🚀 Caratteristiche

* **Nessun limite di 20 MB / 50 MB**: Utilizza le API MTProto di Telethon (supporta download fino a 2 GB per account standard e 4 GB per Telegram Premium).
* **Filtro per Data di Inizio (`--start-date`)**: Recupera i messaggi a partire da una data precisa (`YYYY-MM-DD` o `YYYY-MM-DD HH:MM:SS`).
* **Filtro con Wildcard (`--pattern`)**: Cerca il pattern specificato (es. `*tutorial*.mp4`, `*guida*`, `*1080p*`) contemporaneamente sia nel **nome del file** che nel testo della **descrizione (caption)** del post Telegram.
* **Filtro Tipo di File (`--media-type`)**: Scarica solo le categorie scelte (`video`, `foto`, `documenti`, `archivi`) o pattern MIME (es. `image/*`, `application/pdf`); il default `all` scarica tutti i formati.
* **Limite Quantità (`--limit`)**: Imposta il numero massimo di file da scaricare.
* **Filtro Risoluzione Video (`--min-res` / `--max-res`)**: Filtra i video in base alla risoluzione originale prima del download (default: minimo `480p`, massimo `1080p`).
* **Filtro Dimensione Massima (`--max-size`)**: Imposta una dimensione massima consentita per i video da scaricare (default: `1.5GB`).
* **Controllo Duplicati Intelligente**: Salta automaticamente i file già scaricati senza conteggiarli nel limite `--limit` (es. se imposti `-l 5` scaricherà 5 **nuovi** video effettivi).
* **Controllo Dimensione Opzionale (`--check-size`)**: Di default salta il download se il file esiste già per nome; attivando `--check-size` verifica che anche la dimensione del file corrisponda esattamente.
* **Fallback Intelligente**: Riconosce sia video nativi che file documento video; se il file non ha nome, ricava un nome pulito dal testo/caption del post.
* **Feedback e Scansione in Tempo Reale**: Mostra un contatore live con il numero di messaggi esaminati, la data corrente di scansione, i file scaricati e quelli saltati.
* **Interruzione / Skip al Volo**: Durante il download di qualsiasi video, premendo **`S`** o **`ESC`** il download corrente viene interrotto istantaneamente, il file parziale/incompleto su disco viene eliminato e lo script passa al messaggio successivo.
* **Barra di avanzamento interattiva**: Mostra velocità di trasferimento (MB/s), percentuale e tempo trascorso per ogni download con la libreria `rich`.
* **Gestione Rate-Limit**: Gestisce automaticamente i `FloodWaitError` di Telegram riprendendo al termine dell'attesa.

---

## 📦 Installazione

### 1. Clona o apri la cartella del progetto
```bash
cd d:\Progetti\TelegramMediaDownloader
```

### 2. Crea e attiva l'ambiente virtuale
```bash
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Windows (CMD):
.\venv\Scripts\activate.bat

# Linux / macOS:
source venv/bin/activate
```

### 3. Installa le dipendenze
```bash
pip install -r requirements.txt
```

---

## 🔑 Configurazione Telegram API

Per utilizzare il client Telegram è necessario ottenere `API_ID` e `API_HASH`:

1. Accedi a [https://my.telegram.org](https://my.telegram.org) con il tuo numero di telefono Telegram.
2. Vai su **"API development tools"**.
3. Crea una nuova applicazione (es. nome: `MediaDownloader`).
4. Copia `api_id` e `api_hash`.
5. Crea un file `.env` a partire dal file di esempio:
   ```bash
   cp .env.example .env
   ```
6. Inserisci le tue credenziali nel file `.env`:
   ```ini
   TG_API_ID=12345678
   TG_API_HASH=abcdef1234567890abcdef1234567890
   TG_SESSION_NAME=session_downloader
   DEFAULT_DOWNLOAD_PATH=./downloads
   ```

*Nota: Al primo avvio, Telethon ti chiederà da terminale il tuo numero di telefono e il codice di verifica inviato su Telegram (e la password 2FA se attiva). La sessione verrà salvata localmente nel file `.session`.*

---

## 💻 Esempi d'uso

### Esempio 1: Download con pattern e limite
Scarica i primi 5 video che contengono la parola "tutorial" nel nome o nella caption:
```bash
python main.py --channel @nomecanale --pattern "*tutorial*.mp4" --limit 5
```

### Esempio 2: Download a partire da una data specifica
Scarica tutti i video pubblicati a partire dal 1° Gennaio 2024:
```bash
python main.py --channel @nomecanale --start-date 2024-01-01
```

### Esempio 3: Download completo con tutti i parametri
Scarica fino a 10 video `.mp4` a partire dal 15 Giugno 2024, salvandoli in una cartella personalizzata:
```bash
python main.py -c @nomecanale -d 2024-06-15 -l 10 -p "*.mp4" -o "./miei_video"
```

### Esempio 4: Download per tipo di file
Scarica fino a 50 documenti e archivi pubblicati a partire dal 18 Luglio 2023, usando direttamente il Python dell'ambiente virtuale:
```bash
.\venv\Scripts\python.exe main.py -c "t.me/nomecanale" -d 2023-07-18 -l 50 --media-type documenti,archivi -o "./file"
```

### Opzioni CLI disponibili

| Flag | Abbreviazione | Descrizione | Default |
|------|--------------|-------------|---------|
| `--channel` | `-c` | Username (`@canale`), link (`https://t.me/...`) o ID canale | *Richiesto* |
| `--start-date` | `-d` | Data inizio (`YYYY-MM-DD` o `YYYY-MM-DD HH:MM:SS`) | Nessuna |
| `--limit` | `-l` | Numero massimo di file da scaricare | Tutti |
| `--pattern` | `-p` | Pattern wildcard per il nome file (es. `*lezione*.mp4`) | Tutti |
| `--media-type` | `-t` | Categorie separate da virgola (`video`, `foto`, `documenti`, `archivi`) o pattern MIME (es. `image/*`) | `all` |
| `--min-res` | | Risoluzione minima consentita (es. `480p`, `720p`, `none`) | `480p` |
| `--max-res` | | Risoluzione massima consentita (es. `1080p`, `4k`, `none`) | `1080p` |
| `--max-size` | | Dimensione massima del file (es. `500MB`, `1.5GB`, `none`) | `1.5GB` |
| `--output` | `-o` | Cartella di salvataggio dei file | `./downloads` |
| `--check-size` / `--no-check-size` | | Verifica anche la dimensione del file per considerare il duplicato | `False` (solo nome) |
| `--search-caption` / `--no-search-caption` | | Cerca il pattern anche nella caption del post | `True` |
| `--reverse` / `--no-reverse` | | Scarica dal più vecchio al più recente a partire da `start-date` | `True` |

---

## 🛡️ Note di sicurezza
* Non condividere mai il tuo file `.env` o il file `.session`.
* Il file `.gitignore` è già configurato per escludere sessioni, download e variabili d'ambiente.
