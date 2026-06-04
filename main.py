import os
import json
import time
import re

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

STATE_FILE = "state.json"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"


def load_state():
    if not os.path.exists(STATE_FILE):
        return {"youtube_playlist_id": None, "spotify_playlist_id": None, "processed": {}}
    
    with open(STATE_FILE) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            # Si el archivo existe pero está vacío o corrupto, retornamos la estructura base
            print(f"Advertencia: {STATE_FILE} estaba vacío o corrupto. Se creará uno nuevo.")
            return {"youtube_playlist_id": None, "spotify_playlist_id": None, "processed": {}}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_youtube_playlist_videos(youtube, playlist_id):
    videos = []
    next_page_token = None

    while True:
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token,
        )
        response = request.execute()

        for item in response.get("items", []):
            snippet = item["snippet"]
            video_id = snippet["resourceId"]["videoId"]
            videos.append({
                "id": video_id,
                "title": snippet["title"],
                "channel": snippet.get("videoOwnerChannelTitle") or snippet["channelTitle"],
                "published_at": snippet["publishedAt"],
            })

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return videos


def clean_title(title):
    # Elimina texto entre paréntesis o corchetes: (Official Video), [Lyric Video], etc.
    title = re.sub(r'[\(\[].*?[\)\]]', '', title)
    # Si el formato del título de YouTube es "Artista - Título", nos quedamos con el título
    if '-' in title:
        title = title.split('-', 1)[-1]
    return title.strip()


def clean_artist(artist):
    # Elimina sufijos comunes de canales de YouTube sin importar mayúsculas/minúsculas
    artist = re.sub(r'(?i)(VEVO|Official|Oficial|Topic|Channel)', '', artist)
    # Limpia guiones residuales y espacios
    return artist.strip(' -').strip()


def search_spotify_track(sp, title, artist):
    query = f"track:{title} artist:{artist}"
    results = sp.search(q=query, type="track", limit=1)
    tracks = results.get("tracks", {}).get("items", [])
    return tracks[0] if tracks else None


def get_playlist_track_ids(sp, playlist_id):
    track_ids = set()
    results = sp.playlist_tracks(playlist_id)
    while results:
        for item in results.get("items", []):
            track = item.get("track")
            if track and track.get("id"):
                track_ids.add(track["id"])
        results = sp.next(results) if results.get("next") else None
    return track_ids


def main():
    required = [
        "SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET",
        "SPOTIFY_PLAYLIST_ID", "YOUTUBE_API_KEY", "YOUTUBE_PLAYLIST_ID",
    ]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        print(f"Missing required env vars: {', '.join(missing)}")
        return

    youtube_playlist_id = os.getenv("YOUTUBE_PLAYLIST_ID")
    spotify_playlist_id = os.getenv("SPOTIFY_PLAYLIST_ID")

    state = load_state()
    if state["youtube_playlist_id"] != youtube_playlist_id or state["spotify_playlist_id"] != spotify_playlist_id:
        state = {
            "youtube_playlist_id": youtube_playlist_id,
            "spotify_playlist_id": spotify_playlist_id,
            "processed": {},
        }

    processed_ids = set(state["processed"].keys())

    youtube = build(
        YOUTUBE_API_SERVICE_NAME,
        YOUTUBE_API_VERSION,
        developerKey=os.getenv("YOUTUBE_API_KEY"),
    )

    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback"),
        scope="playlist-modify-public playlist-modify-private",
    ))

    print("Fetching YouTube playlist videos...")
    youtube_videos = get_youtube_playlist_videos(youtube, youtube_playlist_id)
    print(f"Found {len(youtube_videos)} videos in YouTube playlist.")

    new_videos = [v for v in youtube_videos if v["id"] not in processed_ids]
    if not new_videos:
        print("No new videos to add.")
        return

    print(f"Found {len(new_videos)} new video(s) to process.")
    existing_spotify_tracks = get_playlist_track_ids(sp, spotify_playlist_id)

    for video in new_videos:
        original_title = video["title"]
        original_artist = video["channel"]
        
        # Aplicamos la limpieza de texto aquí
        clean_t = clean_title(original_title)
        clean_a = clean_artist(original_artist)
        
        print(f"Processing: {original_artist} - {original_title}")
        print(f"  -> Searching Spotify as: {clean_a} - {clean_t}")

        track = search_spotify_track(sp, clean_t, clean_a)
        if track and track["id"] not in existing_spotify_tracks:
            sp.playlist_add_items(spotify_playlist_id, [track["id"]])
            print(f"  -> Added: \"{track['name']}\" by {track['artists'][0]['name']}")
            state["processed"][video["id"]] = {
                "title": original_title,
                "channel": original_artist,
                "status": "added",
                "spotify_track_id": track["id"],
            }
            existing_spotify_tracks.add(track["id"])
            time.sleep(0.5)
        elif track:
            print(f"  -> Already in playlist: \"{track['name']}\"")
            state["processed"][video["id"]] = {
                "title": original_title,
                "channel": original_artist,
                "status": "already_in_playlist",
            }
        else:
            print(f"  -> Not found on Spotify")
            state["processed"][video["id"]] = {
                "title": original_title,
                "channel": original_artist,
                "status": "not_found",
            }

        save_state(state)

    print("Done!")


if __name__ == "__main__":
    main()