"""
eSewa Utility Functions
Handles HMAC-SHA256 signature generation and payment verification.
"""

import hmac
import hashlib
import base64
import json
import logging
import requests

from django.conf import settings

logger = logging.getLogger(__name__)


# ─── SIGNATURE HELPERS ────────────────────────────────────────────────────────

def generate_esewa_signature(total_amount: str, transaction_uuid: str, product_code: str) -> str:
    """
    Generate HMAC-SHA256 signature for eSewa payment initiation.

    The message format MUST be exactly:
        total_amount={total_amount},transaction_uuid={uuid},product_code={code}

    Args:
        total_amount    : Total payment amount as string (e.g. "1500.00")
        transaction_uuid: Unique transaction identifier
        product_code    : eSewa merchant product code

    Returns:
        Base64-encoded HMAC-SHA256 signature string
    """
    message = (
        f"total_amount={total_amount},"
        f"transaction_uuid={transaction_uuid},"
        f"product_code={product_code}"
    )
    secret    = settings.ESEWA_SECRET_KEY.encode("utf-8")
    msg_bytes = message.encode("utf-8")
    raw_sig   = hmac.new(secret, msg_bytes, hashlib.sha256).digest()
    signature = base64.b64encode(raw_sig).decode("utf-8")

    logger.debug("Generated signature for txn=%s", transaction_uuid)
    return signature

def verify_esewa_signature(data_string: str, received_signature: str) -> bool:
    """
    Verify the HMAC-SHA256 signature from eSewa callback.
    """

    secret = settings.ESEWA_SECRET_KEY.encode("utf-8")

    raw_sig = hmac.new(
        secret,
        data_string.encode("utf-8"),
        hashlib.sha256
    ).digest()

    calculated_signature = base64.b64encode(raw_sig).decode("utf-8")

    is_valid = hmac.compare_digest(calculated_signature, received_signature)

    if not is_valid:
        logger.warning(
            "Signature mismatch | expected=%s | received=%s",
            calculated_signature,
            received_signature
        )

    return is_valid

# ─── DECODE ESEWA CALLBACK DATA ───────────────────────────────────────────────

def decode_esewa_response(encoded_data: str) -> dict:
    """
    Decode the base64-encoded JSON data sent by eSewa in the success callback.

    eSewa sends: GET /success/?data=<base64_encoded_json>

    Args:
        encoded_data: Base64-encoded string from eSewa

    Returns:
        Decoded dict with keys: transaction_uuid, total_amount, product_code, signature, status, ref_id, etc.

    Raises:
        ValueError: If decoding or JSON parsing fails
    """
    try:
        decoded_bytes = base64.b64decode(encoded_data)
        decoded_str   = decoded_bytes.decode("utf-8")
        data          = json.loads(decoded_str)
        logger.debug("Decoded eSewa response: %s", data)
        return data
    except (base64.binascii.Error, UnicodeDecodeError) as e:
        logger.error("Base64 decode failed: %s", str(e))
        raise ValueError("Invalid base64 encoding in eSewa response.")
    except json.JSONDecodeError as e:
        logger.error("JSON parse failed: %s", str(e))
        raise ValueError("Invalid JSON in eSewa response data.")


# ─── VERIFY WITH ESEWA STATUS API ────────────────────────────────────────────

def verify_payment_with_esewa(transaction_uuid: str, total_amount: str) -> dict:
    """
    Verify a payment's status directly with eSewa's transaction status API.

    This is the CRITICAL server-side verification step — never trust only
    the callback data. Always verify with eSewa's API.

    API Endpoint:
        GET {ESEWA_BASE_URL}/api/epay/transaction/status/
        Params: product_code, transaction_uuid, total_amount

    Args:
        transaction_uuid: The transaction UUID to verify
        total_amount    : Expected total amount

    Returns:
        Dict with eSewa status response (contains: status, ref_id, etc.)

    Raises:
        requests.RequestException : Network or timeout errors
        ValueError                : Unexpected response format
    """
    verify_url = f"{settings.ESEWA_BASE_URL}/api/epay/transaction/status/"
    params = {
        "product_code"    : settings.ESEWA_PRODUCT_CODE,
        "transaction_uuid": transaction_uuid,
        "total_amount"    : total_amount,
    }

    logger.info("Verifying payment with eSewa API | txn=%s", transaction_uuid)

    try:
        response = requests.get(
            verify_url,
            params=params,
            timeout=15,  # 15 second timeout
        )
        response.raise_for_status()
        data = response.json()
        logger.info("eSewa verification response | txn=%s | status=%s", transaction_uuid, data.get("status"))
        return data

    except requests.Timeout:
        logger.error("eSewa verification timed out | txn=%s", transaction_uuid)
        raise requests.RequestException("eSewa verification API timed out. Please try again.")

    except requests.ConnectionError:
        logger.error("Cannot connect to eSewa API | txn=%s", transaction_uuid)
        raise requests.RequestException("Unable to connect to eSewa servers. Check your internet.")

    except requests.HTTPError as e:
        logger.error("eSewa API HTTP error %s | txn=%s", response.status_code, transaction_uuid)
        raise requests.RequestException(f"eSewa API returned error {response.status_code}.")

    except (ValueError, KeyError) as e:
        logger.error("eSewa API returned invalid JSON | txn=%s", transaction_uuid)
        raise ValueError("Invalid response from eSewa verification API.")
