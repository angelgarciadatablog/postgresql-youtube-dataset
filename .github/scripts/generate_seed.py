#!/usr/bin/env python3
"""
generate_seed.py
Consulta BigQuery y genera:
  - csv/<tabla>.csv  para cada tabla del schema
  - seed.sql         DDL + DML con CREATE TABLE IF NOT EXISTS e INSERT ON CONFLICT
"""

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import bigquery
from google.oauth2 import service_account

# ── Configuración ─────────────────────────────────────────────────────────────

PROJECT = "youtube-datasets-360"
DATASET = "angelgarciadatablog"
OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent  # raíz del repo
CSV_DIR = OUTPUT_DIR / "csv"

# ── Tablas: orden respeta dependencias FK ─────────────────────────────────────

TABLES = [
    {
        "bq":       "channels_static",
        "pg":       "channels",
        "columns":  ["channel_id", "channel_title", "country", "published_at",
                     "description", "thumbnail_url", "channel_url"],
        "pk":       ["channel_id"],
        "conflict": "update",
        "order_by": "published_at DESC",
    },
    {
        "bq":       "channels_snapshot",
        "pg":       "channel_metrics",
        "columns":  ["channel_id", "snapshot_date", "subscriber_count",
                     "view_count", "video_count"],
        "pk":       ["channel_id", "snapshot_date"],
        "conflict": "nothing",
        "order_by": "snapshot_date DESC",
    },
    {
        "bq":       "videos_static",
        "pg":       "videos",
        "columns":  ["video_id", "channel_id", "title", "published_at",
                     "duration_seconds", "description", "thumbnail_url", "video_url"],
        "pk":       ["video_id"],
        "conflict": "update",
        "order_by": "published_at DESC",
    },
    {
        "bq":       "videos_snapshot",
        "pg":       "video_metrics",
        "columns":  ["video_id", "snapshot_date", "view_count",
                     "like_count", "comment_count"],
        "pk":       ["video_id", "snapshot_date"],
        "conflict": "nothing",
        "order_by": "snapshot_date DESC, video_id",
    },
    {
        "bq":       "playlists_manual_static",
        "pg":       "playlists",
        "columns":  ["playlist_id", "channel_id", "title", "published_at",
                     "description", "privacy_status", "thumbnail_url", "playlist_url"],
        "pk":       ["playlist_id"],
        "conflict": "update",
        "order_by": "published_at DESC",
    },
    {
        "bq":       "playlist_items_manual_static",
        "pg":       "playlist_videos",
        "columns":  ["playlist_id", "video_id", "position", "added_at"],
        "pk":       ["playlist_id", "video_id"],
        "conflict": "update",
        "order_by": "playlist_id, position",
    },
    {
        "bq":       "playlist_items_snapshot",
        "pg":       "playlist_videos_history",
        "columns":  ["playlist_id", "video_id", "snapshot_date", "position", "added_at"],
        "pk":       ["playlist_id", "video_id", "snapshot_date"],
        "conflict": "nothing",
        "order_by": "snapshot_date DESC, playlist_id, position",
    },
]

# ── DDL (orden: primero sin FK, luego dependientes) ───────────────────────────

