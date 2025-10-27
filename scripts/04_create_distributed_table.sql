-- For multi-node ClickHouse clusters (optional for MVP)
-- Distributed table for querying across shards
CREATE TABLE IF NOT EXISTS logs.logs_distributed AS logs.logs
ENGINE = Distributed('logs_cluster', 'logs', 'logs', rand());
