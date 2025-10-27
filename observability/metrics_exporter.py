"""
Prometheus metrics exporter for log pipeline services
"""
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time

# Metrics definitions
logs_ingested_total = Counter(
    'logs_ingested_total',
    'Total number of logs ingested',
    ['service', 'level']
)

logs_indexed_total = Counter(
    'logs_indexed_total',
    'Total number of logs indexed to ClickHouse',
    ['service']
)

query_duration_seconds = Histogram(
    'query_duration_seconds',
    'Query duration in seconds',
    ['endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

kafka_consumer_lag = Gauge(
    'kafka_consumer_lag',
    'Kafka consumer lag',
    ['topic', 'partition', 'group']
)

clickhouse_disk_usage_bytes = Gauge(
    'clickhouse_disk_usage_bytes',
    'ClickHouse disk usage in bytes',
    ['database', 'table']
)

log_errors_total = Counter(
    'log_errors_total',
    'Total number of errors in log pipeline',
    ['component', 'error_type']
)


def start_metrics_server(port=8080):
    """Start Prometheus metrics HTTP server"""
    start_http_server(port)
    print(f'Metrics server started on port {port}')


if __name__ == '__main__':
    start_metrics_server()
    # Keep the server running
    while True:
        time.sleep(1)
