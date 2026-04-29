"""
DRF Views for Kalimati Price Forecasting API (SARIMAX + LightGBM ensemble).

Updated:
  - _get_dataframe() replaces _latest_csv() + load_csv() everywhere.
    It queries price_predictor.DailyPriceHistory first (DB-first strategy)
    and falls back to the most recent uploaded CSV only if the DB is empty
    or unavailable.
  - train_commodity() / retrain_all() now receive a pre-loaded DataFrame
    (df=) so the DB / CSV is not hit a second time inside the pipeline.
  - MarketAnalysisView._from_db() now reads price_predictor.DailyPriceHistory
    directly instead of the local PriceRecord model.
  - _run_forecast(): each forecast step includes a `confidence` field
    derived from the CI width relative to the predicted price.
"""

import logging
from pathlib import Path

from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from payment.quota import check_and_increment_quota

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


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────


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


def _get_dataframe():
    """
    Return a cleaned price DataFrame.

    Priority:
        1. price_predictor.DailyPriceHistory (DB-first)
        2. Most recent uploaded CSV file (fallback)

    Raises:
        NoDataError — neither DB nor CSV has data.
    """
    from .ml.preprocess import load_from_db, load_csv

    # ── Primary: DB ───────────────────────────────────────────────────────
    try:
        df = load_from_db()
        logger.info("_get_dataframe: loaded %d rows from DB.", len(df))
        return df
    except Exception as db_err:
        logger.warning(
            "_get_dataframe: DB load failed (%s) — falling back to CSV.", db_err
        )

    # ── Fallback: CSV ─────────────────────────────────────────────────────
    csv_files = sorted(DATA_DIR.glob("*.csv"))
    if not csv_files:
        raise NoDataError(
            detail=(
                "price_predictor DB is empty and no CSV files found in DATA_DIR. "
                "Either run the market-price fetch endpoint or upload a CSV via POST /api/upload/."
            )
        )

    csv_path = str(csv_files[-1])
    logger.info("_get_dataframe: loading from CSV: %s", csv_path)
    return load_csv(csv_path)


def _confidence_from_ci(predicted: float, lower: float, upper: float) -> float:
    """
    Confidence score calibrated for agricultural price data.

    Reference points:
      CI width =  5% of price  → ~92% confidence  (excellent)
      CI width = 15% of price  → ~78% confidence  (good)
      CI width = 25% of price  → ~65% confidence  (acceptable)
      CI width = 40% of price  → ~50% confidence  (wide)
      CI width = 60%+ of price → ~40% confidence  (floor)
    """
    if predicted <= 0:
        return 70.0
    ci_pct = (upper - lower) / predicted * 100

    # Sigmoid-style mapping: full confidence at 5%, floor at 60%
    # confidence = 92 - (87 * (ci_pct - 5) / 55) clamped to [40, 92]
    if ci_pct <= 5:
        return 92.0
    if ci_pct >= 60:
        return 40.0
    confidence = 92.0 - (52.0 * (ci_pct - 5.0) / 55.0)
    return round(max(40.0, min(92.0, confidence)), 1)


