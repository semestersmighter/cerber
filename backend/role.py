from fastapi import APIRouter
from db import get_connection

# On utilise APIRouter au lieu de FastAPI
router = APIRouter(
    prefix="/api",
    tags=["roles"] # Cela créera une nouvelle catégorie "roles" dans Swagger
)

@router.get("/verify-role")
def verify_role(token: str, role: str) -> bool:
    query = """
        SELECT 1 
        FROM "Session" s
        JOIN "User" u ON s."nif" = u."nif"
        JOIN "UserRole" ur ON u."nif" = ur."nif"
        JOIN "Role" r ON ur."roleID" = r."roleID"
        WHERE s."sessionToken" = %s 
          AND r."name" = %s 
          AND s."expireAt" >= CURRENT_TIMESTAMP
    """
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (token, role))
            return cur.fetchone() is not None