DDL = """\
-- channels (raíz del schema, sin FK)
CREATE TABLE IF NOT EXISTS channels (
  channel_id    TEXT PRIMARY KEY,
  channel_title TEXT NOT NULL,
  country       TEXT,
  published_at  TIMESTAMP NOT NULL,
  description   TEXT,
  thumbnail_url TEXT,
  channel_url   TEXT
);

-- videos (FK → channels)
CREATE TABLE IF NOT EXISTS videos (
  video_id         TEXT PRIMARY KEY,
  channel_id       TEXT NOT NULL REFERENCES channels(channel_id),
  title            TEXT NOT NULL,
  published_at     TIMESTAMP NOT NULL,
  duration_seconds INTEGER,
  description      TEXT,
  thumbnail_url    TEXT,
  video_url        TEXT
);

-- video_metrics (FK → videos)
CREATE TABLE IF NOT EXISTS video_metrics (
  video_id      TEXT NOT NULL REFERENCES videos(video_id),
  snapshot_date DATE NOT NULL,
  view_count    INTEGER,
  like_count    INTEGER,
  comment_count INTEGER,
  PRIMARY KEY (video_id, snapshot_date)
);

-- channel_metrics (FK → channels)
CREATE TABLE IF NOT EXISTS channel_metrics (
  channel_id       TEXT NOT NULL REFERENCES channels(channel_id),
  snapshot_date    DATE NOT NULL,
  subscriber_count INTEGER,
  view_count       INTEGER,
  video_count      INTEGER,
  PRIMARY KEY (channel_id, snapshot_date)
);

-- playlists (FK → channels)
CREATE TABLE IF NOT EXISTS playlists (
  playlist_id    TEXT PRIMARY KEY,
  channel_id     TEXT NOT NULL REFERENCES channels(channel_id),
  title          TEXT NOT NULL,
  published_at   TIMESTAMP NOT NULL,
  description    TEXT,
  privacy_status TEXT,
  thumbnail_url  TEXT,
  playlist_url   TEXT
);

-- playlist_videos (FK → playlists, videos)
CREATE TABLE IF NOT EXISTS playlist_videos (
  playlist_id TEXT      NOT NULL REFERENCES playlists(playlist_id),
  video_id    TEXT      NOT NULL REFERENCES videos(video_id),
  position    INTEGER   NOT NULL,
  added_at    TIMESTAMP,
  PRIMARY KEY (playlist_id, video_id)
);

-- playlist_videos_history (FK → playlists, videos)
CREATE TABLE IF NOT EXISTS playlist_videos_history (
  playlist_id   TEXT      NOT NULL REFERENCES playlists(playlist_id),
  video_id      TEXT      NOT NULL REFERENCES videos(video_id),
  snapshot_date DATE      NOT NULL,
  position      INTEGER   NOT NULL,
  added_at      TIMESTAMP,
  PRIMARY KEY (playlist_id, video_id, snapshot_date)
);"""


# ── Autenticación ─────────────────────────────────────────────────────────────

def get_client():
    sa_key = os.environ.get("GCP_SA_KEY")
    if sa_key:
        info = json.loads(sa_key)
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/bigquery"]
        )
        return bigquery.Client(project=PROJECT, credentials=creds)
    return bigquery.Client(project=PROJECT)


# ── Generación ────────────────────────────────────────────────────────────────

def escape_value(val):
    if val is None:
        return "NULL"
    if isinstance(val, (int, float)):
        return str(val)
    return "'" + str(val).replace("'", "''") + "'"


def query_table(client, table):
    cols = ", ".join(table["columns"])
    sql = f"SELECT {cols} FROM `{PROJECT}.{DATASET}.{table['bq']}` ORDER BY {table['order_by']}"
    return [dict(row) for row in client.query(sql).result()]


def write_csv(rows, table):
    CSV_DIR.mkdir(exist_ok=True)
    path = CSV_DIR / f"{table['pg']}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=table["columns"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"  CSV → {path.name} ({len(rows)} filas)")


def generate_inserts(rows, table):
    if not rows:
        return f"-- {table['pg']}: sin filas"

    pg      = table["pg"]
    cols    = table["columns"]
    pk      = table["pk"]
    lines   = [f"-- {pg}"]

    for row in rows:
        vals     = ", ".join(escape_value(row[c]) for c in cols)
        col_list = ", ".join(cols)
        stmt     = f"INSERT INTO {pg} ({col_list}) VALUES ({vals})"

        if table["conflict"] == "nothing":
            stmt += f"\n  ON CONFLICT ({', '.join(pk)}) DO NOTHING"
        else:
            update_cols = [c for c in cols if c not in pk]
            set_clause  = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
            stmt += f"\n  ON CONFLICT ({', '.join(pk)}) DO UPDATE SET {set_clause}"

        lines.append(stmt + ";")

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Conectando a BigQuery...")
    client = get_client()

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    seed_parts = [
        f"-- seed.sql — generado automáticamente el {timestamp}",
        "-- No editar manualmente: este archivo se sobreescribe cada semana.",
        "",
        DDL,
    ]

    for table in TABLES:
        print(f"\n{table['bq']} → {table['pg']}")
        rows = query_table(client, table)
        print(f"  {len(rows)} filas")
        write_csv(rows, table)
        seed_parts.append(generate_inserts(rows, table))

    seed_path = OUTPUT_DIR / "seed.sql"
    seed_path.write_text("\n\n".join(seed_parts), encoding="utf-8")
    print(f"\nseed.sql generado ({seed_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
