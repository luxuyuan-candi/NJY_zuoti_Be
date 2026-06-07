from fastapi import Header, HTTPException, status


def require_bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    return authorization.removeprefix("Bearer ").strip()


def require_admin_token(authorization: str | None = Header(default=None)) -> str:
    token = require_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid admin token")
    return token
