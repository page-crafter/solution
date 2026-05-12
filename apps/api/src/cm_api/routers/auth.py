from fastapi import APIRouter, Depends

from cm_api.auth.dependencies import get_current_user
from cm_api.auth.user import CurrentUser

router = APIRouter(tags=["auth"])


@router.get("/me")
def read_me(user: CurrentUser = Depends(get_current_user)) -> dict[str, str]:
    """Return the authenticated user profile consumed by the web shell."""
    return {"subject": user.subject, "email": user.email, "displayName": user.display_name}
