app/
  bot/
    handlers.py          # telegram handlers (/top,/me,/rules, video_note, reactions)
    scheduler.py         # periodic rating publisher
    formatting.py        # rating text + zero-ping text (HTML)
    messages.py          # message templates and localization
    media_assets.py      # media asset constants and path helpers
    media_send.py        # telegram media sending utilities
    assets/              # image assets for bot messages
  core/
    config.py            # constants/env parsing
    scoring.py           # pure domain rules: apply_circle/apply_reaction_delta
    models.py            # DTOs (UserStats, TopRow, etc.)
  storage/
    repo.py              # Repository interfaces (DAO)
    sqlite_repo.py       # SQLite implementation
    pg_repo.py           # PostgreSQL implementation
    migrations.py        # migration runner and utilities
    PRODUCTION_MIGRATION_SETUP.md  # production migration setup guide
    migrations/          # migration SQL files
      00*_migration_name.sql
  main.py                # wiring: config + repo + bot + scheduler