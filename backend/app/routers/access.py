"""Contrôle d'accès à une ressource selon les rôles de l'utilisateur.

Appelé par les services protégés (SSO) avec l'en-tête
`Authorization: Bearer <jeton>`, ou par le navigateur avec le cookie de session.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status

from .. import events
from ..deps import CurrentUser, current_user, resource_access

router = APIRouter(prefix="/api/access", tags=["contrôle d'accès"])


@router.get("/{slug}")
def check_access(slug: str, request: Request, user: CurrentUser = Depends(current_user)):
    resource = resource_access(user.nif, slug)
    if resource is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ressource inconnue")

    events.log(request, events.ACCESS_CHECK, resource["allowed"], user.nif, slug)
    if not resource["allowed"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Accès refusé pour vos rôles")
    return {"allowed": True, "nif": user.nif, "roles": user.roles,
            "resource": {k: resource[k] for k in ("slug", "name", "url")}}
