import os
import time

from fastapi import HTTPException
import nacl.signing
import nacl.exceptions

from agno.utils.log import log_error

DISCORD_PUBLIC_KEY = os.getenv("DISCORD_PUBLIC_KEY")
if not DISCORD_PUBLIC_KEY:
    log_error("DISCORD_PUBLIC_KEY is not set in environment variables.")


def verify_discord_signature(body: bytes, signature: str, timestamp: str) -> bool:
    if not DISCORD_PUBLIC_KEY:
        raise HTTPException(status_code=500, detail="DISCORD_PUBLIC_KEY is not set")
    
    # Validate timestamp (allow a 5-minute tolerance to prevent replay attacks)
    current_time = int(time.time())
    try:
        req_timestamp = int(timestamp)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid timestamp format")

    if abs(current_time - req_timestamp) > 60 * 5:
        return False

    try:
        verify_key = nacl.signing.VerifyKey(bytes.fromhex(DISCORD_PUBLIC_KEY))
    except Exception as e:
        log_error(f"Invalid Discord public key: {e}")
        raise HTTPException(status_code=500, detail="Invalid Discord public key")

    message = timestamp.encode() + body
    try:
        verify_key.verify(message, bytes.fromhex(signature))
        return True
    except nacl.exceptions.BadSignatureError:
        return False