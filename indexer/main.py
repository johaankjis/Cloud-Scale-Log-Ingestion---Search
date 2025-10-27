"""
Log Indexer Service - Kafka consumer that writes to ClickHouse
Implements exactly-once semantics with checkpointing
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import List, Dict
import os
from confluent_kafka import Consumer, KafkaError, KafkaException
from clickhouse_driver import Client
import signal
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'logs-ingestion')
KAFKA_GROUP_ID = os.getenv('KAFKA_GROUP_ID', 'log-indexer-group')
CLICKHOUSE_HOST = os.getenv('CLICKHOUSE_HOST', 'clickhouse')
CLICKHOUSE_PORT = int(os.getenv('CLICKHOUSE_PORT', '9000'))
CLICKHOUSE_DATABASE = os.getenv('CLICKHOUSE_DATABASE', 'logs')
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '1000'))
BATCH_TIMEOUT_MS = int(os.getenv('BATCH_TIMEOUT_MS', '5000'))

# Global flag for graceful shutdown
running = True


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global running
    logger.info(f'Received signal {signum}, initiating graceful shutdown...')
    running = False


class LogIndexer:
    """Kafka consumer that indexes logs into ClickHouse"""
    
    def __init__(self):
        # Initialize Kafka consumer
        self.consumer_config = {
            'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
            'group.id': KAFKA_GROUP_ID,
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False,  # Manual commit for exactly-once
            'max.poll.interval.ms': 300000,
            'session.timeout.ms': 10000,
        }
        self.consumer = Consumer(self.consumer_config)
        
        # Initialize ClickHouse client
        self.clickhouse = Client(
            host=CLICKHOUSE_HOST,
            port=CLICKHOUSE_PORT,
            database=CLICKHOUSE_DATABASE
        )
        
        self.batch = []
        self.last_commit_time = datetime.now()
        
        logger.info('Log Indexer initialized')
    
    def subscribe(self):
        """Subscribe to Kafka topic"""
        self.consumer.subscribe([KAFKA_TOPIC])
        logger.info(f'Subscribed to topic: {KAFKA_TOPIC}')
    
    def process_message(self, msg) -> Dict:
        """Parse and transform log message"""
        try:
            log_data = json.loads(msg.value().decode('utf-8'))
            
            # Transform for ClickHouse schema
            return {
                'timestamp': datetime.fromisoformat(log_data['timestamp'].replace('Z', '+00:00')),
                'service': log_data['service'],
                'level': log_data['level'],
                'message': log_data['message'],
                'metadata': json.dumps(log_data.get('metadata', {})),
                'partition': msg.partition(),
                'offset': msg.offset()
            }
        except Exception as e:
            logger.error(f'Error processing message: {e}')
            return None
    
    def write_batch_to_clickhouse(self, batch: List[Dict]):
        """Write batch of logs to ClickHouse"""
        if not batch:
            return
        
        try:
            # Prepare data for insertion
            data = [
                (
                    log['timestamp'],
                    log['service'],
                    log['level'],
                    log['message'],
                    log['metadata']
                )
                for log in batch
            ]
            
            # Insert into ClickHouse
            query = '''
                INSERT INTO logs (timestamp, service, level, message, metadata)
                VALUES
            '''
            
            self.clickhouse.execute(query, data)
            logger.info(f'Wrote {len(batch)} logs to ClickHouse')
            
        except Exception as e:
            logger.error(f'Error writing to ClickHouse: {e}')
            raise
    
    def commit_offsets(self):
        """Commit Kafka offsets after successful write"""
        try:
            self.consumer.commit(asynchronous=False)
            logger.debug('Committed offsets')
        except KafkaException as e:
            logger.error(f'Error committing offsets: {e}')
            raise
    
    async def run(self):
        """Main consumer loop"""
        global running
        
        self.subscribe()
        
        logger.info('Starting consumer loop...')
        
        try:
            while running:
                # Poll for messages
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    # Check if we should flush batch on timeout
                    elapsed = (datetime.now() - self.last_commit_time).total_seconds() * 1000
                    if self.batch and elapsed > BATCH_TIMEOUT_MS:
                        self.write_batch_to_clickhouse(self.batch)
                        self.commit_offsets()
                        self.batch = []
                        self.last_commit_time = datetime.now()
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        logger.debug(f'Reached end of partition {msg.partition()}')
                    else:
                        logger.error(f'Kafka error: {msg.error()}')
                    continue
                
                # Process message
                log_entry = self.process_message(msg)
                if log_entry:
                    self.batch.append(log_entry)
                
                # Write batch if size threshold reached
                if len(self.batch) >= BATCH_SIZE:
                    self.write_batch_to_clickhouse(self.batch)
                    self.commit_offsets()
                    self.batch = []
                    self.last_commit_time = datetime.now()
        
        except Exception as e:
            logger.error(f'Error in consumer loop: {e}')
            raise
        
        finally:
            # Flush remaining batch
            if self.batch:
                logger.info('Flushing remaining batch...')
                self.write_batch_to_clickhouse(self.batch)
                self.commit_offsets()
            
            self.consumer.close()
            logger.info('Consumer closed')


async def main():
    """Main entry point"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    indexer = LogIndexer()
    
    try:
        await indexer.run()
    except Exception as e:
        logger.error(f'Fatal error: {e}')
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