def _run_forecast(commodity: str, steps: int, model_type: str) -> dict:
    """
    Core forecast logic. Loads saved models and returns a prediction dict.

    model_type: 'sarimax' | 'lgbm' | 'ensemble'

    Each entry in `forecast` includes:
        date, predicted_price, lower_bound, upper_bound, confidence (0-100)
    """
    from .ml.sarimax_model import load_sarimax, forecast_sarimax
    from .ml.lgbm_model import load_lgbm, forecast_lightgbm
    from .ml.ensemble import ensemble_with_ci, load_weights, weighted_ensemble
    from .ml.preprocess import prepare_series
    from datetime import timedelta

    _assert_models_exist(commodity)

    paths = _model_paths(commodity)
    df = _get_dataframe()  # DB-first, CSV fallback
    series = prepare_series(df, commodity)

    # Build future date labels
    last_date = series.index[-1]
    forecast_dates = [
        (last_date + timedelta(days=i + 1)).strftime("%Y-%m-%d") for i in range(steps)
    ]

    weights = load_weights(paths["weights"])
    sarimax_result = None
    lgbm_preds = None

    if model_type in ("sarimax", "ensemble") and paths["sarimax"].exists():
        sarimax_model = load_sarimax(paths["sarimax"])
        sarimax_result = forecast_sarimax(sarimax_model, steps=steps)

    if model_type in ("lgbm", "ensemble") and paths["lgbm"].exists():
        lgbm_model = load_lgbm(paths["lgbm"])
        lgbm_res = forecast_lightgbm(lgbm_model, series, steps=steps)
        lgbm_preds = lgbm_res["predictions"]

    if sarimax_result is None and lgbm_preds is None:
        raise ForecastFailedError(
            model_type,
            detail=f"No trained model file found for '{commodity}' with model='{model_type}'.",
        )

    # Build preds / lower / upper 
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

    # Build final response list (confidence added here)
    forecast_list = []
    for i in range(steps):
        p = preds[i]
        lo = lower[i]
        hi = upper[i]
        forecast_list.append(
            {
                "date": forecast_dates[i],
                "predicted_price": p,
                "lower_bound": lo,
                "upper_bound": hi,
                "confidence": _confidence_from_ci(p, lo, hi),
            }
        )

    return {
        "commodity": commodity,
        "model": model_type,
        "steps": steps,
        "last_known_date": str(last_date.date()),
        "ensemble_weights": weights if model_type == "ensemble" else None,
        "forecast": forecast_list,
        "individual_models": (
            {
                "sarimax": sarimax_result["predictions"] if sarimax_result else None,
                "lgbm": lgbm_preds,
            }
            if model_type == "ensemble"
            else None
        ),
    }

