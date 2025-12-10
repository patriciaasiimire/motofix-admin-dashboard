# app/routers/admin.py
from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime
from ..deps import verify_admin_token  # JWT protection
from ..db import get_db

router = APIRouter(prefix="/admin", tags=["Admin"])


# ────────────────────────── SERVICE REQUESTS ──────────────────────────
@router.get("/requests")
async def list_requests(
    status: Optional[str] = Query(None),
    limit: int = 100,
    db = Depends(get_db),
    admin = Depends(verify_admin_token)
):
    if status:
        rows = await db.fetch(
            "SELECT * FROM service_requests WHERE status = $1 ORDER BY created_at DESC LIMIT $2",
            status, limit
        )
    else:
        rows = await db.fetch(
            "SELECT * FROM service_requests ORDER BY created_at DESC LIMIT $1", limit
        )
    return [dict(r) for r in rows]


# ───────────────────────────── MECHANICS ──────────────────────────────
@router.get("/mechanics")
async def list_mechanics(
    verified: Optional[bool] = None,
    db = Depends(get_db),
    admin = Depends(verify_admin_token)
):
    if verified is not None:
        rows = await db.fetch(
            "SELECT id, phone, name, location, is_verified, rating, jobs_completed, created_at FROM mechanics WHERE is_verified = $1",
            verified
        )
    else:
        rows = await db.fetch(
            "SELECT id, phone, name, location, is_verified, rating, jobs_completed, created_at FROM mechanics"
        )
    return [dict(r) for r in rows]


# ───────────────────────────── PAYMENTS WITH PAGINATION ───────────────────────────────
@router.get("/payments")
async def list_payments(
    phone: Optional[str] = Query(None, description="Search by phone number (e.g. +256758969973 or 0758969973)"),
    type: Optional[str] = Query(None, description="collection or payout"),
    status: Optional[str] = Query(None, description="success, pending, failed"),
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    db = Depends(get_db),
    admin = Depends(verify_admin_token)
):
    offset = (page - 1) * page_size
    params = []
    conditions = []

    # Phone search – smart: works with or without +, with 0 or 07
    if phone:
        clean_phone = phone.strip().replace(" ", "").replace("-", "")
        if clean_phone.startswith("0"):
            clean_phone = "+256" + clean_phone[1:]
        elif not clean_phone.startswith("+"):
            clean_phone = "+256" + clean_phone

        conditions.append(f"phone = ${len(params)+1}")
        params.append(clean_phone)

    if type:
        conditions.append(f"type = ${len(params)+1}")
        params.append(type)
    if status:
        conditions.append(f"status = ${len(params)+1}")
        params.append(status)

    where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""

    # Total count
    total = await db.fetchval("SELECT COUNT(*) FROM payments" + where_clause, *params) or 0

    # Results
    query = f"""
        SELECT 
            id, transaction_id, phone, amount, type, status, 
            reason, provider, metadata, created_at, updated_at
        FROM payments
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ${len(params)+1} OFFSET ${len(params)+2}
    """
    params.extend([page_size, offset])
    rows = await db.fetch(query, *params)

    return {
        "data": [dict(r) for r in rows],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": (total + page_size - 1) // page_size,
            "has_next": page * page_size < total,
            "has_prev": page > 1
        },
        "search": {
            "phone": phone,
            "type": type,
            "status": status
        },
        "tip": "Phone search works with +256, 0, or 07 — we normalize it automatically"
    }


# ────────────────────────────── STATS ─────────────────────────────────
@router.get("/stats")
async def dashboard_stats(db = Depends(get_db), admin = Depends(verify_admin_token)):
    stats = {}

    # Requests
    stats["total_requests"] = await db.fetchval("SELECT COUNT(*) FROM service_requests") or 0
    stats["completed_jobs"] = await db.fetchval("SELECT COUNT(*) FROM service_requests WHERE status = 'completed'") or 0
    stats["pending_jobs"] = await db.fetchval("SELECT COUNT(*) FROM service_requests WHERE status IN ('pending', 'accepted')") or 0

    # Mechanics
    stats["total_mechanics"] = await db.fetchval("SELECT COUNT(*) FROM mechanics") or 0
    stats["verified_mechanics"] = await db.fetchval("SELECT COUNT(*) FROM mechanics WHERE is_verified = true") or 0

    # Money — safe even if no payments yet
    collected = await db.fetchval("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE type = 'collection' AND status = 'success'") or 0
    paid_out = await db.fetchval("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE type = 'payout' AND status = 'success'") or 0

    stats["revenue_collected_ugx"] = float(collected)
    stats["paid_to_mechanics_ugx"] = float(paid_out)
    stats["profit_ugx"] = float(collected - paid_out)
    stats["total_transactions"] = await db.fetchval("SELECT COUNT(*) FROM payments") or 0

    stats["as_of"] = datetime.utcnow().isoformat() + "Z"
    stats["motofix_is_unstoppable"] = True

    return stats


# ───────────────────────────── REVENUE CHART ─────────────────────────────
@router.get("/dashboard/revenue-chart")
async def revenue_chart(limit: int = 30, db = Depends(get_db), admin = Depends(verify_admin_token)):
    """
    Return recent daily revenue points for successful collection transactions.
    Aggregates `payments` by date (YYYY-MM-DD) and returns up to `limit`
    days in ascending order (oldest -> newest).
    """
    query = """
        SELECT to_char(created_at::date, 'YYYY-MM-DD') AS date,
               COALESCE(SUM(amount), 0) AS amount
        FROM payments
        WHERE type = 'collection' AND status = 'success'
        GROUP BY date
        ORDER BY date DESC
        LIMIT $1
    """
    rows = await db.fetch(query, limit)
    # rows come back newest-first; transform and reverse for charting (oldest-first)
    data = [{
        "date": r["date"],
        "amount": float(r["amount"] or 0)
    } for r in rows]
    return list(reversed(data))