"""
DRF Views for Kalimati Price Forecasting API (SARIMAX + LightGBM ensemble).

All expected failures are raised as ForecastAPIError subclasses.
The custom_exception_handler in exceptions.py converts them to
consistent JSON error responses automatically.
"""

import logging
from pathlib import Path

from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny

from .models import ModelMetric
from .serializers import (
    ForecastRequestSerializer,
    UploadCSVSerializer,
    RetrainSerializer,
    ModelMetricSerializer,
)
from .exceptions import (
    NoDataError,
    ModelNotTrainedError,
    ForecastFailedError,
    TrainingFailedError,
    ForecastAPIError,
)

logger = logging.getLogger(__name__)

MODELS_DIR = Path(settings.MODELS_DIR)
DATA_DIR = Path(settings.DATA_DIR)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _slug(commodity: str) -> str:
    return commodity.lower().replace(" ", "_")


def _model_paths(commodity: str) -> dict:
    s = _slug(commodity)
    return {
        "sarimax": MODELS_DIR / f"{s}_sarimax.pkl",
        "lgbm": MODELS_DIR / f"{s}_lgbm.pkl",
        "weights": MODELS_DIR / f"{s}_weights.pkl",
    }


def _assert_models_exist(commodity: str):
    """Raise ModelNotTrainedError if neither model file exists on disk."""
    permission_classes = [AllowAny]
    paths = _model_paths(commodity)
    has_sarimax = paths["sarimax"].exists()
    has_lgbm = paths["lgbm"].exists()

    if not has_sarimax and not has_lgbm:
        raise ModelNotTrainedError(commodity)
    if not has_sarimax:
        logger.warning(
            "SARIMAX model missing for '%s'. Will use LightGBM only.", commodity
        )
    if not has_lgbm:
        logger.warning(
            "LightGBM model missing for '%s'. Will use SARIMAX only.", commodity
        )


def _latest_csv() -> str:
    """Return path to the most recently uploaded CSV, or raise NoDataError."""
    permission_classes = [AllowAny]
    csv_files = sorted(DATA_DIR.glob("*.csv"))
    if not csv_files:
        raise NoDataError()
    return str(csv_files[-1])


def _run_forecast(commodity: str, steps: int, model_type: str) -> dict:
    """
    Core forecast logic. Loads saved models and returns a prediction dict.

    model_type: 'sarimax' | 'lgbm' | 'ensemble'
    """
    permission_classes = [AllowAny]
    from .ml.sarimax_model import load_sarimax, forecast_sarimax
    from .ml.lgbm_model import load_lgbm, forecast_lightgbm
    from .ml.ensemble import ensemble_with_ci, load_weights, weighted_ensemble
    from .ml.preprocess import load_csv, prepare_series

    _assert_models_exist(commodity)

    paths = _model_paths(commodity)

    # Load historical series for LightGBM seeding
    csv_path = _latest_csv()
    df = load_csv(csv_path)
    series = prepare_series(df, commodity)

    # Build future date labels
    from datetime import timedelta

    last_date = series.index[-1]
    forecast_dates = [
        (last_date + timedelta(days=i + 1)).strftime("%Y-%m-%d") for i in range(steps)
    ]

    weights = load_weights(paths["weights"])

    # ── Run requested model(s) ─────────────────────────────────────────────────
    sarimax_result = None
    lgbm_preds = None

    if model_type in ("sarimax", "ensemble") and paths["sarimax"].exists():
        from .ml.sarimax_model import load_sarimax, forecast_sarimax

        sarimax_model = load_sarimax(paths["sarimax"])
        sarimax_result = forecast_sarimax(sarimax_model, steps=steps)

    if model_type in ("lgbm", "ensemble") and paths["lgbm"].exists():
        from .ml.lgbm_model import load_lgbm, forecast_lightgbm

        lgbm_model = load_lgbm(paths["lgbm"])
        lgbm_res = forecast_lightgbm(lgbm_model, series, steps=steps)
        lgbm_preds = lgbm_res["predictions"]

    # ── No model available for requested type ──────────────────────────────────
    if sarimax_result is None and lgbm_preds is None:
        raise ForecastFailedError(
            model_type,
            detail=f"No trained model file found for '{commodity}' with model='{model_type}'.",
        )

    # ── Build final prediction ─────────────────────────────────────────────────
    if model_type == "sarimax":
        if sarimax_result is None:
            raise ModelNotTrainedError(commodity, model="SARIMAX")
        preds = sarimax_result["predictions"]
        lower = sarimax_result.get("lower", preds)
        upper = sarimax_result.get("upper", preds)

    elif model_type == "lgbm":
        if lgbm_preds is None:
            raise ModelNotTrainedError(commodity, model="LightGBM")
        preds = lgbm_preds
        # LightGBM has no native CI — use ±8% spread
        lower = [round(max(0.0, p * 0.92), 2) for p in preds]
        upper = [round(p * 1.08, 2) for p in preds]

    else:  # ensemble
        if sarimax_result is not None and lgbm_preds is not None:
            result = ensemble_with_ci(sarimax_result, lgbm_preds, weights)
        elif sarimax_result is not None:
            result = sarimax_result
        else:
            result = {
                "predictions": lgbm_preds,
                "lower": [round(max(0.0, p * 0.92), 2) for p in lgbm_preds],
                "upper": [round(p * 1.08, 2) for p in lgbm_preds],
            }
        preds = result["predictions"]
        lower = result["lower"]
        upper = result["upper"]

    return {
        "commodity": commodity,
        "model": model_type,
        "steps": steps,
        "last_known_date": str(last_date.date()),
        "ensemble_weights": weights if model_type == "ensemble" else None,
        "forecast": [
            {
                "date": forecast_dates[i],
                "predicted_price": preds[i],
                "lower_bound": lower[i],
                "upper_bound": upper[i],
            }
            for i in range(steps)
        ],
        "individual_models": (
            {
                "sarimax": sarimax_result["predictions"] if sarimax_result else None,
                "lgbm": lgbm_preds,
            }
            if model_type == "ensemble"
            else None
        ),
    }


