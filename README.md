# YouTube → Spotify Playlist Updater

Script en Python que sincroniza automáticamente una playlist de YouTube Music con una playlist de Spotify. Detecta videos nuevos, busca las canciones correspondientes en Spotify y las agrega a la playlist destino.

---

## Requisitos Previos

- **Python 3.8+**
- **Conexión a internet**

### 1. Obtener YouTube Data API Key

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un proyecto o selecciona uno existente
3. Habilita la **YouTube Data API v3** desde la biblioteca de APIs
4. Ve a **Credenciales** → **Crear credenciales** → **API Key**
5. (Opcional) Restringe la key por referer o por API para mayor seguridad

### 2. Obtener Spotify API Credentials

1. Ve a [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Inicia sesión y haz clic en **Create App**
3. Ponle un nombre y descripción (ej. "YouTube-to-Spotify Updater")
4. Una vez creada, copia el **Client ID** y el **Client Secret**
5. Haz clic en **Edit Settings** y agrega `http://localhost:8888/callback` como **Redirect URI**

### 3. Obtener los IDs de las playlists

**YouTube:** La URL tiene este formato: `https://www.youtube.com/playlist?list=PL...` — el ID es lo que sigue a `list=`.

**Spotify:** La URL tiene este formato: `https://open.spotify.com/playlist/4wSSnJQOP3T...` — el ID es el segmento después de `/playlist/`.

---

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/youtube-to-spotify-updater.git
cd youtube-to-spotify-updater

# Crear y activar entorno virtual
python -m venv venv

# Windows
.\venv\Scripts\activate
# macOS/Linux
# source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Copiar el archivo de ejemplo de variables de entorno
cp .env-example .env
```

---

## Configuración (`.env`)

Edita el archivo `.env` con tus credenciales:

```env
# --- Spotify ---

# Client ID y Client Secret de tu app en Spotify Developer Dashboard
SPOTIPY_CLIENT_ID=tu_client_id
SPOTIPY_CLIENT_SECRET=tu_client_secret

# Redirect URI configurada en la app de Spotify (por defecto http://localhost:8888/callback)
# Se recomienda utilizar http://127.0.0.1:8888/callback
SPOTIPY_REDIRECT_URI=http://localhost:8888/callback

# ID de la playlist de Spotify donde se agregarán las canciones
SPOTIFY_PLAYLIST_ID=4wSSnJQOP3TazWNMhKTCJ9

# --- YouTube ---

# API Key generada en Google Cloud Console
YOUTUBE_API_KEY=tu_api_key

# ID de la playlist de YouTube que se quiere sincronizar
YOUTUBE_PLAYLIST_ID=PLEeJuHePCsFfSi8wEU5y7JBvZRLkKTM-f
```

> `SPOTIPY_REDIRECT_URI` tiene un valor por defecto de `http://localhost:8888/callback` en el código, así que puedes omitirla si ese es el URI que configuraste en Spotify.

---

## Uso

```bash
python main.py
```

La **primera ejecución** abrirá el navegador para autenticar con Spotify mediante OAuth. Tras autorizar, el token se guarda en `.cache` y las ejecuciones posteriores lo reutilizarán automáticamente.

---

## ¿Cómo funciona?

1. **Obtiene los videos** de la playlist de YouTube mediante la API (paginada, hasta 50 por request).
2. **Compara** con el archivo `state.json` para identificar qué videos son nuevos (no procesados antes).
3. Para cada video nuevo:
   - **Limpia el título** con `clean_title()` — elimina texto entre paréntesis/corchetes y extrae la parte después del guion (`"Artista - Título"`).
   - **Limpia el artista** con `clean_artist()` — elimina sufijos como `VEVO`, `Official`, `Topic`, `Channel`.
   - **Busca en Spotify** con la consulta `track:<título> artist:<artista>`.
   - Si encuentra la canción **y no está ya** en la playlist, la agrega.
   - Guarda el resultado en `state.json`.

---

## Edge Cases — Limpieza de títulos

Los títulos de YouTube suelen incluir ruido que dificulta la búsqueda en Spotify. El script aplica dos limpiezas:

### `clean_title()`
- Elimina todo lo que esté entre `(...)` o `[...]`, incluyendo paréntesis y corchetes anidados.
- Si el título contiene `"Artista - Título"`, se queda con la parte después del primer guion.

### `clean_artist()`
- Elimina (case-insensitive): `VEVO`, `Official`, `Oficial`, `Topic`, `Channel`.
- Limpia guiones y espacios sobrantes.

| Video de YouTube | Título limpio | Artista limpio |
|---|---|---|
| `Mitski - Liquid Smooth (Official Audio)` | `Liquid Smooth` | `Mitski` |
| `Laufey - Valentine [Lyric Video]` | `Valentine` | `Laufey` |
| `TWICE - SAY SOMETHING` | `SAY SOMETHING` | `TWICE` |
| `Shihoko Hirata - Topic - Heaven` | `Heaven` | `Shihoko Hirata` |
| `MitskiVEVO - Last Song` | `Last Song` | `Mitski` |
| `ANRI - Topic` (canal) | *(no aplica)* | `ANRI` |
| `Liana Flores - rises the moon` | `rises the moon` | `Liana Flores` |

**Limitaciones conocidas:**
- Si el artista real contiene palabras como "Topic" en su nombre, la limpieza podría dañarlo.
- Si el título usa paréntesis como parte legítima del nombre (ej. `"(I've Had) The Time of My Life"`), se perderá esa parte.
- En esos casos la canción quedará marcada como `"not_found"` en `state.json`.

---

## Estructura del proyecto

```
youtube-to-spotify-updater/
├── main.py              # Script principal
├── requirements.txt     # Dependencias (spotipy, google-api-python-client, python-dotenv)
├── .env-example         # Template del archivo .env
├── .gitignore
└── README.md
```

---

## `state.json`

Archivo que almacena el estado de la sincronización para evitar reprocesar canciones:

```json
{
  "youtube_playlist_id": "PLEeJuHePCsFfSi8wEU5y7JBvZRLkKTM-f",
  "spotify_playlist_id": "4wSSnJQOP3TazWNMhKTCJ9",
  "processed": {
    "video_id_1": {
      "title": "Título original en YouTube",
      "channel": "Canal original",
      "status": "added",
      "spotify_track_id": "id_de_spotify"
    },
    "video_id_2": {
      "title": "Título original",
      "channel": "Canal original",
      "status": "not_found"
    }
  }
}
```

- `status` puede ser: `"added"`, `"already_in_playlist"`, `"not_found"`.
- Si cambias la playlist de YouTube o Spotify (cambian los IDs en `.env`), el estado se reinicia automáticamente.
- Se guarda en cada iteración, así que si el script se interrumpe, no pierde progreso.

---

## Notas / Limitaciones

- **Cuota de YouTube API:** Tienes 10,000 unidades/día gratis. Cada request cuesta ~1-5 unidades. Una playlist con ~100 videos puede consumir ~100 unidades.
- **Rate limit de Spotify:** El script espera 0.5 segundos entre cada búsqueda.
- **OAuth de Spotify:** La primera ejecución abre el navegador. El token se guarda en `.cache` y se refresca automáticamente.
- **Solo procesa videos nuevos:** Si un video ya fue procesado (está en `state.json`), se omite.
- **No borra canciones:** Si eliminas un video de YouTube, la canción correspondiente en Spotify **no** se elimina.
