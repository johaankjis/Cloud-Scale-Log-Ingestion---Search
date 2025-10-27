"""
Mock data generator for testing the ingestion pipeline
Generates realistic log entries at configurable rates
"""
import asyncio
import json
import random
from datetime import datetime
from confluent_kafka import Producer
import os

KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'logs-ingestion')

# Mock services
SERVICES = [
    'api-gateway', 'auth-service', 'user-service', 
    'payment-service', 'notification-service', 'analytics-service'
]

# Log levels
LOG_LEVELS = ['DEBUG', 'INFO', 'WARN', 'ERROR']

# Sample log messages
LOG_MESSAGES = {
    'DEBUG': [
        'Processing request',
        'Cache hit for key',
        'Database query executed',
        'Function called with parameters'
    ],
    'INFO': [
        'User logged in successfully',
        'Request completed in {}ms',
        'New record created',
        'Configuration loaded'
    ],
    'WARN': [
        'High memory usage detected',
        'Slow query detected: {}ms',
        'Rate limit approaching',
        'Deprecated API endpoint called'
    ],
    'ERROR': [
        'Database connection failed',
        'Authentication failed for user',
        'Timeout waiting for response',
        'Invalid request payload'
    ]
}


def generate_log_entry():
    """Generate a random log entry"""
    service = random.choice(SERVICES)
    level = random.choices(
        LOG_LEVELS, 
        weights=[30, 50, 15, 5]  # More INFO, fewer ERRORs
    )[0]
    
    message_template = random.choice(LOG_MESSAGES[level])
    if '{}' in message_template:
        message = message_template.format(random.randint(10, 5000))
    else:
        message = message_template
    
    metadata = {
        'request_id': f'req-{random.randint(100000, 999999)}',
        'user_id': f'user-{random.randint(1, 10000)}',
        'ip_address': f'{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}',
        'endpoint': f'/api/v1/{random.choice(["users", "orders", "products", "analytics"])}'
    }
    
    return {
        'timestamp': datetime.utcnow().isoformat(),
        'service': service,
        'level': level,
        'message': message,
        'metadata': metadata
    }


async def generate_logs(rate_per_second=1000, duration_seconds=3600):
    """
    Generate logs at specified rate
    
    Args:
        rate_per_second: Target logs per second (default 1000)
        duration_seconds: How long to generate logs (default 1 hour)
    """
    producer_config = {
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'client.id': 'mock-data-generator',
        'enable.idempotence': True,
        'acks': 'all',
        'compression.type': 'lz4',
        'linger.ms': 10,
        'batch.size': 32768,
    }
    
    producer = Producer(producer_config)
    
    print(f'Starting log generation: {rate_per_second} logs/sec for {duration_seconds}s')
    
    batch_size = 100
    delay = batch_size / rate_per_second
    
    start_time = asyncio.get_event_loop().time()
    total_sent = 0
    
    try:
        while (asyncio.get_event_loop().time() - start_time) < duration_seconds:
            batch_start = asyncio.get_event_loop().time()
            
            # Generate and send batch
            for _ in range(batch_size):
                log_entry = generate_log_entry()
                key = log_entry['service'].encode('utf-8')
                value = json.dumps(log_entry).encode('utf-8')
                
                producer.produce(
                    KAFKA_TOPIC,
                    key=key,
                    value=value
                )
                total_sent += 1
            
            producer.poll(0)
            
            # Calculate sleep time to maintain rate
            elapsed = asyncio.get_event_loop().time() - batch_start
            sleep_time = max(0, delay - elapsed)
            await asyncio.sleep(sleep_time)
            
            # Print stats every 10 seconds
            if total_sent % (rate_per_second * 10) == 0:
                elapsed_total = asyncio.get_event_loop().time() - start_time
                actual_rate = total_sent / elapsed_total
                print(f'Sent {total_sent} logs | Rate: {actual_rate:.0f} logs/sec')
    
    finally:
        producer.flush()
        print(f'Generation complete. Total logs sent: {total_sent}')


if __name__ == '__main__':
    # Generate 10K logs/sec for 1 hour (MVP target)
    asyncio.run(generate_logs(rate_per_second=10000, duration_seconds=3600))
