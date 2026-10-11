"""
EcoSort AI — Storage Layer

Primary: Amazon DynamoDB (when AWS credentials are configured)
Fallback: In-memory storage for development / demo
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from .config import settings
from .models import ScanRecord

logger = logging.getLogger(__name__)

# In-memory fallback store
_memory_store: List[dict] = []


def _is_aws_configured() -> bool:
    return bool(settings.aws_access_key_id and settings.aws_secret_access_key)


def _get_dynamodb_table():
    """Return a DynamoDB Table resource."""
    import boto3
    dynamodb = boto3.resource(
        "dynamodb",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
    )
    return dynamodb.Table(settings.dynamodb_table)


async def save_scan(record: ScanRecord) -> None:
    """Persist a scan record to DynamoDB or in-memory store."""
    if _is_aws_configured():
        try:
            table = _get_dynamodb_table()
            item = record.model_dump()
            # DynamoDB requires Decimal for numbers; confidence can be float
            if item.get("confidence") is not None:
                from decimal import Decimal
                item["confidence"] = Decimal(str(item["confidence"]))
            table.put_item(Item=item)
            logger.info(f"Saved scan {record.id} to DynamoDB")
            return
        except Exception as e:
            logger.warning(f"DynamoDB save failed, falling back to memory: {e}")

    _memory_store.insert(0, record.model_dump())


async def get_scans(limit: int = 100) -> List[ScanRecord]:
    """Retrieve scan records from DynamoDB or in-memory store."""
    if _is_aws_configured():
        try:
            table = _get_dynamodb_table()
            response = table.scan(Limit=limit)
            items = response.get("Items", [])
            # Sort by timestamp descending
            items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            records = []
            for item in items:
                if item.get("confidence") is not None:
                    item["confidence"] = float(item["confidence"])
                records.append(ScanRecord(**item))
            return records
        except Exception as e:
            logger.warning(f"DynamoDB get failed, falling back to memory: {e}")

    return [ScanRecord(**r) for r in _memory_store[:limit]]


async def delete_scan(scan_id: str) -> bool:
    """Delete a scan record by ID."""
    if _is_aws_configured():
        try:
            table = _get_dynamodb_table()
            table.delete_item(Key={"id": scan_id})
            return True
        except Exception as e:
            logger.warning(f"DynamoDB delete failed, falling back to memory: {e}")

    before = len(_memory_store)
    _memory_store[:] = [r for r in _memory_store if r.get("id") != scan_id]
    return len(_memory_store) < before


async def clear_scans() -> int:
    """Clear all scan records."""
    if _is_aws_configured():
        try:
            table = _get_dynamodb_table()
            response = table.scan(ProjectionExpression="id")
            items = response.get("Items", [])
            with table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(Key={"id": item["id"]})
            return len(items)
        except Exception as e:
            logger.warning(f"DynamoDB clear failed, falling back to memory: {e}")

    count = len(_memory_store)
    _memory_store.clear()
    return count
