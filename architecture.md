app/
  bot/
    handlers.py          # telegram handlers (/top,/me,/rules, video_note, reactions)
    scheduler.py         # periodic rating publisher
    formatting.py        # rating text + zero-ping text (HTML)
  core/
    config.py            # constants/env parsing
    scoring.py           # pure domain rules: apply_circle/apply_reaction_delta
    models.py            # DTOs (UserStats, TopRow, etc.)
  storage/
    repo.py              # Repository interfaces (DAO)
    sqlite_repo.py       # SQLite implementation
    pg_repo.py           # PostgreSQL implementation (later)
    migrations.sql       # schema
  main.py                # wiring: config + repo + bot + scheduler