# Views
class ForecastView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        
        blocked = check_and_increment_quota(request.user, "price_forecast")
        if blocked:
            return blocked
        
        serializer = ForecastRequestSerializer(data=request.query_params)

        if not serializer.is_valid():
            from rest_framework.exceptions import ValidationError

            raise ValidationError(serializer.errors)

        data = serializer.validated_data
        commodity = data["commodity"]
        days = data["days"]
        model = data["model"]

        logger.info(
            "Forecast request: commodity=%s days=%d model=%s", commodity, days, model
        )

        try:
            result = _run_forecast(commodity, days, model)

            return Response(result, status=status.HTTP_200_OK)

        except ModelNotTrainedError:
            return Response(
                {"commodity": commodity, "status": "not_trained", "forecast": []},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UploadCSVView(APIView):
    """
    POST /api/upload/
    Multipart form: file=<your_kalimati.csv>

    Still supported as a manual override / one-off data import.
    The system will use the DB by default; this CSV is only used as a fallback.
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

        from .ml.preprocess import load_csv

        df = load_csv(str(save_path))
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
                "date_range": {"from": str(date_min), "to": str(date_max)},
                "note": (
                    "The system uses the price_predictor DB as primary data source. "
                    "This CSV will be used only as a fallback if the DB is unavailable."
                ),
                "next_step": "POST /api/retrain/ to train models.",
            },
            status=status.HTTP_201_CREATED,
        )


class RetrainView(APIView):
    """
    POST /api/retrain/
    Body: {"commodity": "Tomato"}  — train one commodity
    Body: {}                       — retrain all
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RetrainSerializer(data=request.data)
        if not serializer.is_valid():
            from rest_framework.exceptions import ValidationError

            raise ValidationError(serializer.errors)

        commodity = serializer.validated_data.get("commodity", "").strip()

        # Load data once here — pass it into the pipeline to avoid a second
        # DB / CSV hit inside train_commodity / retrain_all.
        df = _get_dataframe()

        from .ml.train_pipeline import train_commodity, retrain_all

        if commodity:
            logger.info("Retrain requested for: %s", commodity)
            result = train_commodity(commodity, MODELS_DIR, df=df)
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
            results = retrain_all(MODELS_DIR, df=df)
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

        return Response({"count": len(trained), "commodities": sorted(trained)})


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
    Returns the last N days of actual recorded prices (from DB or CSV).
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

        from .ml.preprocess import prepare_series

        df = _get_dataframe()  # DB-first, CSV fallback
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


class MarketAnalysisView(APIView):
    """
    GET /api/market-analysis/

    Returns today's Kalimati prices alongside yesterday's prices so the
    frontend can show the price change correctly.

    Primary: queries price_predictor.DailyPriceHistory directly.
    Fallback: reads from the most recently uploaded CSV.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        # Primary: price_predictor DB 
        try:
            return self._from_price_predictor_db()
        except Exception as e:
            logger.warning(
                "price_predictor DB market analysis failed (%s), falling back to CSV.",
                e,
            )

        # Fallback: CSV 
        try:
            return self._from_csv()
        except Exception as e:
            logger.error("CSV market analysis also failed: %s", e)
            raise ForecastAPIError(
                code="MARKET_DATA_ERROR",
                message="Could not retrieve market analysis data.",
                detail=str(e),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # DB implementation (price_predictor.DailyPriceHistory)
    def _from_price_predictor_db(self):
        from price_predictor.models import DailyPriceHistory
        from django.db.models import Max

        latest_date = DailyPriceHistory.objects.aggregate(d=Max("date"))["d"]
        if not latest_date:
            raise ValueError("No DailyPriceHistory rows in price_predictor DB.")

        today_qs = DailyPriceHistory.objects.filter(date=latest_date).select_related(
            "product"
        )

        # Previous trading day (may not be exactly yesterday if data is sparse)
        prev_date = DailyPriceHistory.objects.filter(date__lt=latest_date).aggregate(
            d=Max("date")
        )["d"]

        prev_lookup = {}
        if prev_date:
            for rec in DailyPriceHistory.objects.filter(date=prev_date).select_related(
                "product"
            ):
                prev_lookup[rec.product.commodityname] = rec.avg_price

        changes = []
        for rec in today_qs:
            name = rec.product.commodityname
            yesterday_price = prev_lookup.get(name)
            change_pct = 0.0
            trend = "stable"

            if yesterday_price and yesterday_price > 0:
                change_pct = round(
                    (rec.avg_price - yesterday_price) / yesterday_price * 100, 2
                )
                trend = (
                    "up" if change_pct > 0 else "down" if change_pct < 0 else "stable"
                )

            changes.append(
                {
                    "commodity": name,
                    "today": rec.avg_price,
                    "yesterday": yesterday_price,
                    "change_percentage": change_pct,
                    "trend": trend,
                    "unit": rec.product.commodityunit or "kg",
                }
            )

        up_count = sum(1 for c in changes if c["trend"] == "up")
        down_count = sum(1 for c in changes if c["trend"] == "down")
        market_trend = (
            "Bullish"
            if up_count > down_count
            else "Bearish" if down_count > up_count else "Neutral"
        )

        return Response(
            {
                "today": str(latest_date),
                "market_trend": market_trend,
                "changes": changes,
            }
        )

    # CSV fallback implementation
    def _from_csv(self):
        from .ml.preprocess import load_csv

        csv_files = sorted(DATA_DIR.glob("*.csv"))
        if not csv_files:
            raise NoDataError()

        df = load_csv(str(csv_files[-1]))
        dates = sorted(df["date"].unique())
        latest_date = dates[-1]
        prev_date = dates[-2] if len(dates) >= 2 else None

        today_df = df[df["date"] == latest_date]
        prev_df = df[df["date"] == prev_date] if prev_date is not None else None

        prev_lookup = {}
        if prev_df is not None:
            for _, row in prev_df.iterrows():
                prev_lookup[row["commodity"]] = row["avg_price"]

        changes = []
        for _, row in today_df.iterrows():
            yesterday_price = prev_lookup.get(row["commodity"])
            change_pct = 0.0
            trend = "stable"

            if yesterday_price and yesterday_price > 0:
                change_pct = round(
                    (row["avg_price"] - yesterday_price) / yesterday_price * 100, 2
                )
                trend = (
                    "up" if change_pct > 0 else "down" if change_pct < 0 else "stable"
                )

            changes.append(
                {
                    "commodity": row["commodity"],
                    "today": row["avg_price"],
                    "yesterday": yesterday_price,
                    "change_percentage": change_pct,
                    "trend": trend,
                    "unit": "kg",
                }
            )

        up_count = sum(1 for c in changes if c["trend"] == "up")
        down_count = sum(1 for c in changes if c["trend"] == "down")
        market_trend = (
            "Bullish"
            if up_count > down_count
            else "Bearish" if down_count > up_count else "Neutral"
        )

        return Response(
            {
                "today": str(latest_date.date()),
                "market_trend": market_trend,
                "changes": changes,
            }
        )
