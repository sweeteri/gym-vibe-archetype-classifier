import pandas as pd
import numpy as np
import os
from sklearn.preprocessing import MinMaxScaler
import re


class MusicFeatureEngineer:
    def __init__(self, input_path='data/processed/collected_data.csv', output_path='data/processed/featured_data.csv'):
        self.input_path = input_path
        self.output_path = output_path

    def clean_lyrics(self, text):
        if not isinstance(text, str):
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
            print(f"--- Limiting engineering to first {limit} tracks ---")

        print(f"--- Engineering Features for {len(df)} tracks ---")

        for col in ['bpm', 'popularity', 'rank', 'gain']:
            if col in df.columns:
                if col == 'bpm':
                    df[col] = df[col].replace(0, np.nan)
                    df[col] = df[col].fillna(df[col].median() if not df[col].isna().all() else 120)
                elif col == 'gain':
                    df[col] = df[col].fillna(-10.0)
                else:
                    df[col] = df[col].fillna(df[col].mean() if not df[col].isna().all() else 0)

        if 'lyrics' in df.columns:
            print("  > Cleaning lyrics...")
            df['clean_lyrics'] = df['lyrics'].apply(self.clean_lyrics)
            df['lyrics_word_count'] = df['clean_lyrics'].apply(lambda x: len(x.split()))
        else:
            df['clean_lyrics'] = ""
            df['lyrics_word_count'] = 0

        scaler = MinMaxScaler()
        metrics_to_scale = ['bpm', 'popularity', 'rank', 'gain', 'lyrics_word_count', 'lastfm_playcount',
                            'lastfm_listeners']
        num_cols = [c for c in metrics_to_scale if c in df.columns]

        if num_cols:
            for col in num_cols:
                df[col] = df[col].fillna(0)

            scaled_features = scaler.fit_transform(df[num_cols])
            scaled_df = pd.DataFrame(scaled_features, columns=[f'scaled_{c}' for c in num_cols])
            df = pd.concat([df, scaled_df], axis=1)

        def detect_vibe(row):
            agg_genre = str(row.get('aggregated_genre', '')).lower()
            lf_tags = str(row.get('lastfm_tags', '')).lower()
            combined = f"{agg_genre} {lf_tags}"

            if any(word in combined for word in ['energetic', 'dance', 'pop', 'upbeat', 'high energy']):
                return 'high_energy'
            if any(word in combined for word in ['chill', 'acoustic', 'slow', 'sad', 'relax', 'ambient']):
                return 'chill'
            if any(word in combined for word in ['rock', 'metal', 'hard', 'drums', 'electric']):
                return 'aggressive'
            return 'neutral'

        df['inferred_vibe'] = df.apply(detect_vibe, axis=1)


        vital_columns = ['spotify_id', 'track_name', 'artist_name', 'lastfm_tags', 'aggregated_genre', 'lyrics',
                         'inferred_vibe', 'target']
        cols_to_drop = [c for c in df.columns if df[c].replace('', np.nan).isna().all() and c not in vital_columns]
        df = df.drop(columns=cols_to_drop)

        df.to_csv(self.output_path, index=False)
        print(f"✅ Feature engineering complete! Saved to {self.output_path}")
        return df


if __name__ == "__main__":
    MusicFeatureEngineer().engineer_features(limit=5)
