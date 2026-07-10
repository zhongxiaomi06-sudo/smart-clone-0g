from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any

from pydantic import BaseModel

from .domain import new_id, utc_now

logger = logging.getLogger(__name__)

# 尝试导入 passlib(bcrypt),失败则降级到 hashlib pbkdf2_hmac
try:
    from passlib.context import CryptContext

    _pwd_context: CryptContext | None = CryptContext(schemes=["bcrypt"], deprecated="auto")
    _HAS_PASSLIB = True
except ImportError:  # pragma: no cover
    _pwd_context = None
    _HAS_PASSLIB = False

# 尝试导入 PyJWT,失败则降级到 HMAC-SHA256 手动实现
try:
    import jwt as _pyjwt

    _HAS_PYJWT = True
except ImportError:  # pragma: no cover
    _pyjwt = None
    _HAS_PYJWT = False


# --------------------------------------------------------------------------- #
# 数据模型
# --------------------------------------------------------------------------- #


class User(BaseModel):
    """用户记录。"""

    id: str  # user_xxx 格式
    email: str
    password_hash: str  # bcrypt 哈希
    created_at: str  # ISO UTC
    is_active: bool = True


class UserInfo(BaseModel):
    """对外暴露的用户信息(不含密码)。"""

    id: str
    email: str
    created_at: str


class RegisterRequest(BaseModel):
    email: str
    password: str  # 最少 8 位


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str  # JWT
    token_type: str = "Bearer"
    user: UserInfo


# --------------------------------------------------------------------------- #
# 密码哈希工具(优先 passlib bcrypt,降级 pbkdf2_hmac)
# --------------------------------------------------------------------------- #


def _hash_password(password: str) -> str:
    """对密码进行哈希。优先使用 passlib bcrypt,降级到 pbkdf2_hmac。"""
    if _HAS_PASSLIB and _pwd_context is not None:
        try:
            return _pwd_context.hash(password)
        except Exception:
            pass  # passlib 后端不可用,降级到 pbkdf2_hmac
    # 降级方案格式: pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
    salt = os.urandom(16)
    iterations = 100000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, password_hash: str) -> bool:
    """验证密码。根据哈希格式自动选择验证方式。"""
    if _HAS_PASSLIB and _pwd_context is not None:
        try:
            return _pwd_context.verify(password, password_hash)
        except Exception:
            # passlib 无法识别该格式,尝试降级方案
            pass
    # 降级方案验证: pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
    if password_hash.startswith("pbkdf2_sha256$"):
        try:
            _, iterations_str, salt_hex, hash_hex = password_hash.split("$", 3)
            iterations = int(iterations_str)
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(hash_hex)
            digest = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt, iterations
            )
            return hmac.compare_digest(digest, expected)
        except (ValueError, AttributeError):
            return False
    return False


# --------------------------------------------------------------------------- #
# JWT 工具(优先 PyJWT,降级 HMAC-SHA256 手动实现)
# --------------------------------------------------------------------------- #


