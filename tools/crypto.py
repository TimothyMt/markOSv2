"""Token encryption utils — Fernet symmetric encryption.

ENCRYPTION_KEY env var = Fernet 32-byte key (base64 encoded).
Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Lý do: FB access tokens KHÔNG được lưu plain text trong DB.
Nếu DB bị compromise → attacker chỉ có cipher text, không dùng được.
"""
import logging
from config import ENCRYPTION_KEY

logger = logging.getLogger(__name__)


def _get_fernet():
    from cryptography.fernet import Fernet, InvalidToken  # noqa
    if not ENCRYPTION_KEY:
        raise RuntimeError(
            "ENCRYPTION_KEY chưa set. "
            "Chạy: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\" "
            "rồi set vào env var."
        )
    return Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)


def encrypt_token(token: str) -> str:
    """Encrypt FB access token trước khi lưu DB."""
    return _get_fernet().encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    """Decrypt token lấy ra từ DB. Raise nếu key sai hoặc data hỏng."""
    from cryptography.fernet import InvalidToken
    try:
        return _get_fernet().decrypt(encrypted.encode()).decode()
    except InvalidToken:
        raise ValueError("Token decrypt thất bại — key sai hoặc data corrupt")
