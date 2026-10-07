# Todo app

Flask to-do list with per-user login and SQLite.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `SECRET_KEY` in `.env` to a long random string. Never commit `.env` or `*.db` files.

## Run

```bash
python app.py
```

Open http://127.0.0.1:5000 — register, then add, complete, and delete your own tasks.

## Test

```bash
pytest
```
