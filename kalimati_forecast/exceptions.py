"""
Centralised error handling for the Kalimati Forecasting API.

Every error returned by the API has the same shape:
{
    "error": {
        "code":    "MODEL_NOT_TRAINED",
        "message": "Human-readable explanation",
        "detail":  "Optional technical detail"
    }
}
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

# Error codes 

class ErrorCode:
    # Data errors
    NO_DATA = "NO_DATA"
    INVALID_CSV = "INVALID_CSV"
    MISSING_COLUMN = "MISSING_COLUMN"
    COMMODITY_NOT_FOUND = "COMMODITY_NOT_FOUND"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    DATE_PARSE_ERROR = "DATE_PARSE_ERROR"

    # Model errors
    MODEL_NOT_TRAINED = "MODEL_NOT_TRAINED"
    TRAINING_FAILED = "TRAINING_FAILED"
    FORECAST_FAILED = "FORECAST_FAILED"
    MODEL_LOAD_ERROR = "MODEL_LOAD_ERROR"

    # Request errors
    INVALID_PARAMS = "INVALID_PARAMS"
    MISSING_FILE = "MISSING_FILE"

    # Server errors
    INTERNAL_ERROR = "INTERNAL_ERROR"


# Custom exception classes 


class ForecastAPIError(Exception):
    """Base exception for all forecast API errors."""

    def __init__(
        self,
        code: str,
        message: str,
        detail: str = None,
        http_status: int = status.HTTP_400_BAD_REQUEST,
    ):
        self.code = code
        self.message = message
        self.detail = detail
        self.http_status = http_status
        super().__init__(message)

    def to_response(self) -> Response:
        body = {
            "error": {
                "code": self.code,
                "message": self.message,
            }
        }
        if self.detail:
            body["error"]["detail"] = self.detail
        return Response(body, status=self.http_status)


class NoDataError(ForecastAPIError):
    def __init__(self, detail: str = None):
        super().__init__(
            code=ErrorCode.NO_DATA,
            message="No CSV data found. Please upload your Kalimati dataset first via POST /api/upload/.",
            detail=detail,
            http_status=status.HTTP_404_NOT_FOUND,
        )


class InvalidCSVError(ForecastAPIError):
    def __init__(self, detail: str = None):
        super().__init__(
            code=ErrorCode.INVALID_CSV,
            message="The uploaded file could not be parsed as a valid Kalimati price CSV.",
            detail=detail,
            http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class MissingColumnError(ForecastAPIError):
    def __init__(self, column: str, available: list = None):
        detail = f"Required column '{column}' not found."
        if available:
            detail += f" Available columns: {available}"
        super().__init__(
            code=ErrorCode.MISSING_COLUMN,
            message=f"CSV is missing required column: '{column}'.",
            detail=detail,
            http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class CommodityNotFoundError(ForecastAPIError):
    def __init__(self, commodity: str, available: list = None):
        detail = f"'{commodity}' not found in data."
        if available:
            top = available[:10]
            detail += f" Available commodities: {top}"
        super().__init__(
            code=ErrorCode.COMMODITY_NOT_FOUND,
            message=f"Commodity '{commodity}' not found in the uploaded dataset.",
            detail=detail,
            http_status=status.HTTP_404_NOT_FOUND,
        )


class InsufficientDataError(ForecastAPIError):
    def __init__(self, commodity: str, got: int, need: int):
        super().__init__(
            code=ErrorCode.INSUFFICIENT_DATA,
            message=f"Not enough data to train models for '{commodity}'.",
            detail=f"Got {got} days of data. Minimum required: {need} days.",
            http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class ModelNotTrainedError(ForecastAPIError):
    def __init__(self, commodity: str, model: str = None):
        which = f"'{model}' model" if model else "Models"
        super().__init__(
            code=ErrorCode.MODEL_NOT_TRAINED,
            message=f"{which} for '{commodity}' have not been trained yet.",
            detail="Call POST /api/retrain/ with this commodity to train before forecasting.",
            http_status=status.HTTP_404_NOT_FOUND,
        )


class ModelLoadError(ForecastAPIError):
    def __init__(self, model: str, detail: str = None):
        super().__init__(
            code=ErrorCode.MODEL_LOAD_ERROR,
            message=f"Failed to load saved '{model}' model from disk.",
            detail=detail,
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class TrainingFailedError(ForecastAPIError):
    def __init__(self, model: str, detail: str = None):
        super().__init__(
            code=ErrorCode.TRAINING_FAILED,
            message=f"Training failed for the '{model}' model.",
            detail=detail,
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class ForecastFailedError(ForecastAPIError):
    def __init__(self, model: str, detail: str = None):
        super().__init__(
            code=ErrorCode.FORECAST_FAILED,
            message=f"Forecast generation failed for the '{model}' model.",
            detail=detail,
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# DRF global exception handler 


def custom_exception_handler(exc, context):
    """
    Catches ForecastAPIError globally so views don't need try/except everywhere.
    Also wraps unexpected exceptions in a consistent error shape.
    """
    if isinstance(exc, ForecastAPIError):
        logger.warning(
            "ForecastAPIError [%s]: %s | detail: %s",
            exc.code,
            exc.message,
            exc.detail,
        )
        return exc.to_response()

    # Let DRF handle its own exceptions (validation errors etc.)
    response = exception_handler(exc, context)
    if response is not None:
        original = response.data
        response.data = {
            "error": {
                "code": ErrorCode.INVALID_PARAMS,
                "message": "Invalid request parameters.",
                "detail": original,
            }
        }
        return response

    # Truly unexpected errors
    logger.exception("Unhandled exception in %s", context.get("view"))
    return Response(
        {
            "error": {
                "code": ErrorCode.INTERNAL_ERROR,
                "message": "An unexpected server error occurred.",
                "detail": str(exc) if DEBUG else None,
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


try:
    from django.conf import settings

    DEBUG = settings.DEBUG
except Exception:
    DEBUG = False
