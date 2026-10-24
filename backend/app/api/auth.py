import secrets

from fastapi import Header, HTTPException

from app.config.settings import operator_token


def require_operator(x_operator_token: str | None = Header(default=None)) -> None:
    expected = operator_token()
    if not expected:
        raise HTTPException(
            status_code=403,
            detail={
                "status": "NOT_CONFIGURED",
                "message": "Set OPERATOR_TOKEN before trial, knock, or motion commands.",
            },
        )
    if x_operator_token is None:
        raise HTTPException(status_code=401, detail={"status": "UNAUTHORIZED"})
    try:
        matches = secrets.compare_digest(x_operator_token, expected)
    except (TypeError, ValueError):
        matches = False
    if not matches:
        raise HTTPException(status_code=401, detail={"status": "UNAUTHORIZED"})
