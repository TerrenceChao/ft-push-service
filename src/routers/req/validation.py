from fastapi import (
    Path,
)
from ...domains.data.models import UserDTO


def websocket_endpoint_check(
    role: str = Path(...),
    role_id: int = Path(...),
) -> (UserDTO):
    return UserDTO(
        role=role,
        role_id=role_id
    )
