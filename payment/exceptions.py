"""
Custom Exception Handler & Error Codes for eSewa Payment API

All API errors return a consistent JSON structure:
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Human readable message.",
        "details": { ... }   # optional extra context
    }
}
"""

import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


# ─── ERROR CODES ──────────────────────────────────────────────────────────────

class EsewaErrorCode:
    # Validation errors
    VALIDATION_ERROR       = "VALIDATION_ERROR"
    INVALID_AMOUNT         = "INVALID_AMOUNT"
    AMOUNT_TOO_LOW         = "AMOUNT_TOO_LOW"
    AMOUNT_TOO_HIGH        = "AMOUNT_TOO_HIGH"

    # Payment state errors
    PAYMENT_NOT_FOUND      = "PAYMENT_NOT_FOUND"
    PAYMENT_ALREADY_DONE   = "PAYMENT_ALREADY_DONE"

    # eSewa callback errors
    MISSING_CALLBACK_DATA  = "MISSING_CALLBACK_DATA"
    INVALID_CALLBACK_DATA  = "INVALID_CALLBACK_DATA"
    SIGNATURE_MISMATCH     = "SIGNATURE_MISMATCH"
    TRANSACTION_NOT_FOUND  = "TRANSACTION_NOT_FOUND"

    # eSewa API errors
    ESEWA_API_TIMEOUT      = "ESEWA_API_TIMEOUT"
    ESEWA_API_UNREACHABLE  = "ESEWA_API_UNREACHABLE"
    ESEWA_API_ERROR        = "ESEWA_API_ERROR"
    PAYMENT_NOT_COMPLETE   = "PAYMENT_NOT_COMPLETE"
    PAYMENT_FAILED         = "PAYMENT_FAILED"

    # Server errors
    INTERNAL_ERROR         = "INTERNAL_ERROR"


# ─── CUSTOM EXCEPTION CLASSES ────────────────────────────────────────────────

class PaymentAPIError(Exception):
    """Base class for all payment-related API errors."""
    code        = EsewaErrorCode.INTERNAL_ERROR
    message     = "An unexpected error occurred."
    http_status = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message=None, details=None):
        self.message = message or self.__class__.message
        self.details = details or {}
        super().__init__(self.message)

    def to_response(self):
        body = {
            "error": {
                "code"   : self.code,
                "message": self.message,
            }
        }
        if self.details:
            body["error"]["details"] = self.details
        return Response(body, status=self.http_status)


class ValidationError(PaymentAPIError):
    code        = EsewaErrorCode.VALIDATION_ERROR
    http_status = status.HTTP_400_BAD_REQUEST


class PaymentNotFoundError(PaymentAPIError):
    code        = EsewaErrorCode.PAYMENT_NOT_FOUND
    message     = "Payment record not found."
    http_status = status.HTTP_404_NOT_FOUND


class PaymentAlreadyProcessedError(PaymentAPIError):
    code        = EsewaErrorCode.PAYMENT_ALREADY_DONE
    message     = "This payment has already been processed."
    http_status = status.HTTP_409_CONFLICT


class MissingCallbackDataError(PaymentAPIError):
    code        = EsewaErrorCode.MISSING_CALLBACK_DATA
    message     = "No callback data received from eSewa. The 'data' query parameter is required."
    http_status = status.HTTP_400_BAD_REQUEST


class InvalidCallbackDataError(PaymentAPIError):
    code        = EsewaErrorCode.INVALID_CALLBACK_DATA
    message     = "The callback data from eSewa could not be decoded. It may be malformed."
    http_status = status.HTTP_400_BAD_REQUEST


class SignatureMismatchError(PaymentAPIError):
    code        = EsewaErrorCode.SIGNATURE_MISMATCH
    message     = "Payment signature verification failed. This request may have been tampered with."
    http_status = status.HTTP_400_BAD_REQUEST


class TransactionNotFoundError(PaymentAPIError):
    code        = EsewaErrorCode.TRANSACTION_NOT_FOUND
    message     = "No matching transaction found for the provided UUID."
    http_status = status.HTTP_404_NOT_FOUND


class EsewaAPITimeoutError(PaymentAPIError):
    code        = EsewaErrorCode.ESEWA_API_TIMEOUT
    message     = "eSewa verification API timed out. Please check your eSewa app for transaction status."
    http_status = status.HTTP_504_GATEWAY_TIMEOUT


class EsewaAPIUnreachableError(PaymentAPIError):
    code        = EsewaErrorCode.ESEWA_API_UNREACHABLE
    message     = "Unable to reach eSewa servers. Please try again shortly."
    http_status = status.HTTP_502_BAD_GATEWAY


class EsewaAPIError(PaymentAPIError):
    code        = EsewaErrorCode.ESEWA_API_ERROR
    http_status = status.HTTP_502_BAD_GATEWAY


class PaymentNotCompleteError(PaymentAPIError):
    code        = EsewaErrorCode.PAYMENT_NOT_COMPLETE
    http_status = status.HTTP_402_PAYMENT_REQUIRED


class PaymentFailedError(PaymentAPIError):
    code        = EsewaErrorCode.PAYMENT_FAILED
    message     = "Payment was not completed successfully."
    http_status = status.HTTP_402_PAYMENT_REQUIRED


# ─── GLOBAL DRF EXCEPTION HANDLER ────────────────────────────────────────────

def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler.
    Converts all errors into a consistent JSON format.
    """
    # Handle our custom PaymentAPIError subclasses
    if isinstance(exc, PaymentAPIError):
        logger.warning(
            "PaymentAPIError | code=%s | msg=%s | view=%s",
            exc.code, exc.message, context["view"].__class__.__name__
        )
        return exc.to_response()

    # Let DRF handle its built-in exceptions first
    response = exception_handler(exc, context)

    if response is not None:
        # Reformat DRF's default error response
        original_data = response.data
        formatted = {
            "error": {
                "code"   : EsewaErrorCode.VALIDATION_ERROR,
                "message": "Request validation failed.",
                "details": original_data,
            }
        }
        response.data = formatted
        return response

    # Catch-all for unhandled exceptions
    logger.exception("Unhandled exception in view=%s", context["view"].__class__.__name__)
    return Response(
        {
            "error": {
                "code"   : EsewaErrorCode.INTERNAL_ERROR,
                "message": "An internal server error occurred. Please try again later.",
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
