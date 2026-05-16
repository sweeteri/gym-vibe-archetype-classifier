# 🏋️‍♂️ Gym Vibe Archetype Classifier




- **Presentation**  [Google Slides](https://docs.google.com/presentation/d/1iQz_gjMijmNL2yL0e3zvU4rL4ZcK0bsss7hmb-Nhd5M/edit?usp=sharing) 
- **Report** [Google Docs](https://docs.google.com/document/d/1qoBpEmwiq9PdrQb10ckgwoqlCzx7nKVDYxRu1sbpDm8/edit?usp=sharing) 
- **Dataset** [Google Drive](https://drive.google.com/drive/folders/14Nn3nEBlxmtmNZu6czr9z19JB7bFLpwS?usp=sharing) 
---

## Project Overview

This project builds a machine learning classifier that categorizes songs into different **workout vibes** — from high-intensity battle cries to chill cooldown melodies.

---

## Project Structure
```
gym-vibe-archetype-classifier/
│
├── parser/
│ ├── parser.py # Fetches data from Spotify, Deezer, iTunes, Genius APIs
│ └── remove_duplicates.py # Removes duplicate songs
│
├── notebooks/
│ ├── baseline.ipynb # Baseline model
│ ├── features.ipynb # Feature engineering
│ └── normal_pipeline_calibrated.ipynb # Final calibrated pipeline
│
└── README.md
```
---
## Data Sources

- **Spotify API** 
- **Deezer API** 
- **iTunes API**
- **Genius API** 

---

## ML Pipeline

| Notebook | Description |
|----------|-------------|
| `baseline.ipynb` | Simple model to establish performance floor |
| `features.ipynb` | Feature extraction, selection, and transformation |
| `normal_pipeline_calibrated.ipynb` | Final production pipeline with probability calibration |

---
