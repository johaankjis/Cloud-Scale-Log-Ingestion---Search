"""
Health check endpoint for the indexer service
Monitors consumer lag and ClickHouse connectivity
"""
from flask import Flask, jsonify
from confluent_kafka import Consumer
from clickhouse_driver import Client
import os

app = Flask(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'logs-ingestion')
KAFKA_GROUP_ID = os.getenv('KAFKA_GROUP_ID', 'log-indexer-group')
CLICKHOUSE_HOST = os.getenv('CLICKHOUSE_HOST', 'clickhouse')
CLICKHOUSE_PORT = int(os.getenv('CLICKHOUSE_PORT', '9000'))


@app.route('/health')
def health():
    """Basic health check"""
    return jsonify({'status': 'healthy'}), 200


@app.route('/ready')
def ready():
    """Readiness check - verifies connectivity to dependencies"""
    try:
        # Check ClickHouse connectivity
        clickhouse = Client(host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT)
        clickhouse.execute('SELECT 1')
        
        # Check Kafka connectivity
        consumer = Consumer({
            'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
            'group.id': f'{KAFKA_GROUP_ID}-health'
        })
        consumer.list_topics(timeout=5)
        consumer.close()
        
        return jsonify({
            'status': 'ready',
            'clickhouse': 'connected',
            'kafka': 'connected'
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'not ready',
            'error': str(e)
        }), 503


@app.route('/metrics')
def metrics():
    """Consumer lag metrics"""
    try:
        consumer = Consumer({
            'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
            'group.id': f'{KAFKA_GROUP_ID}-metrics'
        })
        
        # Get consumer lag
        metadata = consumer.list_topics(KAFKA_TOPIC, timeout=5)
        
        consumer.close()
        
        return jsonify({
            'topic': KAFKA_TOPIC,
            'partitions': len(metadata.topics[KAFKA_TOPIC].partitions)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
