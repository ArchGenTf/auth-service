from fastapi import APIRouter, HTTPException, Depends, Header, status
from pydantic import BaseModel, Field
from typing import Optional
from db import get_database
from utils.auth_helper import hash_password, verify_password, create_access_token, create_refresh_token, decode_token

router = APIRouter(prefix="/auth", tags=["auth"])

class UserRegisterInput(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")

class UserLoginInput(BaseModel):
    username: str
    password: str

class TokenRefreshInput(BaseModel):
    refresh_token: str

# Helper dependency to resolve current user from JWT token headers
async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization credentials invalid or missing"
        )

    token = authorization.split(" ")[1]
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token signature expired or malformed"
        )

    db = get_database()
    if db is None:
        # DB fallback for compilation/offline testing
        return {"username": payload.get("sub"), "email": "fallback@archgen.ai"}

    user = await db["users"].find_one({"username": payload.get("sub")})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorized identity not found in database"
        )

    return {"id": str(user["_id"]), "username": user["username"], "email": user["email"]}

@router.post("/register")
async def register(input_data: UserRegisterInput):
    db = get_database()
    if db is None:
        return {"status": "success", "message": "Offline registration mockup successful."}

    # Check duplicate
    existing_user = await db["users"].find_one({"username": input_data.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username is already registered.")

    existing_email = await db["users"].find_one({"email": input_data.email})
    if existing_email:
        raise HTTPException(status_code=400, detail="Email address already registered.")

    user_doc = {
        "username": input_data.username,
        "password": hash_password(input_data.password),
        "email": input_data.email
    }

    await db["users"].insert_one(user_doc)
    return {"status": "success", "message": "Registration completed successfully."}

@router.post("/login")
async def login(input_data: UserLoginInput):
    db = get_database()
    if db is None:
        # Offline Mock Credentials for UI checks
        if input_data.username == "admin" and input_data.password == "admin123":
            access = create_access_token({"sub": "admin"})
            refresh = create_refresh_token({"sub": "admin"})
            return {
                "access_token": access,
                "refresh_token": refresh,
                "user": {"username": "admin", "email": "admin@archgen.ai"}
            }
        raise HTTPException(status_code=401, detail="Invalid mock credentials.")

    user = await db["users"].find_one({"username": input_data.username})
    if not user or not verify_password(input_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    # Generate tokens
    access = create_access_token({"sub": user["username"]})
    refresh = create_refresh_token({"sub": user["username"]})

    return {
        "access_token": access,
        "refresh_token": refresh,
        "user": {
            "username": user["username"],
            "email": user["email"]
        }
    }

@router.post("/refresh")
async def refresh_token(input_data: TokenRefreshInput):
    payload = decode_token(input_data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token signature invalid or expired.")

    new_access = create_access_token({"sub": payload.get("sub")})
    return {"access_token": new_access}

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user
