import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import require_roles
from app.db.session import get_db
from app.models.cloud import IntegrationConnection, IntegrationOutbox, IntegrationSyncRun
from app.models.models import User
from app.schemas.cloud import IntegrationCreate, OutboxEventCreate, SyncRequest
from app.services.cloud import create_connection, enqueue_event, queue_sync, retry_outbox_event, outbox_summary

router = APIRouter()
ADMIN = ("administrator", "eurogrip_admin")

@router.post("/admin/integrations/connections", status_code=201)
def add_connection(payload: IntegrationCreate, db: Session=Depends(get_db),
                   user: User=Depends(require_roles(*ADMIN))):
    try: row=create_connection(db,user.id,payload)
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc))
    return {"data":{"id":row.id,"provider":row.provider,"connection_name":row.connection_name,
        "environment":row.environment,"status":row.status,"credential_env_key":row.credential_env_key,
        "base_url":row.base_url,"config":json.loads(row.config_json),"created_at":row.created_at}}

@router.get("/admin/integrations/connections")
def list_connections(db: Session=Depends(get_db), user: User=Depends(require_roles(*ADMIN))):
    rows=db.scalars(select(IntegrationConnection).order_by(IntegrationConnection.created_at.desc())).all()
    return {"data":[{"id":x.id,"provider":x.provider,"connection_name":x.connection_name,
        "environment":x.environment,"status":x.status,"credential_env_key":x.credential_env_key,
        "base_url":x.base_url,"config":json.loads(x.config_json)} for x in rows]}

@router.post("/admin/integrations/connections/{connection_id}/sync",status_code=202)
def request_sync(connection_id: str,payload: SyncRequest,db: Session=Depends(get_db),
                 user: User=Depends(require_roles(*ADMIN))):
    connection=db.get(IntegrationConnection,connection_id)
    if not connection: raise HTTPException(status_code=404,detail="Integration connection not found.")
    if connection.status!="configured": raise HTTPException(status_code=409,detail="Integration credentials are not configured in the deployment environment.")
    row=queue_sync(db,connection,payload.operation)
    return {"data":{"run_id":row.id,"status":row.status,"operation":row.operation,
        "message":"Sync request queued. An enabled provider worker is required to execute it."}}

@router.get("/admin/integrations/sync-runs")
def sync_runs(db: Session=Depends(get_db),user: User=Depends(require_roles(*ADMIN))):
    rows=db.scalars(select(IntegrationSyncRun).order_by(IntegrationSyncRun.created_at.desc()).limit(200)).all()
    return {"data":[{"id":x.id,"connection_id":x.connection_id,"operation":x.operation,
        "status":x.status,"records_read":x.records_read,"records_written":x.records_written,
        "error_code":x.error_code,"created_at":x.created_at} for x in rows]}

@router.post("/admin/integrations/outbox",status_code=201)
def create_outbox_event(payload: OutboxEventCreate,db: Session=Depends(get_db),
                        user: User=Depends(require_roles(*ADMIN))):
    row=enqueue_event(db,payload.event_type,payload.aggregate_type,payload.aggregate_id,payload.payload)
    return {"data":{"id":row.id,"event_type":row.event_type,"status":row.status,"created_at":row.created_at}}

@router.get("/admin/integrations/outbox")
def list_outbox(db: Session=Depends(get_db),user: User=Depends(require_roles(*ADMIN))):
    rows=db.scalars(select(IntegrationOutbox).order_by(IntegrationOutbox.created_at.desc()).limit(200)).all()
    return {"data":{"summary":outbox_summary(db),"events":[{"id":x.id,"event_type":x.event_type,
        "aggregate_type":x.aggregate_type,"aggregate_id":x.aggregate_id,"status":x.status,
        "attempts":x.attempts,"last_error_code":x.last_error_code,"created_at":x.created_at} for x in rows]}}

@router.post("/admin/integrations/outbox/{event_id}/retry")
def retry_event(event_id: str,db: Session=Depends(get_db),user: User=Depends(require_roles(*ADMIN))):
    event=db.get(IntegrationOutbox,event_id)
    if not event: raise HTTPException(status_code=404,detail="Outbox event not found.")
    try: retry_outbox_event(db,event)
    except ValueError as exc: raise HTTPException(status_code=409,detail=str(exc))
    return {"data":{"id":event.id,"status":event.status,"attempts":event.attempts}}