def _b64url_encode(data: bytes) -> str:
    """base64url 编码(无填充)。"""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    """base64url 解码(自动补齐填充)。"""
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _create_jwt_fallback(payload: dict[str, Any], secret: str) -> str:
    """降级 JWT 签发: 手动构造 header.payload.signature。"""
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(
        json.dumps(header, separators=(",", ":")).encode("utf-8")
    )
    payload_b64 = _b64url_encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(
        secret.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    return f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"


def _decode_jwt_fallback(token: str, secret: str) -> dict[str, Any] | None:
    """降级 JWT 验证: 校验签名并返回 payload,失败返回 None。"""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_signature = hmac.new(
            secret.encode("utf-8"), signing_input, hashlib.sha256
        ).digest()
        actual_signature = _b64url_decode(signature_b64)
        if not hmac.compare_digest(expected_signature, actual_signature):
            return None
        return json.loads(_b64url_decode(payload_b64))
    except (ValueError, json.JSONDecodeError, AttributeError):
        return None


# --------------------------------------------------------------------------- #
# AuthService
# --------------------------------------------------------------------------- #


class AuthService:
    """用户认证服务: 注册、登录、JWT 签发与验证。"""

    def __init__(self, store, jwt_secret: str, jwt_expire_minutes: int = 1440) -> None:
        self.store = store
        self.jwt_secret = jwt_secret
        self.jwt_expire_minutes = jwt_expire_minutes

    def register(self, email: str, password: str) -> AuthResponse:
        """注册新用户,返回 JWT token。

        步骤:
            1. 密码长度验证(>=8)
            2. 检查 email 是否已存在
            3. bcrypt 哈希密码
            4. 创建 User 记录,写入数据库 users 表
            5. 签发 JWT
        """
        # 密码长度验证
        if len(password) < 8:
            raise ValueError("密码至少需要 8 位")
        # 检查 email 是否已存在
        if self.get_user_by_email(email) is not None:
            raise ValueError("该邮箱已注册")
        # 创建用户记录
        user = User(
            id=new_id("user"),
            email=email,
            password_hash=_hash_password(password),
            created_at=utc_now(),
            is_active=True,
        )
        with self.store._connect() as connection:
            connection.execute(
                """
                INSERT INTO users (id, email, password_hash, created_at, is_active)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user.id,
                    user.email,
                    user.password_hash,
                    user.created_at,
                    1 if user.is_active else 0,
                ),
            )
        logger.info("用户注册成功: id=%s email=%s", user.id, user.email)
        token = self._create_token(user)
        return AuthResponse(
            token=token,
            user=UserInfo(id=user.id, email=user.email, created_at=user.created_at),
        )

    def login(self, email: str, password: str) -> AuthResponse:
        """登录,返回 JWT token。

        步骤:
            1. 查找用户
            2. 验证密码(bcrypt verify)
            3. 签发 JWT
        """
        user = self.get_user_by_email(email)
        if user is None or not _verify_password(password, user.password_hash):
            raise ValueError("邮箱或密码错误")
        if not user.is_active:
            raise ValueError("邮箱或密码错误")
        logger.info("用户登录成功: id=%s email=%s", user.id, user.email)
        token = self._create_token(user)
        return AuthResponse(
            token=token,
            user=UserInfo(id=user.id, email=user.email, created_at=user.created_at),
        )

    def verify_token(self, token: str) -> str | None:
        """验证 JWT token,返回 user_id 或 None。

        步骤:
            1. 解码 JWT
            2. 检查过期
            3. 返回 user_id
        """
        payload = self._decode_token(token)
        if payload is None:
            return None
        # 检查过期(PyJWT 已在 decode 时校验,此处为降级方案兜底)
        exp = payload.get("exp")
        if exp is None or time.time() > exp:
            return None
        user_id = payload.get("sub")
        if not isinstance(user_id, str):
            return None
        return user_id

    def get_user_by_id(self, user_id: str) -> User | None:
        """根据 ID 查找用户。"""
        with self.store._connect() as connection:
            row = connection.execute(
                "SELECT id, email, password_hash, created_at, is_active FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_user(row)

    def get_user_by_email(self, email: str) -> User | None:
        """根据 email 查找用户。"""
        with self.store._connect() as connection:
            row = connection.execute(
                "SELECT id, email, password_hash, created_at, is_active FROM users WHERE email = ?",
                (email,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_user(row)

    def _create_token(self, user: User) -> str:
        """签发 JWT。payload 包含 sub(user_id)、email、iat、exp。"""
        now = int(time.time())
        payload = {
            "sub": user.id,
            "email": user.email,
            "iat": now,
            "exp": now + self.jwt_expire_minutes * 60,
        }
        if _HAS_PYJWT and _pyjwt is not None:
            token = _pyjwt.encode(payload, self.jwt_secret, algorithm="HS256")
            # PyJWT < 2.0 返回 bytes, >= 2.0 返回 str
            if isinstance(token, bytes):
                token = token.decode("utf-8")
            return token
        return _create_jwt_fallback(payload, self.jwt_secret)

    def _decode_token(self, token: str) -> dict[str, Any] | None:
        """解码 JWT,返回 payload 或 None。"""
        if _HAS_PYJWT and _pyjwt is not None:
            try:
                return _pyjwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            except Exception:
                return None
        return _decode_jwt_fallback(token, self.jwt_secret)

    @staticmethod
    def _row_to_user(row) -> User:
        """将数据库行转换为 User 模型(is_active: INTEGER -> bool)。"""
        return User(
            id=row["id"],
            email=row["email"],
            password_hash=row["password_hash"],
            created_at=row["created_at"],
            is_active=bool(row["is_active"]),
        )
