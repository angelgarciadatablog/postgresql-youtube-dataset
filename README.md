# postgresql-youtube-dataset

Datos reales del canal [angelgarciadatablog](https://www.youtube.com/@angelgarciadatablog) para practicar PostgreSQL. Actualizado automáticamente cada semana.

## Qué contiene este repo

| Archivo / Carpeta | Para qué sirve |
|---|---|
| `csv/` | Ver los datos sin instalar nada — ábrelos en Excel o Google Sheets |
| `seed.sql` | Crear y poblar la base de datos en tu PostgreSQL local con un solo comando |

## Opción 1 — Ver los datos en CSV

Si aún no tienes PostgreSQL instalado, puedes explorar los datos directamente abriendo cualquier archivo de la carpeta `csv/` en Excel, Google Sheets o el editor que prefieras.

| Archivo | Qué contiene |
|---|---|
| `channels.csv` | Información del canal |
| `channel_metrics.csv` | Métricas del canal semana a semana |
| `videos.csv` | Información de cada video |
| `video_metrics.csv` | Métricas de cada video semana a semana |
| `playlists.csv` | Información de cada playlist |
| `playlist_videos.csv` | Relación actual entre videos y playlists |
| `playlist_videos_history.csv` | Historial de la relación videos ↔ playlists |

## Opción 2 — Cargar los datos en PostgreSQL

### Requisitos

- PostgreSQL instalado y corriendo
- Terminal con acceso a `psql`

### Pasos

**1. Clona el repo:**
```bash
git clone https://github.com/angelgarciadatablog/postgresql-youtube-dataset.git
cd postgresql-youtube-dataset
```

**2. Crea la base de datos:**
```bash
psql postgres -c "CREATE DATABASE youtube_analytics;"
```

**3. Ejecuta el seed:**
```bash
psql -d youtube_analytics -f seed.sql
```

**4. Verifica que las tablas se crearon:**
```bash
psql -d youtube_analytics -c "\dt"
```

Deberías ver 7 tablas listas para consultar.

### Actualizar los datos

Cuando el repo tenga datos más recientes, actualiza tu base de datos con los mismos comandos:

```bash
git pull
psql -d youtube_analytics -f seed.sql
```

El seed es seguro de re-ejecutar — no borra datos existentes, solo agrega los nuevos y actualiza los que cambiaron.

## Schema

```
channels ──────────────────────────────────────────┐
   │                                                │
   ├──► videos ──────────────────────────────────┐  │
   │       │                                     │  │
   │       └──► video_metrics                   │  │
   │                                             │  │
   └──► channel_metrics                          │  │
                                                 │  │
playlists ◄──────────────────────────────────────┘  │
   │         (FK → channels) ◄──────────────────────┘
   │
   ├──► playlist_videos
   └──► playlist_videos_history
```

## Datos actualizados

Los archivos de este repo se actualizan automáticamente cada semana con los datos más recientes del canal. Haz `git pull` para obtener la última versión.
