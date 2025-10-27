"""
Query API - HTTP/gRPC service for querying logs from ClickHouse
Supports filtering by time range, service, level, and full-text search
"""
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
from clickhouse_driver import Client
import json
import gzip
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
CLICKHOUSE_HOST = os.getenv('CLICKHOUSE_HOST', 'clickhouse')
CLICKHOUSE_PORT = int(os.getenv('CLICKHOUSE_PORT', '9000'))
CLICKHOUSE_DATABASE = os.getenv('CLICKHOUSE_DATABASE', 'logs')

app = FastAPI(
    title="Log Query API",
    description="Query interface for cloud-scale log ingestion pipeline",
    version="1.0.0"
)

# Initialize ClickHouse client
clickhouse = Client(
    host=CLICKHOUSE_HOST,
    port=CLICKHOUSE_PORT,
    database=CLICKHOUSE_DATABASE
)


class LogQuery(BaseModel):
    """Log query parameters"""
    start_time: Optional[datetime] = Field(None, description="Start time for query range")
    end_time: Optional[datetime] = Field(None, description="End time for query range")
    service: Optional[str] = Field(None, description="Filter by service name")
    level: Optional[str] = Field(None, description="Filter by log level (DEBUG, INFO, WARN, ERROR)")
    search: Optional[str] = Field(None, description="Full-text search in message")
    limit: int = Field(1000, ge=1, le=10000, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Offset for pagination")


class LogEntry(BaseModel):
    """Log entry response model"""
    timestamp: datetime
    service: str
    level: str
    message: str
    metadata: dict


class QueryResponse(BaseModel):
    """Query response with pagination"""
    total: int
    limit: int
    offset: int
    logs: List[LogEntry]
    query_time_ms: float


class AggregationResponse(BaseModel):
    """Aggregation response"""
    service: str
    level: str
    count: int
    hour: datetime


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "Log Query API",
        "version": "1.0.0",
        "endpoints": {
            "query": "/api/v1/logs",
            "aggregate": "/api/v1/logs/aggregate",
            "errors": "/api/v1/logs/errors",
            "health": "/health"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        clickhouse.execute('SELECT 1')
        return {"status": "healthy", "clickhouse": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.post("/api/v1/logs", response_model=QueryResponse)
async def query_logs(query: LogQuery):
    """
    Query logs with filtering and pagination
    
    Supports:
    - Time range filtering
    - Service and level filtering
    - Full-text search
    - Pagination
    """
    try:
        start = datetime.now()
        
        # Build WHERE clause
        conditions = []
        params = {}
        
        if query.start_time:
            conditions.append("timestamp >= %(start_time)s")
            params['start_time'] = query.start_time
        else:
            # Default to last 24 hours
            conditions.append("timestamp >= %(start_time)s")
            params['start_time'] = datetime.now() - timedelta(hours=24)
        
        if query.end_time:
            conditions.append("timestamp <= %(end_time)s")
            params['end_time'] = query.end_time
        
        if query.service:
            conditions.append("service = %(service)s")
            params['service'] = query.service
        
        if query.level:
            conditions.append("level = %(level)s")
            params['level'] = query.level.upper()
        
        if query.search:
            conditions.append("positionCaseInsensitive(message, %(search)s) > 0")
            params['search'] = query.search
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # Count total matching records
        count_query = f"SELECT count() FROM logs WHERE {where_clause}"
        total = clickhouse.execute(count_query, params)[0][0]
        
        # Fetch logs
        logs_query = f"""
            SELECT timestamp, service, level, message, metadata
            FROM logs
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT %(limit)s
            OFFSET %(offset)s
        """
        params['limit'] = query.limit
        params['offset'] = query.offset
        
        results = clickhouse.execute(logs_query, params)
        
        # Parse results
        logs = []
        for row in results:
            logs.append(LogEntry(
                timestamp=row[0],
                service=row[1],
                level=row[2],
                message=row[3],
                metadata=json.loads(row[4]) if row[4] else {}
            ))
        
        query_time = (datetime.now() - start).total_seconds() * 1000
        
        return QueryResponse(
            total=total,
            limit=query.limit,
            offset=query.offset,
            logs=logs,
            query_time_ms=round(query_time, 2)
        )
    
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/logs/aggregate")
async def aggregate_logs(
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    service: Optional[str] = Query(None)
):
    """
    Get aggregated log counts by service and level
    Uses materialized view for fast queries
    """
    try:
        conditions = []
        params = {}
        
        if start_time:
            conditions.append("hour >= %(start_time)s")
            params['start_time'] = start_time
        else:
            conditions.append("hour >= %(start_time)s")
            params['start_time'] = datetime.now() - timedelta(hours=24)
        
        if end_time:
            conditions.append("hour <= %(end_time)s")
            params['end_time'] = end_time
        
        if service:
            conditions.append("service = %(service)s")
            params['service'] = service
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
            SELECT service, level, sum(log_count) as count, hour
            FROM logs_by_service_level
            WHERE {where_clause}
            GROUP BY service, level, hour
            ORDER BY hour DESC, count DESC
        """
        
        results = clickhouse.execute(query, params)
        
        aggregations = []
        for row in results:
            aggregations.append(AggregationResponse(
                service=row[0],
                level=row[1],
                count=row[2],
                hour=row[3]
            ))
        
        return aggregations
    
    except Exception as e:
        logger.error(f"Aggregation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/logs/errors")
async def get_errors(
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    service: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Get recent error logs
    Uses materialized view for fast error retrieval
    """
    try:
        conditions = []
        params = {'limit': limit}
        
        if start_time:
            conditions.append("timestamp >= %(start_time)s")
            params['start_time'] = start_time
        else:
            conditions.append("timestamp >= %(start_time)s")
            params['start_time'] = datetime.now() - timedelta(hours=24)
        
        if end_time:
            conditions.append("timestamp <= %(end_time)s")
            params['end_time'] = end_time
        
        if service:
            conditions.append("service = %(service)s")
            params['service'] = service
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
            SELECT timestamp, service, message, metadata
            FROM error_logs
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT %(limit)s
        """
        
        results = clickhouse.execute(query, params)
        
        errors = []
        for row in results:
            errors.append({
                'timestamp': row[0].isoformat(),
                'service': row[1],
                'message': row[2],
                'metadata': json.loads(row[3]) if row[3] else {}
            })
        
        return errors
    
    except Exception as e:
        logger.error(f"Error query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/logs/export")
async def export_logs(
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    service: Optional[str] = Query(None),
    format: str = Query("json", regex="^(json|csv)$")
):
    """
    Export logs in JSON or CSV format with gzip compression
    """
    try:
        conditions = []
        params = {}
        
        if start_time:
            conditions.append("timestamp >= %(start_time)s")
            params['start_time'] = start_time
        
        if end_time:
            conditions.append("timestamp <= %(end_time)s")
            params['end_time'] = end_time
        
        if service:
            conditions.append("service = %(service)s")
            params['service'] = service
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
            SELECT timestamp, service, level, message, metadata
            FROM logs
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT 100000
        """
        
        results = clickhouse.execute(query, params)
        
        # Generate export data
        if format == "json":
            data = json.dumps([{
                'timestamp': row[0].isoformat(),
                'service': row[1],
                'level': row[2],
                'message': row[3],
                'metadata': json.loads(row[4]) if row[4] else {}
            } for row in results], indent=2)
            content_type = "application/json"
            filename = f"logs-export-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json.gz"
        else:  # CSV
            lines = ["timestamp,service,level,message"]
            for row in results:
                lines.append(f"{row[0].isoformat()},{row[1]},{row[2]},\"{row[3]}\"")
            data = "\n".join(lines)
            content_type = "text/csv"
            filename = f"logs-export-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv.gz"
        
        # Compress with gzip
        compressed = gzip.compress(data.encode('utf-8'))
        
        return StreamingResponse(
            iter([compressed]),
            media_type=content_type,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Encoding': 'gzip'
            }
        )
    
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
