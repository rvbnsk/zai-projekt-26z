-- Database schema, applied on application startup.

CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash CHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS series (
    id        SERIAL PRIMARY KEY,
    name      VARCHAR(100) NOT NULL,
    min_value DOUBLE PRECISION NOT NULL,
    max_value DOUBLE PRECISION NOT NULL,
    color     CHAR(7) NOT NULL,
    icon      VARCHAR(50),
    unit      VARCHAR(20),
    CHECK (min_value < max_value)
);

CREATE TABLE IF NOT EXISTS sensors (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    series_id    INTEGER NOT NULL REFERENCES series(id) ON DELETE CASCADE,
    api_key_hash CHAR(64) NOT NULL UNIQUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS measurements (
    id        BIGSERIAL PRIMARY KEY,
    series_id INTEGER NOT NULL REFERENCES series(id) ON DELETE CASCADE,
    sensor_id INTEGER REFERENCES sensors(id) ON DELETE SET NULL,
    value     DOUBLE PRECISION NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_measurements_series_timestamp ON measurements (series_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_measurements_timestamp ON measurements (timestamp);
