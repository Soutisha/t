import hashlib
import hmac
import time
import uuid
import json
import logging
from collections import Counter
from contextlib import asynccontextmanager
from collections import defaultdict, deque
from threading import Lock
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from app.api.deps import require_roles
from app.db.session import get_db
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.models import models  # noqa: F401
from app.models import passport  # noqa: F401
from app.models import toolbank  # noqa: F401
from app.models import trustvision  # noqa: F401
from app.models import copilot  # noqa: F401
from app.models import agents  # noqa: F401
from app.models import geospatial  # noqa: F401
from app.models import academy  # noqa: F401
from app.models import security  # noqa: F401
from app.models import privacy  # noqa: F401
from app.models import cloud  # noqa: F401
from app.models.security import SecurityAuditEvent
from app.db.session import SessionLocal
from app.api.routes import router
from app.api.passport_routes import router as passport_router
from app.api.toolbank_routes import router as toolbank_router
from app.api.advocacy_routes import router as advocacy_router
from app.api.trustvision_routes import router as trustvision_router
from app.api.copilot_routes import router as copilot_router
from app.api.agent_routes import router as agent_router
from app.api.geospatial_routes import router as geospatial_router
from app.api.academy_routes import router as academy_router
from app.api.cloud_routes import router as cloud_router
from app.api.analytics_routes import router as analytics_router
from app.api.privacy_routes import router as privacy_router

class JsonLogFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "method", "path", "status_code", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

_handler = logging.StreamHandler()
_handler.setFormatter(JsonLogFormatter())
_root_logger = logging.getLogger()
if not any(getattr(handler, "_pitstop_json", False) for handler in _root_logger.handlers):
    _handler._pitstop_json = True
    _root_logger.addHandler(_handler)
_root_logger.setLevel(getattr(logging, settings.cloud_log_level.upper(), logging.INFO))
logger = logging.getLogger("pitstop.api")

_metrics_lock = Lock()
_request_counts = Counter()
_request_duration_buckets = Counter()
_request_duration_counts = Counter()
_request_duration_sums = Counter()
_METRIC_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Convenient local bootstrap. Production must use reviewed Alembic migrations.
    if settings.app_env == "development":
        Base.metadata.create_all(bind=engine)
    app.state.redis = None
    if settings.redis_url:
        try:
            from redis.asyncio import from_url
            app.state.redis = from_url(settings.redis_url, decode_responses=True)
            await app.state.redis.ping()
        except Exception:
            if settings.app_env.lower() in ("production", "prod"):
                raise RuntimeError("Redis is required in production but could not be reached.")
            app.state.redis = None
    yield
    if app.state.redis is not None:
        await app.state.redis.aclose()

app = FastAPI(title=settings.app_name, version="0.30.0", description="Mechanic advocacy and enablement platform API", lifespan=lifespan)
_rate_lock = Lock()
_rate_buckets = defaultdict(deque)
_AUTH_PATHS = ("/api/v1/auth/otp/request", "/api/v1/auth/otp/verify", "/api/v1/onboarding/mechanics")

