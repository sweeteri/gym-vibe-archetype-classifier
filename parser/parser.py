import os
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from lyricsgenius import Genius
import pylast
import requests
import time
from dotenv import load_dotenv

load_dotenv()


class MusicDataCollector:
    def __init__(self):
        client_id = os.getenv('SPOTIFY_CLIENT_ID')
        client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')

        if client_id and client_secret:
            self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret
            ))
        else:
            self.sp = None
            print("! Spotify Credentials missing. Metadata will be skipped.")

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
        if not self.sp: return None

        try:
            track_id = spotify_id
            if not track_id:
                query = f"track:{track_name} artist:{artist_name}"
                results = self.sp.search(q=query, limit=1, type='track')
                if not results['tracks']['items']:
                    return None
                track = results['tracks']['items'][0]
                track_id = track['id']
            else:
                track = self.sp.track(track_id)

            genres = []
            try:
                artist_id = track['artists'][0]['id']
                artist_info = self.sp.artist(artist_id)
                genres = artist_info.get('genres', [])
            except:
                pass

            data = {
                'spotify_id': track_id,
                'isrc': track.get('external_ids', {}).get('isrc'),
                'track_name': track.get('name'),
                'artist_name': track['artists'][0]['name'] if track.get('artists') else artist_name,
                'album_name': track.get('album', {}).get('name'),
                'track_number': track.get('track_number'),
                'release_year': (track.get('album', {}).get('release_date') or "0000")[:4],
                'popularity': track.get('popularity'),
                'genres': ", ".join(genres)
            }


            try:
                features_list = self.sp.audio_features([track_id])
                if features_list and features_list[0]:
                    f = features_list[0]
                    data.update({
                        'danceability': f.get('danceability'),
                        'energy': f.get('energy'),
                        'key': f.get('key'),
                        'loudness': f.get('loudness'),
                        'mode': f.get('mode'),
                        'speechiness': f.get('speechiness'),
                        'acousticness': f.get('acousticness'),
                        'instrumentalness': f.get('instrumentalness'),
                        'liveness': f.get('liveness'),
                        'valence': f.get('valence'),
                        'tempo': f.get('tempo'),
                    })
            except Exception as e:
                pass

            return data
        except Exception as e:
            print(f"  ! Spotify Error: {e}")
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
                    "itunes_track_view_url": item.get("trackViewUrl"),
                    "itunes_preview_url": item.get("previewUrl"),
                    "itunes_artwork": item.get("artworkUrl100"),
                    "itunes_explicit": item.get("trackExplicitness") == "explicit",
                    "itunes_duration_ms": item.get("trackTimeMillis"),
                    "itunes_country": item.get("country"),
                    "itunes_collection_name": item.get("collectionName"),  # Альбом
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
                "deezer_explicit": track_details.get("explicit_lyrics", False),
                "deezer_preview": track_details.get("preview"),
                "deezer_artist_fans": artist_fans,
                "status_dz": "ok"
            }
        except Exception as e:
            print(f"  ! Deezer error: {e}")
            return {"status_dz": "error"}

    def get_lyrics(self, track_name, artist_name):
        if not self.genius: return None
        try:
            song = self.genius.search_song(track_name, artist_name)
            if song:
                if artist_name.lower() in song.artist.lower() or song.artist.lower() in artist_name.lower():
                    return song.lyrics
            return None
        except Exception as e:
            print(f"  ! Genius error: {e}")
            return None

    def process_csv(self, input_path, output_path, limit=None):
        if not os.path.exists(input_path):
            print(f"Error: {input_path} not found.")
            return

        df = pd.read_csv(input_path)
        if limit:
            df = df.head(limit)
            print(f"--- Limiting processing to first {limit} tracks ---")

        collected_data = []

        print(f"--- Music Data Collection Starting ({len(df)} tracks) ---")

        for idx, row in df.iterrows():
            t = str(row.get('Track name', row.get('track_name', '')))
            a = str(row.get('Artist name', row.get('artist_name', row.get('artist', ''))))
            sid = row.get('Spotify - id', row.get('spotify_id', ''))
            target = row.get('target', '')

            print(f"\n[{idx + 1}/{len(df)}] {t} - {a}")

            item_data = self.get_spotify_data(t, a, sid) or {'track_name': t, 'artist_name': a, 'spotify_id': sid}

            item_data['target'] = target

            print("  > Deezer: Fetching BPM & Track Genre...")
            dz_info = self.get_deezer_info(t, a)
            item_data.update(dz_info)

            print("  > iTunes: Fetching official genre...")
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

            collected_data.append(item_data)
            time.sleep(1)

        output_df = pd.DataFrame(collected_data)

        vital_columns = ['spotify_id', 'track_name', 'artist_name', 'lastfm_tags', 'aggregated_genre', 'lyrics',
                         'target']
        for col in vital_columns:
            if col not in output_df.columns:
                output_df[col] = ""

        cols_to_drop = [c for c in output_df.columns if output_df[c].isna().all() and c not in vital_columns]
        output_df = output_df.drop(columns=cols_to_drop)

        output_df.to_csv(output_path, index=False)
        print(f"\nФайл: {output_path}")


if __name__ == "__main__":
    MusicDataCollector().process_csv('data/raw/manual_tracks_full_tagged.csv', 'data/processed/collected_data.csv', limit=5)
