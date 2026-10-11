"""
EcoSort AI — FastAPI Backend

Endpoints:
  POST /api/classify       — Upload image and classify waste
  GET  /api/history        — Get scan history
  DELETE /api/history/{id} — Delete a scan record
  DELETE /api/history      — Clear all scan history
  GET  /api/stats          — Get dashboard statistics
  GET  /api/health         — Health check
"""

import logging
import io
import time
from collections import defaultdict
from typing import List
from datetime import datetime, timedelta
from collections import Counter

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image

from .config import settings
from .models import ClassificationResult, ScanRecord, HistoryDeleteResponse, HealthResponse
from .classifier import classify_image
from .storage import save_scan, get_scans, delete_scan, clear_scans

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Simple in-memory rate limiter: 20 requests/minute per IP
_rate_data: dict = defaultdict(list)
RATE_LIMIT = 20
RATE_WINDOW = 60  # seconds

def check_rate_limit(client_ip: str) -> None:
    now = time.time()
    window_start = now - RATE_WINDOW
    _rate_data[client_ip] = [t for t in _rate_data[client_ip] if t > window_start]
    if len(_rate_data[client_ip]) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 20 requests per minute.")
    _rate_data[client_ip].append(now)

app = FastAPI(
    title="EcoSort AI API",
    description="AI-powered waste classification backend for EcoSort AI.",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_SIZE_BYTES = settings.max_upload_mb * 1024 * 1024


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    from .config import settings as s
    aws_configured = bool(s.aws_access_key_id and s.aws_secret_access_key)
    return HealthResponse(
        status="ok",
        ai_provider=s.ai_provider,
        demo_mode=s.demo_mode,
        aws_configured=aws_configured,
    )


@app.post("/api/classify", response_model=ClassificationResult)
async def classify_waste(request: Request, file: UploadFile = File(...)):
    """
    Accept an image upload and return a waste classification result.

    Validates:
    - File MIME type (JPG, PNG, WebP only)
    - File size (configurable, default 10 MB)
    - Image validity (must be openable with Pillow)
    """
    # Rate limiting
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip)
    # MIME type validation
    content_type = file.content_type or ""
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{content_type}'. Accepted: JPG, PNG, WebP.",
        )

    # Read and size-check
    image_bytes = await file.read()
    if len(image_bytes) > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(image_bytes) / 1024 / 1024:.1f} MB). Maximum: {settings.max_upload_mb} MB.",
        )
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Validate that bytes form a valid image
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
    except Exception:
        raise HTTPException(status_code=400, detail="Could not decode image. Please upload a valid JPG, PNG, or WebP file.")

    # Re-read after verify (verify() closes the stream)
    image_bytes = await file.seek(0) or image_bytes  # noqa: keep original bytes

    try:
        result = await classify_image(image_bytes, media_type=content_type)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Classification error")
        raise HTTPException(status_code=500, detail="Internal classification error. Please try again.")

    # Persist to storage
    try:
        record = ScanRecord(
            id=result.id,
            category=result.category,
            label=result.label,
            confidence=result.confidence,
            recyclable=result.recyclable,
            timestamp=result.timestamp,
            isDemo=result.isDemo,
        )
        await save_scan(record)
    except Exception as e:
        logger.warning(f"Failed to save scan record: {e}")

    return result


@app.get("/api/history", response_model=List[ScanRecord])
async def get_history():
    """Return scan history (DynamoDB or in-memory)."""
    return await get_scans(limit=200)


@app.delete("/api/history/{scan_id}")
async def delete_scan_record(scan_id: str):
    """Delete a specific scan record."""
    deleted = await delete_scan(scan_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Scan record not found.")
    return {"deleted": scan_id}


@app.delete("/api/history", response_model=HistoryDeleteResponse)
async def clear_scan_history():
    """Clear all scan history."""
    count = await clear_scans()
    return HistoryDeleteResponse(deleted=count)


@app.get("/api/stats")
async def get_stats():
    """Return dashboard statistics."""
    scans = await get_scans(limit=500)

    if not scans:
        now = datetime.utcnow()
        return {
            "totalScans": 0,
            "recyclableCount": 0,
            "categoryBreakdown": [],
            "weeklyData": [
                {"day": (now - timedelta(days=6 - i)).strftime("%a"), "scans": 0}
                for i in range(7)
            ],
            "monthlyData": [
                {"month": (now - timedelta(days=30 * (5 - i))).strftime("%b"), "scans": 0}
                for i in range(6)
            ],
            "recentScans": [],
        }

    total = len(scans)
    recyclable_count = sum(1 for s in scans if s.recyclable)

    # Category breakdown
    cat_counts = Counter(s.category for s in scans)
    category_breakdown = [
        {"category": cat, "count": count, "label": cat}
        for cat, count in cat_counts.most_common()
    ]

    # Weekly data (last 7 days)
    now = datetime.utcnow()
    weekly_data = []
    for i in range(7):
        day = now - timedelta(days=6 - i)
        day_str = day.strftime("%Y-%m-%d")
        count = sum(1 for s in scans if s.timestamp.startswith(day_str))
        weekly_data.append({"day": day.strftime("%a"), "scans": count})

    # Monthly data (last 6 months)
    monthly_data = []
    for i in range(6):
        # Approximate: go back by 30*i days
        month_date = now - timedelta(days=30 * (5 - i))
        month_str = month_date.strftime("%Y-%m")
        count = sum(1 for s in scans if s.timestamp.startswith(month_str))
        monthly_data.append({"month": month_date.strftime("%b"), "scans": count})

    recent_scans = [s.model_dump() for s in scans[:5]]

    return {
        "totalScans": total,
        "recyclableCount": recyclable_count,
        "categoryBreakdown": category_breakdown,
        "weeklyData": weekly_data,
        "monthlyData": monthly_data,
        "recentScans": recent_scans,
    }
