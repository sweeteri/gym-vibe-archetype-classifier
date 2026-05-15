import pandas as pd


def deduplicate_dataset(input_path='data/processed/collected_data_1.csv',
                        output_path='data/processed/collected_data_clean_1.csv'):
    df = pd.read_csv(input_path)
    initial_count = len(df)

    df['tmp_track'] = df['track_name'].astype(str).str.lower().str.strip()
    df['tmp_artist'] = df['artist_name'].astype(str).str.lower().str.strip()

    conflicts = df.groupby(['tmp_track', 'tmp_artist'])['target'].nunique()
    tracks_with_conflicts = conflicts[conflicts > 1].count()

    print(f"Всего строк в файле: {initial_count}")
    print(f"Найдено треков с противоречивыми таргетами: {tracks_with_conflicts}")

    def get_best_target(group):
        return group.value_counts().index[0]

    correct_targets = df.groupby(['tmp_track', 'tmp_artist'])['target'].apply(get_best_target).reset_index()
    correct_targets.columns = ['tmp_track', 'tmp_artist', 'new_target']

    df_unique = df.drop_duplicates(subset=['tmp_track', 'tmp_artist'], keep='first').copy()

    df_unique = df_unique.merge(correct_targets, on=['tmp_track', 'tmp_artist'], how='left')
    df_unique['target'] = df_unique['new_target']

    df_unique = df_unique.drop(columns=['tmp_track', 'tmp_artist', 'new_target'])

    df_unique.to_csv(output_path, index=False)

    final_count = len(df_unique)
    print(f"Дедупликация завершена!")
    print(f"Удалено строк: {initial_count - final_count}")
    print(f"Осталось уникальных треков: {final_count}")
    print(f"Файл сохранен в: {output_path}")


if __name__ == "__main__":
    deduplicate_dataset('data/processed/collected_data_1.csv', 'data/processed/collected_data_fixed_1.csv')