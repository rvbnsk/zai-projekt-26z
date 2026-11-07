# zai-projekt-26z

Aplikacja do zbierania i prezentacji pomiarów temperatury z czujników IoT (projekt ZAI 26Z).

- `backend/` – REST API w FastAPI (Python 3.11) z bazą PostgreSQL; schemat bazy w `backend/schema.sql`.
- `generator/` – emulator czujnika wysyłający wyniki do API.

## Uruchomienie lokalne

Wymagane: Python 3.11, Docker.

```bash
docker compose up -d                      # PostgreSQL 16 na porcie 5432
cd backend
python -m venv .venv
.venv/Scripts/activate                    # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                      # ustaw ADMIN_PASSWORD
uvicorn app.main:app --env-file .env --port 8000
```

Przy starcie aplikacja tworzy tabele (`schema.sql`) i konto administratora z `ADMIN_USERNAME`/`ADMIN_PASSWORD`.
Dokumentacja API: http://localhost:8000/docs

## Generator danych

Skrypt korzysta tylko z biblioteki standardowej Pythona.

```bash
python generator/generator.py --api http://localhost:8000 --key <KLUCZ_CZUJNIKA> --count 48 --interval 3600
python generator/generator.py --api http://localhost:8000 --key <KLUCZ_CZUJNIKA> --live --interval 10
```

| Parametr | Opis | Domyślnie |
| --- | --- | --- |
| `--api` | adres API (lub zmienna `ZAI_API_URL`) | – |
| `--key` | klucz API czujnika (lub zmienna `ZAI_API_KEY`) | – |
| `--count` | liczba wyników; w trybie `--live` 0 = do przerwania | 24 |
| `--interval` | odstęp między wynikami w sekundach | 3600 |
| `--mode` | `random` (losowo z przedziału) lub `sine` (sinusoida) | `sine` |
| `--min`, `--max` | przedział generowanych wartości | 15, 25 |
| `--period` | liczba wyników na pełny okres sinusoidy | 24 |
| `--live` | wysyłanie bieżących wyników co `--interval` s zamiast wyników z przeszłości | – |

Bez `--live` generator wysyła `--count` wyników ze znacznikami czasu z przeszłości, ostatni z bieżącym czasem.
Odrzucone wyniki są wypisywane jako `REJECTED` z powodem odrzucenia.

## Wdrożenie

Aplikacja jest wdrażana na Render (plan darmowy) z pliku `render.yaml`: usługa `zai-api` i baza PostgreSQL `zai-db`.
Darmowy plan usypia aplikację po 15 minutach bezczynności; pierwsze żądanie po uśpieniu trwa ok. 1 minuty.