@app.middleware("http")
async def security_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", "")[:64] or str(uuid.uuid4())
    request.state.request_id = request_id
    started = time.monotonic()
    client_ip = request.client.host if request.client else "unknown"
    fingerprint = hmac.new(settings.client_fingerprint_secret.encode(), client_ip.encode(), hashlib.sha256).hexdigest()
    path = request.url.path
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is not None:
        try:
            general_key = f"pitstop:rate:{fingerprint}:all"
            general_count = await redis_client.incr(general_key)
            if general_count == 1: await redis_client.expire(general_key, 60)
            if general_count > settings.rate_limit_per_minute:
                return __import__("starlette.responses", fromlist=["JSONResponse"]).JSONResponse(
                    status_code=429, content={"detail": "Request rate limit exceeded."},
                    headers={"Retry-After": "60", "X-Request-ID": request_id})
            if path.startswith(_AUTH_PATHS):
                auth_key = f"pitstop:rate:{fingerprint}:{path}"
                auth_count = await redis_client.incr(auth_key)
                if auth_count == 1: await redis_client.expire(auth_key, 60)
                if auth_count > settings.auth_rate_limit_per_minute:
                    return __import__("starlette.responses", fromlist=["JSONResponse"]).JSONResponse(
                        status_code=429, content={"detail": "Too many authentication requests. Try again shortly."},
                        headers={"Retry-After": "60", "X-Request-ID": request_id})
        except Exception:
            if settings.app_env.lower() in ("production", "prod"):
                return __import__("starlette.responses", fromlist=["JSONResponse"]).JSONResponse(
                    status_code=503, content={"detail": "Rate limiting service unavailable."},
                    headers={"Retry-After": "30", "X-Request-ID": request_id})
    else:
        if settings.app_env.lower() in ("production", "prod"):
            return __import__("starlette.responses", fromlist=["JSONResponse"]).JSONResponse(
                status_code=503, content={"detail": "Rate limiting service is not configured."},
                headers={"Retry-After": "30", "X-Request-ID": request_id})
        now = time.monotonic()
        with _rate_lock:
            general = _rate_buckets[(fingerprint, "__all__")]
            while general and now - general[0] >= 60:
                general.popleft()
            if len(general) >= settings.rate_limit_per_minute:
                return __import__("starlette.responses", fromlist=["JSONResponse"]).JSONResponse(
                    status_code=429, content={"detail": "Request rate limit exceeded."},
                    headers={"Retry-After": "60", "X-Request-ID": request_id})
            general.append(now)
            if path.startswith(_AUTH_PATHS):
                auth_bucket = _rate_buckets[(fingerprint, path)]
                while auth_bucket and now - auth_bucket[0] >= 60:
                    auth_bucket.popleft()
                if len(auth_bucket) >= settings.auth_rate_limit_per_minute:
                    return __import__("starlette.responses", fromlist=["JSONResponse"]).JSONResponse(
                        status_code=429, content={"detail": "Too many authentication requests. Try again shortly."},
                        headers={"Retry-After": "60", "X-Request-ID": request_id})
                auth_bucket.append(now)
    try:
        response = await call_next(request)
    except Exception:
        failed_route = request.scope.get("route")
        safe_failed_path = getattr(failed_route, "path", "/unmatched")
        logger.exception("Unhandled request exception", extra={"request_id": request_id, "method": request.method, "path": safe_failed_path})
        response = __import__("starlette.responses", fromlist=["JSONResponse"]).JSONResponse(
            status_code=500, content={"detail": "Internal server error.", "request_id": request_id})
    duration = max(0.0, time.monotonic() - started)
    route = request.scope.get("route")
    metric_path = getattr(route, "path", "/unmatched")
    metric_path = metric_path if metric_path.startswith("/") else "/unknown"
    metric_path = metric_path[:120]
    with _metrics_lock:
        _request_counts[(request.method, metric_path, response.status_code)] += 1
        duration_key = (request.method, metric_path)
        _request_duration_counts[duration_key] += 1
        _request_duration_sums[duration_key] += duration
        for bucket in _METRIC_BUCKETS:
            if duration <= bucket:
                _request_duration_buckets[(request.method, metric_path, bucket)] += 1
        _request_duration_buckets[(request.method, metric_path, "+Inf")] += 1
    logger.info("http_request", extra={
        "request_id": request_id, "method": request.method, "path": metric_path,
        "status_code": response.status_code, "duration_ms": int(duration * 1000)
    })
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=(self)"
    if settings.app_env.lower() in ("production", "prod"):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if settings.audit_log_enabled and (request.method not in ("GET", "HEAD", "OPTIONS") or response.status_code >= 400):
        db = SessionLocal()
        try:
            db.add(SecurityAuditEvent(
                request_id=request_id, actor_user_id=getattr(request.state, "actor_user_id", None),
                method=request.method[:10], path=path[:300], status_code=response.status_code,
                client_fingerprint=fingerprint, user_agent=request.headers.get("user-agent", "")[:300],
                duration_ms=int((time.monotonic()-started)*1000),
                event_type="failed_request" if response.status_code >= 400 else "state_change"
            ))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
    return response
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)
app.include_router(router, prefix="/api/v1")
app.include_router(passport_router, prefix="/api/v1")
app.include_router(toolbank_router, prefix="/api/v1")
app.include_router(advocacy_router, prefix="/api/v1")
app.include_router(trustvision_router, prefix="/api/v1")
app.include_router(copilot_router, prefix="/api/v1")
app.include_router(agent_router, prefix="/api/v1")
app.include_router(geospatial_router, prefix="/api/v1")
app.include_router(academy_router, prefix="/api/v1")
app.include_router(cloud_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(privacy_router, prefix="/api/v1")

@app.get("/internal/metrics", include_in_schema=False, response_class=PlainTextResponse)
def metrics(request: Request):
    supplied = request.headers.get("authorization", "")
    if settings.app_env.lower() in ("production", "prod"):
        expected = f"Bearer {settings.metrics_token}"
        if not settings.metrics_token or not hmac.compare_digest(supplied, expected):
            raise HTTPException(status_code=401, detail="Metrics authentication required.")
    lines = [
        "# HELP pitstop_http_requests_total Total HTTP requests handled by this API process.",
        "# TYPE pitstop_http_requests_total counter",
    ]
    with _metrics_lock:
        for (method, path, status), count in sorted(_request_counts.items()):
            safe_path = path.replace("\\\\", "\\\\\\\\").replace('"', '\\\\"')
            lines.append(f'pitstop_http_requests_total{{method="{method}",path="{safe_path}",status="{status}"}} {count}')
        lines.extend([
            "# HELP pitstop_http_request_duration_seconds HTTP request duration in seconds.",
            "# TYPE pitstop_http_request_duration_seconds histogram",
        ])
        for (method, path), count in sorted(_request_duration_counts.items()):
            safe_path = path.replace("\\\\", "\\\\\\\\").replace('"', '\\\\"')
            for bucket in _METRIC_BUCKETS:
                bucket_count = _request_duration_buckets[(method, path, bucket)]
                lines.append(f'pitstop_http_request_duration_seconds_bucket{{method="{method}",path="{safe_path}",le="{bucket}"}} {bucket_count}')
            inf_count = _request_duration_buckets[(method, path, "+Inf")]
            lines.append(f'pitstop_http_request_duration_seconds_bucket{{method="{method}",path="{safe_path}",le="+Inf"}} {inf_count}')
            lines.append(f'pitstop_http_request_duration_seconds_count{{method="{method}",path="{safe_path}"}} {count}')
            lines.append(f'pitstop_http_request_duration_seconds_sum{{method="{method}",path="{safe_path}"}} {_request_duration_sums[(method, path)]:.6f}')
    return "\\n".join(lines) + "\\n"


@app.get("/health/live")
def live():
    return {"status": "ok", "service": "eurogrip-pitstop-api"}

@app.get("/health/ready")
async def ready(request: Request):
    from fastapi.responses import JSONResponse
    checks = {"database": "unavailable", "redis": "not_configured", "object_storage": "not_configured"}
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["database"] = "connected"
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready", "checks": checks})
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is not None:
        try:
            await redis_client.ping()
            checks["redis"] = "connected"
        except Exception:
            checks["redis"] = "unavailable"
    elif settings.app_env.lower() in ("production", "prod"):
        checks["redis"] = "unavailable"
    if settings.app_env.lower() in ("production", "prod"):
        try:
            from app.services.object_storage import get_object_storage
            get_object_storage().check()
            checks["object_storage"] = "connected"
        except Exception:
            checks["object_storage"] = "unavailable"
        if checks["redis"] != "connected" or checks["object_storage"] != "connected":
            return JSONResponse(status_code=503, content={"status": "not_ready", "checks": checks})
    return {"status": "ready", "checks": checks}


@app.get("/api/v1/admin/security/audit-events")
def security_audit_events(limit: int = 100, db=Depends(get_db),
                          user=Depends(require_roles("administrator", "eurogrip_admin"))):
    from sqlalchemy import select
    bounded = max(1, min(limit, 500))
    rows = db.scalars(select(SecurityAuditEvent).order_by(SecurityAuditEvent.created_at.desc()).limit(bounded)).all()
    return {"data": [{
        "request_id": x.request_id, "actor_user_id": x.actor_user_id,
        "method": x.method, "path": x.path, "status_code": x.status_code,
        "duration_ms": x.duration_ms, "event_type": x.event_type,
        "created_at": x.created_at
    } for x in rows]}
