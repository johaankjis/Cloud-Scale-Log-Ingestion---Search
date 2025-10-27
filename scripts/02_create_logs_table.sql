-- Create main logs table with optimized schema for time-series data
CREATE TABLE IF NOT EXISTS logs.logs
(
    timestamp DateTime64(3) CODEC(Delta, ZSTD),
    service LowCardinality(String),
    level LowCardinality(String),
    message String CODEC(ZSTD),
    metadata String CODEC(ZSTD),
    date Date DEFAULT toDate(timestamp)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (service, level, timestamp)
TTL timestamp + INTERVAL 30 DAY
SETTINGS index_granularity = 8192;

-- Create indexes for faster queries
ALTER TABLE logs.logs ADD INDEX idx_message message TYPE tokenbf_v1(32768, 3, 0) GRANULARITY 4;
