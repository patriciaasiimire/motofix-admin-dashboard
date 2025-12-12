from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from ..deps import verify_admin_token
from ..db import get_db

router = APIRouter(prefix="/admin", tags=["Admin"])


# ──────────────────────────── MODELS ────────────────────────────

class MechanicCreate(BaseModel):
    phone: str
    name: str
    location: Optional[str] = None
    is_verified: bool = False


class MechanicUpdate(BaseModel):
    phone: Optional[str] = None
    name: Optional[str] = None
    location: Optional[str] = None
    is_verified: Optional[bool] = None
    rating: Optional[int] = None
    jobs_completed: Optional[int] = None


# ────────────────────────── SERVICE REQUESTS ──────────────────────────

@router.get("/requests")
async def list_requests(
    status: Optional[str] = Query(None),
    limit: int = 100,
    db=Depends(get_db),
    admin=Depends(verify_admin_token)
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
    verified: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=200),
    db=Depends(get_db),
    admin=Depends(verify_admin_token)
):
    """
    Return mechanics with optional search and pagination.
    Supports filtering by verification status and fuzzy match on name/phone/location.
    """
    offset = (page - 1) * pageSize
    params = []
    conditions = []

    if verified is not None:
        conditions.append(f"is_verified = ${len(params) + 1}")
        params.append(verified)

    if search:
        like_term = f"%{search.lower()}%"
        conditions.append(
            f"(lower(name) LIKE ${len(params) + 1} OR lower(phone) LIKE ${len(params) + 1} OR lower(location) LIKE ${len(params) + 1})"
        )
        params.append(like_term)

    where_sql = " WHERE " + " AND ".join(conditions) if conditions else ""

    total = await db.fetchval(f"SELECT COUNT(*) FROM mechanics{where_sql}", *params)

    query = f"""
        SELECT id, phone, name, location, is_verified, rating, jobs_completed, created_at
        FROM mechanics
        {where_sql}
        ORDER BY created_at DESC
        LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
    """
    rows = await db.fetch(query, *params, pageSize, offset)

    data = [dict(r) for r in rows]
    return {
        "data": data,
        "page": page,
        "pageSize": pageSize,
        "total": total,
        "totalPages": (total + pageSize - 1) // pageSize if total is not None else 0,
    }


@router.post("/mechanics")
async def add_mechanic(
    mechanic: MechanicCreate,
    db=Depends(get_db),
    admin=Depends(verify_admin_token)
):
    # Normalize phone
    phone = mechanic.phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("0"):
        phone = "+256" + phone[1:]
    elif not phone.startswith("+"):
        phone = "+256" + phone

    query = """
        INSERT INTO mechanics (phone, name, location, is_verified, rating, jobs_completed)
        VALUES ($1, $2, $3, $4, 0, 0)
        RETURNING *
    """

    result = await db.fetchrow(
        query,
        phone,
        mechanic.name,
        mechanic.location,
        mechanic.is_verified
    )

    return dict(result)


@router.patch("/mechanics/{mechanic_id}")
async def update_mechanic(
    mechanic_id: int,
    updates: MechanicUpdate,
    db=Depends(get_db),
    admin=Depends(verify_admin_token)
):
    update_data = updates.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    # Build dynamic SQL
    set_parts = []
    params = []

    for idx, (key, value) in enumerate(update_data.items(), start=1):
        set_parts.append(f"{key} = ${idx}")
        params.append(value)

    params.append(mechanic_id)

    query = f"""
        UPDATE mechanics
        SET {', '.join(set_parts)}
        WHERE id = ${len(params)}
        RETURNING *
    """

    result = await db.fetchrow(query, *params)

    if not result:
        raise HTTPException(status_code=404, detail="Mechanic not found")

    return dict(result)


@router.delete("/mechanics/{mechanic_id}")
async def delete_mechanic(
    mechanic_id: int,
    db=Depends(get_db),
    admin=Depends(verify_admin_token)
):
    result = await db.fetchval("DELETE FROM mechanics WHERE id = $1 RETURNING id", mechanic_id)

    if not result:
        raise HTTPException(status_code=404, detail="Mechanic not found")

    return {"detail": "Mechanic deleted successfully"}


# ───────────────────────────── PAYMENTS WITH PAGINATION ───────────────────────────────

@router.get("/payments")
async def list_payments(
    phone: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db=Depends(get_db),
    admin=Depends(verify_admin_token)
):
    offset = (page - 1) * page_size
    params = []
    conditions = []

    # Phone normalization
    if phone:
        clean = phone.strip().replace(" ", "").replace("-", "")
        if clean.startswith("0"):
            clean = "+256" + clean[1:]
        elif not clean.startswith("+"):
            clean = "+256" + clean
        conditions.append(f"phone = ${len(params) + 1}")
        params.append(clean)

    if type:
        conditions.append(f"type = ${len(params) + 1}")
        params.append(type)

    if status:
        conditions.append(f"status = ${len(params) + 1}")
        params.append(status)

    where_sql = " WHERE " + " AND ".join(conditions) if conditions else ""

    total = await db.fetchval(f"SELECT COUNT(*) FROM payments{where_sql}", *params)

    query = f"""
        SELECT id, transaction_id, phone, amount, type, status, reason, provider, metadata,
               created_at, updated_at
        FROM payments
        {where_sql}
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
        "search": {"phone": phone, "type": type, "status": status}
    }


# ────────────────────────────── STATS ─────────────────────────────────

@router.get("/stats")
async def dashboard_stats(
    db=Depends(get_db),
    admin=Depends(verify_admin_token)
):
    stats = {}

    stats["total_requests"] = await db.fetchval("SELECT COUNT(*) FROM service_requests") or 0
    stats["completed_jobs"] = await db.fetchval(
        "SELECT COUNT(*) FROM service_requests WHERE status = 'completed'"
    ) or 0
    stats["pending_jobs"] = await db.fetchval(
        "SELECT COUNT(*) FROM service_requests WHERE status IN ('pending', 'accepted')"
    ) or 0

    stats["total_mechanics"] = await db.fetchval("SELECT COUNT(*) FROM mechanics") or 0
    stats["verified_mechanics"] = await db.fetchval(
        "SELECT COUNT(*) FROM mechanics WHERE is_verified = true"
    ) or 0

    collected = await db.fetchval(
        "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE type='collection' AND status='success'"
    )
    paid_out = await db.fetchval(
        "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE type='payout' AND status='success'"
    )

    stats["revenue_collected_ugx"] = float(collected or 0)
    stats["paid_to_mechanics_ugx"] = float(paid_out or 0)
    stats["profit_ugx"] = float((collected or 0) - (paid_out or 0))
    stats["total_transactions"] = await db.fetchval("SELECT COUNT(*) FROM payments") or 0

    stats["as_of"] = datetime.utcnow().isoformat() + "Z"
    stats["motofix_is_unstoppable"] = True

    return stats


# ───────────────────────────── REVENUE CHART ─────────────────────────────

@router.get("/dashboard/revenue-chart")
async def revenue_chart(
    limit: int = 30,
    db=Depends(get_db),
    admin=Depends(verify_admin_token)
):
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

    data = [
        {"date": r["date"], "amount": float(r["amount"])}
        for r in rows
    ]

    return list(reversed(data))