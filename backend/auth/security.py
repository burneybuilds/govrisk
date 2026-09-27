import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from dotenv import load_dotenv
import bcrypt
from jose import JWTError, jwt

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "govrisk-dev-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


# bcrypt hashes at most 72 bytes of input and raises ValueError beyond that.
BCRYPT_MAX_PASSWORD_BYTES = 72


def generate_id() -> str:
    return str(uuid.uuid4())


def hash_password(password: str) -> str:
    encoded = password.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_PASSWORD_BYTES:
        # Callers validate this via the Pydantic schemas; raise a clear error
        # rather than letting bcrypt's ValueError surface as an HTTP 500.
        raise ValueError(
            "password must be at most "
            f"{BCRYPT_MAX_PASSWORD_BYTES} bytes when UTF-8 encoded"
        )
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    encoded = plain_password.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_PASSWORD_BYTES:
        # Cannot match any bcrypt hash, and passing it through raises ValueError,
        # which would surface as an HTTP 500 on the public login endpoint.
        return False
    return bcrypt.checkpw(encoded, hashed_password.encode("utf-8"))


def create_access_token(subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": subject,
        "role": role,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": subject,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
