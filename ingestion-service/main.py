"""
Log Ingestion Service - gRPC endpoint that publishes logs to Kafka
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncIterator
import grpc
from grpc import aio
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'logs-ingestion')

# Initialize Kafka producer with idempotent settings
producer_config = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'client.id': 'log-ingestion-service',
    'enable.idempotence': True,
    'acks': 'all',
    'retries': 10,
    'max.in.flight.requests.per.connection': 5,
    'compression.type': 'lz4',
    'linger.ms': 10,
    'batch.size': 32768,
}

producer = Producer(producer_config)


def delivery_report(err, msg):
    """Callback for message delivery reports"""
    if err is not None:
        logger.error(f'Message delivery failed: {err}')
    else:
        logger.debug(f'Message delivered to {msg.topic()} [{msg.partition()}]')


class LogIngestionService:
    """gRPC service for log ingestion"""
    
    async def IngestLog(self, request, context):
        """Single log ingestion"""
        try:
            log_entry = {
                'timestamp': request.timestamp or datetime.utcnow().isoformat(),
                'service': request.service,
                'level': request.level,
                'message': request.message,
                'metadata': json.loads(request.metadata) if request.metadata else {}
            }
            
            # Use service name as partition key for better distribution
            key = request.service.encode('utf-8')
            value = json.dumps(log_entry).encode('utf-8')
            
            # Produce to Kafka
            producer.produce(
                KAFKA_TOPIC,
                key=key,
                value=value,
                callback=delivery_report
            )
            producer.poll(0)
            
            return {'success': True, 'message': 'Log ingested successfully'}
            
        except Exception as e:
            logger.error(f'Error ingesting log: {e}')
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return {'success': False, 'message': str(e)}
    
    async def IngestLogBatch(self, request, context):
        """Batch log ingestion for higher throughput"""
        try:
            success_count = 0
            
            for log in request.logs:
                log_entry = {
                    'timestamp': log.timestamp or datetime.utcnow().isoformat(),
                    'service': log.service,
                    'level': log.level,
                    'message': log.message,
                    'metadata': json.loads(log.metadata) if log.metadata else {}
                }
                
                key = log.service.encode('utf-8')
                value = json.dumps(log_entry).encode('utf-8')
                
                producer.produce(
                    KAFKA_TOPIC,
                    key=key,
                    value=value,
                    callback=delivery_report
                )
                success_count += 1
            
            # Flush to ensure all messages are sent
            producer.flush()
            
            return {
                'success': True,
                'message': f'{success_count} logs ingested successfully',
                'count': success_count
            }
            
        except Exception as e:
            logger.error(f'Error ingesting batch: {e}')
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return {'success': False, 'message': str(e), 'count': 0}


async def serve():
    """Start the gRPC server"""
    server = aio.server()
    # Add service to server (proto definitions would be generated)
    # server.add_LogIngestionServiceServicer_to_server(LogIngestionService(), server)
    
    listen_addr = '[::]:50051'
    server.add_insecure_port(listen_addr)
    
    logger.info(f'Starting gRPC server on {listen_addr}')
    await server.start()
    
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info('Shutting down server...')
        await server.stop(5)
        producer.flush()


if __name__ == '__main__':
    asyncio.run(serve())
