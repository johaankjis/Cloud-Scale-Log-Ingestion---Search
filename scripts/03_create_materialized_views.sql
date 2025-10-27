-- Materialized view for aggregated metrics by service and level
CREATE MATERIALIZED VIEW IF NOT EXISTS logs.logs_by_service_level
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (service, level, toStartOfHour(timestamp))
AS
SELECT
    service,
    level,
    toStartOfHour(timestamp) as hour,
    count() as log_count
FROM logs.logs
GROUP BY service, level, hour;

-- Materialized view for error tracking
CREATE MATERIALIZED VIEW IF NOT EXISTS logs.error_logs
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, service)
AS
SELECT
    timestamp,
    service,
    message,
    metadata
FROM logs.logs
WHERE level = 'ERROR';
