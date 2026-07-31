"""Auth and request dependencies.

Role-based access (PRD 10.2): caregiver, nurse, researcher, admin. The token
scheme here is a prototype stand-in for the deployment's real identity provider -
it is deliberately simple and deliberately not a security boundary anyone should
rely on outside a research sandbox.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from ..settings import get_settings

ROLES = ("caregiver", "nurse", "researcher", "admin")

# Prototype token table. Real deployments replace this with OIDC.
DEV_TOKENS = {
    "dev-token": ("dev-user", "admin"),
    "caregiver-token": ("caregiver-1", "caregiver"),
    "nurse-token": ("nurse-1", "nurse"),
    "researcher-token": ("researcher-1", "researcher"),
}


@dataclass
class Principal:
    actor_id: str
    role: str

    def has(self, *roles: str) -> bool:
        return self.role == "admin" or self.role in roles


async def current_principal(authorization: str | None = Header(default=None)) -> Principal:
    settings = get_settings()
    if not settings.api_auth_required:
        return Principal(actor_id="anonymous", role="admin")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    entry = DEV_TOKENS.get(token)
    if entry is None and token == settings.dev_api_token:
        entry = ("dev-user", "admin")
    if entry is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unknown token")
    return Principal(actor_id=entry[0], role=entry[1])


def require(*roles: str):
    async def _dep(principal: Principal = Depends(current_principal)) -> Principal:
        if not principal.has(*roles):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, f"role {principal.role!r} may not do this"
            )
        return principal

    return _dep