# ── Views ──────────────────────────────────────────────────────────────────────


class ForecastView(APIView):
    """
    GET /api/forecast/?commodity=Tomato&days=7&model=ensemble

    model options: sarimax | lgbm | ensemble (default)
    days range: 1–30
    """
    permission_classes = [AllowAny]
    def get(self, request):
        serializer = ForecastRequestSerializer(data=request.query_params)
        if not serializer.is_valid():
            # Serializer validation errors are caught by custom_exception_handler
            from rest_framework.exceptions import ValidationError

            raise ValidationError(serializer.errors)

        data = serializer.validated_data
        commodity = data["commodity"]
        days = data["days"]
        model = data["model"]

        logger.info(
            "Forecast request: commodity=%s days=%d model=%s", commodity, days, model
        )
        result = _run_forecast(commodity, days, model)
        return Response(result, status=status.HTTP_200_OK)


class UploadCSVView(APIView):
    """
    POST /api/upload/
    Multipart form: file=<your_kalimati.csv>
    """
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser]

    def post(self, request):
        serializer = UploadCSVSerializer(data=request.data)
        if not serializer.is_valid():
            from rest_framework.exceptions import ValidationError

            raise ValidationError(serializer.errors)

        uploaded = serializer.validated_data["file"]
        save_path = DATA_DIR / uploaded.name

        try:
            with open(save_path, "wb") as f:
                for chunk in uploaded.chunks():
                    f.write(chunk)
        except OSError as e:
            logger.error("Failed to save uploaded file: %s", e)
            raise ForecastAPIError(
                code="FILE_SAVE_ERROR",
                message="Could not save the uploaded file to disk.",
                detail=str(e),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Parse and summarise the uploaded file
        from .ml.preprocess import load_csv

        df = load_csv(str(save_path))  # raises InvalidCSVError if bad

        commodities = df["commodity"].unique().tolist()
        date_min = df["date"].min().date()
        date_max = df["date"].max().date()

        logger.info(
            "CSV uploaded: %s | %d rows | %d commodities | %s to %s",
            uploaded.name,
            len(df),
            len(commodities),
            date_min,
            date_max,
        )

        return Response(
            {
                "message": f"'{uploaded.name}' uploaded successfully.",
                "rows": len(df),
                "commodities_found": len(commodities),
                "sample_commodities": commodities[:10],
                "date_range": {
                    "from": str(date_min),
                    "to": str(date_max),
                },
                "next_step": "POST /api/retrain/ to train models.",
            },
            status=status.HTTP_201_CREATED,
        )


class RetrainView(APIView):
    """
    POST /api/retrain/
    Body: {"commodity": "Tomato"}   — train one commodity
    Body: {}                        — retrain all
    """
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = RetrainSerializer(data=request.data)
        if not serializer.is_valid():
            from rest_framework.exceptions import ValidationError

            raise ValidationError(serializer.errors)

        commodity = serializer.validated_data.get("commodity", "").strip()
        csv_path = _latest_csv()

        from .ml.train_pipeline import train_commodity, retrain_all

        if commodity:
            logger.info("Retrain requested for: %s", commodity)
            result = train_commodity(commodity, csv_path, MODELS_DIR)
            self._persist_metrics(commodity, result.get("metrics", {}))
            return Response(
                {
                    "message": f"'{commodity}' retrained successfully.",
                    "metrics": result.get("metrics"),
                    "weights": result.get("weights"),
                },
                status=status.HTTP_200_OK,
            )

        else:
            logger.info("Full retrain requested for all commodities.")
            results = retrain_all(csv_path, MODELS_DIR)
            for comm, res in results.items():
                if res.get("status") == "success":
                    self._persist_metrics(comm, res.get("metrics", {}))

            success = sum(1 for r in results.values() if r.get("status") == "success")
            return Response(
                {
                    "message": f"Retrain complete: {success}/{len(results)} commodities succeeded.",
                    "results": {
                        c: {
                            "status": r.get("status"),
                            "metrics": r.get("metrics"),
                            "error": r.get("error"),
                        }
                        for c, r in results.items()
                    },
                },
                status=status.HTTP_200_OK,
            )

    def _persist_metrics(self, commodity: str, metrics: dict):
        """Save evaluation metrics to the database."""
        for model_name, m in metrics.items():
            if isinstance(m, dict) and "error" not in m:
                ModelMetric.objects.update_or_create(
                    commodity=commodity,
                    model_name=model_name,
                    defaults={
                        "mae": m.get("mae"),
                        "rmse": m.get("rmse"),
                        "mape": m.get("mape"),
                    },
                )


class CommoditiesView(APIView):
    """
    GET /api/commodities/
    Lists all commodities that have at least one trained model on disk.
    """
    permission_classes = [AllowAny]
    def get(self, request):
        trained = set()
        for f in MODELS_DIR.glob("*_weights.pkl"):
            name = f.name.replace("_weights.pkl", "").replace("_", " ").title()
            trained.add(name)

        return Response(
            {
                "count": len(trained),
                "commodities": sorted(trained),
            }
        )


class MetricsView(APIView):
    """
    GET /api/metrics/
    GET /api/metrics/?commodity=Tomato
    """
    permission_classes = [AllowAny]
    def get(self, request):
        commodity = request.query_params.get("commodity", "").strip()
        qs = ModelMetric.objects.all().order_by("commodity", "model_name")
        if commodity:
            qs = qs.filter(commodity__iexact=commodity)
            if not qs.exists():
                raise ModelNotTrainedError(commodity)
        return Response(ModelMetricSerializer(qs, many=True).data)


class HistoryView(APIView):
    """
    GET /api/history/<commodity>/?days=30
    Returns the last N days of actual recorded prices.
    """
    permission_classes = [AllowAny]
    def get(self, request, commodity):
        days = request.query_params.get("days", "30")
        try:
            days = int(days)
            if days < 1 or days > 730:
                raise ValueError
        except ValueError:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"days": "Must be an integer between 1 and 730."})

        csv_path = _latest_csv()

        from .ml.process import load_csv, prepare_series

        df = load_csv(csv_path)
        series = prepare_series(df, commodity)
        recent = series.tail(days)

        return Response(
            {
                "commodity": commodity,
                "days": days,
                "data_points": len(recent),
                "data": [
                    {"date": str(d.date()), "price": round(float(p), 2)}
                    for d, p in zip(recent.index, recent.values)
                ],
            }
        )
