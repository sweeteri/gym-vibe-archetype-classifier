import pandas as pd
import numpy as np
import os
import re
from sklearn.preprocessing import MinMaxScaler


class MusicFeatureEngineer:
    def __init__(self, input_path='data/processed/collected_data.csv', output_path='data/processed/featured_data.csv'):
        self.input_path = input_path
        self.output_path = output_path

    def clean_lyrics(self, text):
        if not isinstance(text, str) or text.strip() == "":
            return ""
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\d+Embed$', '', text.strip())
        text = text.replace('\n', ' ').strip()
        return text

    def engineer_features(self, limit=None):
        if not os.path.exists(self.input_path):
            print(f"Error: {self.input_path} not found.")
            return

        df = pd.read_csv(self.input_path)
        if limit:
            df = df.head(limit)

        print(f"--- Исходное количество колонок: {len(df.columns)} ---")

        trash_columns = [
            'spotify_id', 'deezer_id', 'deezer_isrc', 'status_dz', 'itunes_artist_id',
            'itunes_track_view_url', 'itunes_preview_url', 'itunes_artwork',
            'itunes_artist_view_url', 'deezer_preview', 'lastfm_tags'
        ]
        df = df.drop(columns=[c for c in trash_columns if c in df.columns])

        if 'itunes_genre' in df.columns and 'aggregated_genre' in df.columns:
            df['genre_final'] = df['aggregated_genre'].fillna(df['itunes_genre']).fillna('unknown')

        explicit_cols = ['deezer_explicit', 'itunes_explicit']
        df['is_explicit'] = 0
        for col in explicit_cols:
            if col in df.columns:
                df['is_explicit'] = df['is_explicit'] | df[col].fillna(False).astype(int)

        if 'lyrics' in df.columns:
            df['clean_lyrics'] = df['lyrics'].apply(self.clean_lyrics)
            df['lyrics_word_count'] = df['clean_lyrics'].apply(lambda x: len(x.split()))
        else:
            df['clean_lyrics'] = ""
            df['lyrics_word_count'] = 0

        numeric_map = {
            'bpm': 120,
            'rank': 0,
            'gain': -10,
            'deezer_artist_fans': 0,
            'itunes_duration_ms': 200000
        }

        for col, default in numeric_map.items():
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                fill_value = df[col].median() if df[col].notna().any() else default
                df[col] = df[col].fillna(fill_value)

        scaler = MinMaxScaler()
        cols_to_scale = ['bpm', 'rank', 'gain', 'lyrics_word_count', 'deezer_artist_fans']
        available_scale = [c for c in cols_to_scale if c in df.columns]

        if available_scale:
            scaled_data = scaler.fit_transform(df[available_scale])
            scaled_df = pd.DataFrame(scaled_data, columns=[f'scaled_{c}' for c in available_scale])
            df = pd.concat([df.reset_index(drop=True), scaled_df], axis=1)

        def detect_vibe(row):
            genre = str(row.get('genre_final', '')).lower()
            lyrics = str(row.get('clean_lyrics', '')).lower()
            combined = f"{genre} {lyrics}"

            if any(w in combined for w in ['chill', 'relax', 'slow', 'ambient', 'lofi']): return 'chill'
            if any(w in combined for w in ['hard', 'aggressive', 'metal', 'war', 'fight', 'power']): return 'aggressive'
            if any(w in combined for w in ['dance', 'club', 'pop', 'energy', 'party']): return 'high_energy'
            return 'neutral'

        df['inferred_vibe'] = df.apply(detect_vibe, axis=1)

        threshold = len(df) * 0.9
        df = df.dropna(axis=1, thresh=len(df) - threshold)

        cols_to_remove = ['itunes_genre', 'aggregated_genre', 'deezer_explicit', 'itunes_explicit', 'lyrics']
        df = df.drop(columns=[c for c in cols_to_remove if c in df.columns])

        for col in df.columns:
            if df[col].nunique() <= 1 and col != 'target':
                df = df.drop(columns=[col])

        df.to_csv(self.output_path, index=False)
        print(f"--- Обработка завершена. Осталось колонок: {len(df.columns)} ---")
        print(f"Колонки: {list(df.columns)}")
        return df


if __name__ == "__main__":
    os.makedirs('data/processed', exist_ok=True)
    engineer = MusicFeatureEngineer()
    engineer.engineer_features()