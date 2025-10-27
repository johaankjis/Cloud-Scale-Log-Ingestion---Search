"""
Seed ClickHouse with sample data for testing
"""
from clickhouse_driver import Client
from datetime import datetime, timedelta
import random
import json

CLICKHOUSE_HOST = 'localhost'
CLICKHOUSE_PORT = 9000
CLICKHOUSE_DATABASE = 'logs'

SERVICES = ['api-gateway', 'auth-service', 'user-service', 'payment-service']
LOG_LEVELS = ['DEBUG', 'INFO', 'WARN', 'ERROR']

def generate_sample_logs(count=10000):
    """Generate sample log entries"""
    logs = []
    base_time = datetime.now() - timedelta(days=7)
    
    for i in range(count):
        timestamp = base_time + timedelta(seconds=i * 60)
        service = random.choice(SERVICES)
        level = random.choices(LOG_LEVELS, weights=[30, 50, 15, 5])[0]
        
        logs.append((
            timestamp,
            service,
            level,
            f'Sample log message {i}',
            json.dumps({
                'request_id': f'req-{i}',
                'user_id': f'user-{random.randint(1, 1000)}'
            })
        ))
    
    return logs


def seed_database():
    """Seed ClickHouse with sample data"""
    client = Client(host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT)
    
    print('Generating sample logs...')
    logs = generate_sample_logs(10000)
    
    print('Inserting into ClickHouse...')
    query = '''
        INSERT INTO logs.logs (timestamp, service, level, message, metadata)
        VALUES
    '''
    
    client.execute(query, logs)
    
    print(f'Successfully inserted {len(logs)} sample logs')
    
    # Verify insertion
    count = client.execute('SELECT count() FROM logs.logs')[0][0]
    print(f'Total logs in database: {count}')


if __name__ == '__main__':
    seed_database()
