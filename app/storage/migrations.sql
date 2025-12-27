PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  chat_id       INTEGER NOT NULL,
  user_id       INTEGER NOT NULL,
  username      TEXT,
  display_name  TEXT NOT NULL,
  circles       INTEGER NOT NULL DEFAULT 0,
  reactions     INTEGER NOT NULL DEFAULT 0,
  points        INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (chat_id, user_id)
);

CREATE TABLE IF NOT EXISTS circle_messages (
  chat_id        INTEGER NOT NULL,
  message_id     INTEGER NOT NULL,
  author_id      INTEGER NOT NULL,
  created_at_ts  INTEGER NOT NULL,
  PRIMARY KEY (chat_id, message_id)
);

CREATE TABLE IF NOT EXISTS reactions_log (
  chat_id     INTEGER NOT NULL,
  message_id  INTEGER NOT NULL,
  reactor_id  INTEGER NOT NULL,
  emoji       TEXT NOT NULL,
  PRIMARY KEY (chat_id, message_id, reactor_id, emoji)
);

CREATE TABLE IF NOT EXISTS chat_state (
  chat_id         INTEGER NOT NULL PRIMARY KEY,
  last_circle_ts  INTEGER NOT NULL DEFAULT 0,
  last_rating_ts  INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_circle_messages_chat_ts
  ON circle_messages(chat_id, created_at_ts);

CREATE INDEX IF NOT EXISTS idx_users_chat_points
  ON users(chat_id, points DESC);
