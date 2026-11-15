from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.models import User, UserStatus

bearer = HTTPBearer(auto_error=False)

def current_user(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required.")
    try:
        claims = decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired access token.")
    user = db.get(User, claims.get("sub"))
    if not user or user.status != UserStatus.active:
        raise HTTPException(status_code=401, detail="Account is unavailable.")
    request.state.actor_user_id = user.id
    return user

def require_roles(*allowed: str):
    def checker(user: User = Depends(current_user)) -> User:
        roles = {r.role_code for r in user.roles}
        if not roles.intersection(allowed):
            raise HTTPException(status_code=403, detail="You do not have permission to perform this action.")
        return user
    return checker
