"""Connections page (row 2, UC-001 steps 2-3, A1, E2, FR-002)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import Owner, current_owner
from ..db import get_db
from ..marketplace import MarketplaceError, SimulatorAdapter, get_marketplace
from ..models import Connection, utcnow
from ..schemas import ConnectionToggle
from ..services.common import get_connection

router = APIRouter(prefix="/connections", tags=["connections"])

# Operations Phase 1 needs from a marketplace; missing ones make the connection unavailable.
REQUIRED_OPERATIONS = ["list_listings"]


def connection_out(c: Connection) -> dict:
    # Credentials are never stored or shown; only status and capabilities.
    return {
        "provider": c.provider,
        "enabled": c.enabled,
        "status": c.status,
        "account_name": c.account_name,
        "operations": c.operations,
        "status_detail": c.status_detail,
        "checked_at": c.checked_at,
    }


@router.get("")
def list_connections(owner: Owner = Depends(current_owner), db: Session = Depends(get_db)):
    return [connection_out(get_connection(db, owner.id))]


@router.put("/simulator")
def toggle_simulator(
    body: ConnectionToggle,
    owner: Owner = Depends(current_owner),
    db: Session = Depends(get_db),
    market: SimulatorAdapter = Depends(get_marketplace),
):
    conn = get_connection(db, owner.id)
    conn.enabled = body.enabled
    conn.checked_at = utcnow()
    if not body.enabled:
        # A1: not needed, so it stays disconnected and its operations are unavailable.
        conn.status, conn.operations, conn.account_name, conn.status_detail = "disconnected", [], None, None
    else:
        try:
            caps = market.capabilities()
            missing = [op for op in REQUIRED_OPERATIONS if op not in caps.operations]
            if missing:
                raise MarketplaceError(f"Marketplace does not support: {', '.join(missing)}")
            conn.status, conn.operations = "connected", caps.operations
            conn.account_name, conn.status_detail = caps.account, f"{caps.name}{' (simulated)' if caps.simulated else ''}"
        except MarketplaceError as e:
            # E2: mark unavailable; the owner can retry or carry on without it.
            conn.status, conn.operations, conn.account_name, conn.status_detail = "unavailable", [], None, str(e)
    db.commit()
    return connection_out(conn)
