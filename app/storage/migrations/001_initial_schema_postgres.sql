-- Initial schema for PostgreSQL

CREATE TABLE IF NOT EXISTS users (
  chat_id       BIGINT NOT NULL,
  user_id       BIGINT NOT NULL,
  username      TEXT,
  display_name  TEXT NOT NULL,
  circles       INT NOT NULL DEFAULT 0,
  reactions     INT NOT NULL DEFAULT 0,
  points        INT NOT NULL DEFAULT 0,
  PRIMARY KEY (chat_id, user_id)
);

CREATE TABLE IF NOT EXISTS circle_messages (
  chat_id        BIGINT NOT NULL,
  message_id     BIGINT NOT NULL,
  author_id      BIGINT NOT NULL,
  created_at_ts  BIGINT NOT NULL,
  PRIMARY KEY (chat_id, message_id)
);

CREATE TABLE IF NOT EXISTS reactions_log (
  chat_id     BIGINT NOT NULL,
  message_id  BIGINT NOT NULL,
  reactor_id  BIGINT NOT NULL,
  emoji       TEXT NOT NULL,
  PRIMARY KEY (chat_id, message_id, reactor_id, emoji)
);

CREATE TABLE IF NOT EXISTS chat_state (
  chat_id           BIGINT NOT NULL PRIMARY KEY,
  last_circle_ts    BIGINT NOT NULL DEFAULT 0,
  last_rating_ts    BIGINT NOT NULL DEFAULT 0,
  ratings_enabled   BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_circle_messages_chat_ts
  ON circle_messages(chat_id, created_at_ts);

CREATE INDEX IF NOT EXISTS idx_users_chat_points
  ON users(chat_id, points DESC);
