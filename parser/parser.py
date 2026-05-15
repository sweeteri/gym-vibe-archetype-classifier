import os
import pandas as pd
from lyricsgenius import Genius
import pylast
import requests
import time
from dotenv import load_dotenv

load_dotenv()


class MusicDataCollector:
    def __init__(self):
        self.spotify_blocked = True
        self.sp = None
        print("! Spotify is temporarily DISABLED due to rate limits.")

        genius_token = os.getenv('GENIUS_ACCESS_TOKEN')
        if genius_token and genius_token != "your_genius_access_token":
            self.genius = Genius(genius_token)
            self.genius.verbose = False
            self.genius.remove_section_headers = True
        else:
            self.genius = None
            print("! Genius Token не настроен. Пропускаю поиск текста песен.")

        lastfm_key = os.getenv('LASTFM_API_KEY')
        lastfm_secret = os.getenv('LASTFM_API_SECRET')
        if lastfm_key and lastfm_secret:
            self.network = pylast.LastFMNetwork(api_key=lastfm_key, api_secret=lastfm_secret)
        else:
            self.network = None
            print("Warning: Last.fm credentials missing. Tags will be skipped.")

    def get_spotify_data(self, track_name, artist_name, spotify_id=None):
        """Spotify is currently disabled due to rate limits."""
        return None

    def get_lastfm_tags(self, track_name, artist_name):
        if not self.network: return None
        try:
            track = self.network.get_track(artist_name, track_name)
            top_tags = track.get_top_tags(limit=10)

            if not top_tags:
                artist = self.network.get_artist(artist_name)
                top_tags = artist.get_top_tags(limit=10)

            tags_str = ", ".join([tag.item.name for tag in top_tags])

            stats = {
                "lastfm_playcount": track.get_playcount(),
                "lastfm_listeners": track.get_listeners(),
                "lastfm_tags": tags_str
            }
            return stats
        except Exception:
            return {"lastfm_tags": None}

    def get_itunes_info(self, track_name, artist_name):
        try:
            query = f"{artist_name} {track_name}"
            url = f"https://itunes.apple.com/search?term={query}&entity=song&limit=1"
            res = requests.get(url, timeout=5).json()
            if res.get('resultCount', 0) > 0:
                item = res['results'][0]
                return {
                    "itunes_genre": item.get("primaryGenreName"),
                    "itunes_release_date": item.get("releaseDate"),
                    "itunes_release_year": (item.get("releaseDate") or "0000")[:4],
                    "itunes_track_view_url": item.get("trackViewUrl"),
                    "itunes_preview_url": item.get("previewUrl"),
                    "itunes_artwork": item.get("artworkUrl100"),
                    "itunes_explicit": item.get("trackExplicitness") == "explicit",
                    "itunes_duration_ms": item.get("trackTimeMillis"),
                    "itunes_country": item.get("country"),
                    "itunes_collection_name": item.get("collectionName"),
                    "itunes_artist_id": item.get("artistId"),
                    "itunes_artist_view_url": item.get("artistViewUrl")
                }
            return {}
        except:
            return {}

    def get_deezer_info(self, track_name, artist_name):
        query = f"{artist_name} {track_name}"
        try:
            search_res = requests.get(
                "https://api.deezer.com/search",
                params={"q": query, "limit": 5},
                timeout=10
            ).json()

            if not search_res.get("data"):
                return {}

            best_match = None
            for candidate in search_res["data"]:
                c_artist = candidate["artist"]["name"].lower()
                u_artist = artist_name.lower()
                if u_artist in c_artist or c_artist in u_artist:
                    best_match = candidate
                    break

            if not best_match:
                best_match = search_res["data"][0]

            track_details = requests.get(
                f"https://api.deezer.com/track/{best_match['id']}",
                timeout=10
            ).json()

            genre = ""
            if "genres" in track_details and track_details["genres"].get("data"):
                genre = track_details["genres"]["data"][0].get("name", "")

            artist_fans = 0
            try:
                artist_details = requests.get(
                    best_match['artist']['link'].replace('www.deezer.com', 'api.deezer.com')).json()
                artist_fans = artist_details.get('nb_fan', 0)
            except:
                pass

            return {
                "deezer_id": best_match.get("id"),
                "deezer_isrc": track_details.get("isrc"),
                "bpm": track_details.get("bpm"),
                "rank": track_details.get("rank"),
                "gain": track_details.get("gain"),
                "deezer_genre": genre,
                "deezer_album_name": best_match.get("album", {}).get("title"),
                "deezer_explicit": track_details.get("explicit_lyrics", False),
                "deezer_preview": track_details.get("preview"),
                "deezer_artist_fans": artist_fans,
                "status_dz": "ok"
            }
        except Exception as e:
            print(f"  ! Deezer error: {e}")
            return {"status_dz": "error"}

    def get_lyrics(self, track_name, artist_name, retries=2):
        if not self.genius or not track_name or not artist_name: return None

        for attempt in range(retries + 1):
            try:
                song = self.genius.search_song(track_name, artist_name)
                if song:
                    if artist_name.lower() in song.artist.lower() or song.artist.lower() in artist_name.lower():
                        return song.lyrics
                return None
            except Exception as e:
                err_str = str(e)
                if "503" in err_str or "504" in err_str or "overloaded" in err_str.lower():
                    if attempt < retries:
                        wait_time = 4 * (attempt + 1)
                        print(f"  ! Genius is overloaded. Retrying in {wait_time}s... ({attempt + 1}/{retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        print("  ! Genius is offline/overloaded. Skipping.")
                elif "song_info" in err_str:
                    print(f"  ! Genius internal library error (song_info). Skipping this track.")
                    return None
                else:
                    print(f"  ! Genius error: {e}")
                return None
        return None

    def process_csv(self, input_path, output_path, start_idx=0, end_idx=None):
        if not os.path.exists(input_path):
            print(f"Error: {input_path} not found.")
            return

        try:
            df = pd.read_csv(input_path, encoding='utf-8-sig')
        except UnicodeDecodeError:
            df = pd.read_csv(input_path, encoding='cp1252')

        df.columns = [str(c).strip() for c in df.columns]
        def normalize(s):
            return "".join(filter(str.isalnum, s.lower()))

        cols_norm = {normalize(c): c for c in df.columns}

        total_rows = len(df)
        if end_idx is None:
            end_idx = total_rows

        df_slice = df.iloc[start_idx:end_idx]
        columns_order = [
            'track_name', 'artist_name', 'spotify_id', 'target',
            'deezer_id', 'deezer_isrc', 'bpm', 'rank', 'gain', 'deezer_genre',
            'deezer_explicit', 'deezer_preview', 'deezer_artist_fans', 'status_dz',
            'itunes_genre', 'itunes_release_date', 'itunes_track_view_url', 'itunes_preview_url',
            'itunes_artwork', 'itunes_explicit', 'itunes_duration_ms', 'itunes_country',
            'itunes_collection_name', 'itunes_artist_id', 'itunes_artist_view_url',
            'lastfm_tags', 'lyrics', 'aggregated_genre'
        ]
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if not os.path.exists(output_path):
            pd.DataFrame(columns=columns_order).to_csv(output_path, index=False)
            print(f"Created new output file with headers: {output_path}")

        for idx, row in df_slice.iterrows():
            def get_val(possible_names):
                for name in possible_names:
                    norm = normalize(name)
                    if norm in cols_norm:
                        v = row[cols_norm[norm]]
                        if pd.notna(v): return str(v).strip()
                return ""

            t = get_val(['Track name', 'track_name', 'track', 'title'])
            a = get_val(['Artist name', 'artist_name', 'artist'])
            sid = get_val(['Spotify - id', 'spotify_id', 'id'])
            target = get_val(['target', 'label'])

            if not t or not a or t.lower() in ['nan', 'none'] or a.lower() in ['nan', 'none']:
                if idx < start_idx + 5:
                    print(f"\n[{idx + 1}/{total_rows}] Debug Details: t='{t}', a='{a}', sid='{sid}'")
                    print(f"  Available columns in row: {list(row.index)}")
                print(f"\n[{idx + 1}/{total_rows}] Skipping: Missing track name or artist.")
                continue

            print(f"\n[{idx + 1}/{total_rows}] {t} - {a}")

            item_data = {
                'track_name': t,
                'artist_name': a,
                'spotify_id': sid,
                'isrc': get_val(['isrc']),
                'album_name': get_val(['album_name', 'album']),
                'track_number': get_val(['track_number']),
                'release_year': get_val(['release_year', 'year']),
                'genres': get_val(['genres']),
                'target': target
            }

            print("  > Deezer: Fetching BPM & Track Metadata...")
            dz_info = self.get_deezer_info(t, a)
            item_data.update(dz_info)

            print("  > iTunes: Fetching official genre & year...")
            it_info = self.get_itunes_info(t, a)
            item_data.update(it_info)

            if self.network:
                print("  > Last.fm: Fetching tags & stats...")
                lf_info = self.get_lastfm_tags(t, a)
                item_data.update(lf_info)

            print("  > Genius: Fetching lyrics...")
            item_data['lyrics'] = self.get_lyrics(t, a)

            it_gen = item_data.get('itunes_genre', '')
            dz_gen = item_data.get('deezer_genre', '')
            sp_gen = item_data.get('genres', '')
            lf_tags = item_data.get('lastfm_tags', '')

            all_gen_sources = [it_gen, dz_gen, sp_gen]
            item_data['aggregated_genre'] = ", ".join(filter(None, all_gen_sources))

            if not item_data['aggregated_genre'].strip() and lf_tags:
                item_data['aggregated_genre'] = lf_tags

            row_df = pd.DataFrame([item_data])
            for col in columns_order:
                if col not in row_df.columns:
                    row_df[col] = None

            row_df[columns_order].to_csv(output_path, mode='a', header=False, index=False)
            time.sleep(1.2)


input_file = 'data/raw/manual_tracks_full_tagged_dedup_1.csv'

MusicDataCollector().process_csv(
    input_file,
    'data/processed/collected_data_1.csv',
    start_idx=0,
    end_idx=350
)