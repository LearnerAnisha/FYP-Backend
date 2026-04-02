"""
Preprocessing pipeline for Kalimati market price data.
Every public function raises a typed ForecastAPIError on failure —
callers never see raw exceptions from pandas or numpy.

Updated: load_from_db() added — reads directly from
price_predictor.DailyPriceHistory instead of a CSV file.
"""

import logging
import numpy as np
import pandas as pd
from datetime import date

from ..exceptions import (
    InvalidCSVError,
    MissingColumnError,
    CommodityNotFoundError,
    InsufficientDataError,
)

logger = logging.getLogger(__name__)

# Minimum days needed to train models reliably
MIN_TRAIN_DAYS = 90

# Nepal festival calendar
NEPAL_FESTIVALS = {
    date(2023, 10, 24),
    date(2024, 10, 13),
    date(2025, 10, 2),  # Dashain
    date(2023, 11, 12),
    date(2024, 11, 1),
    date(2025, 10, 20),  # Tihar
    date(2023, 11, 19),
    date(2024, 11, 7),
    date(2025, 10, 28),  # Chhath
    date(2023, 3, 8),
    date(2024, 3, 25),
    date(2025, 3, 14),  # Holi
    date(2023, 9, 18),
    date(2024, 9, 6),
    date(2025, 8, 27),  # Teej
    date(2023, 1, 15),
    date(2024, 1, 15),
    date(2025, 1, 15),  # Maghe Sankranti
}


def _festival_flag(d) -> int:
    """Return 1 if date is within 5 days of a major Nepal festival."""
    try:
        target = d.date() if hasattr(d, "date") else d
        return int(any(abs((target - f).days) <= 5 for f in NEPAL_FESTIVALS))
    except Exception:
        return 0


# Column name aliases (handles various Kalimati CSV formats)
_COL_ALIASES = {
    "commodity_name": "commodity",
    "commodity name": "commodity",
    "item": "commodity",
    "name": "commodity",
    "minimum": "min_price",
    "min": "min_price",
    "maximum": "max_price",
    "max": "max_price",
    "average": "avg_price",
    "avg": "avg_price",
    "price": "avg_price",
}

REQUIRED_COLUMNS = ["commodity", "avg_price"]

# Data loading

def load_from_db() -> pd.DataFrame:
    """
    Load Kalimati price history directly from
    price_predictor.DailyPriceHistory (Django ORM).

    Returns a DataFrame with the same schema as load_csv():
        commodity  : str
        date       : datetime64
        avg_price  : float
        min_price  : float
        max_price  : float

    This means prepare_series(), build_features(), and the entire
    training pipeline work without any further changes.

    Raises:
        InvalidCSVError — DB is empty, app not installed, or query failed.
    """
    try:
        from price_predictor.models import DailyPriceHistory
    except ImportError as e:
        raise InvalidCSVError(
            detail=(
                f"Cannot import price_predictor models: {e}. "
                "Ensure 'price_predictor' is listed in INSTALLED_APPS."
            )
        )

    try:
        qs = (
            DailyPriceHistory.objects.select_related("product")
            .values(
                "date",
                "avg_price",
                "min_price",
                "max_price",
                commodity=_F("product__commodityname"),
            )
            .order_by("date")
        )

        if not qs.exists():
            raise InvalidCSVError(
                detail=(
                    "price_predictor.DailyPriceHistory is empty. "
                    "Run the Kalimati market-price fetch endpoint first."
                )
            )

        df = pd.DataFrame.from_records(list(qs))

    except InvalidCSVError:
        raise
    except Exception as e:
        raise InvalidCSVError(detail=f"Database read failed: {e}")

    # Normalise

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    bad_dates = df["date"].isna().sum()
    if bad_dates == len(df):
        raise InvalidCSVError(
            detail="Every row has an unparseable date in DailyPriceHistory."
        )
    if bad_dates > 0:
        logger.warning("Dropped %d rows with unparseable dates from DB.", bad_dates)
        df = df.dropna(subset=["date"])

    df["avg_price"] = pd.to_numeric(df["avg_price"], errors="coerce")
    bad_prices = df["avg_price"].isna().sum()
    if bad_prices == len(df):
        raise InvalidCSVError(
            detail="avg_price column has no numeric values in DailyPriceHistory."
        )
    if bad_prices > 0:
        logger.warning(
            "Dropped %d rows with non-numeric avg_price from DB.", bad_prices
        )
        df = df.dropna(subset=["avg_price"])

    invalid_prices = (df["avg_price"] <= 0).sum()
    if invalid_prices > 0:
        logger.warning(
            "Dropped %d rows with zero/negative prices from DB.", invalid_prices
        )
        df = df[df["avg_price"] > 0]

    if df.empty:
        raise InvalidCSVError(
            detail="No valid rows remain in DailyPriceHistory after cleaning."
        )

    df["commodity"] = df["commodity"].astype(str).str.strip()
    df = df.sort_values("date").reset_index(drop=True)

    logger.info(
        "Loaded from DB: %d rows, %d commodities, %s → %s",
        len(df),
        df["commodity"].nunique(),
        df["date"].min().date(),
        df["date"].max().date(),
    )
    return df


def load_csv(filepath: str) -> pd.DataFrame:
    """
    Load and validate a Kalimati price CSV.

    Raises:
        InvalidCSVError  — file cannot be read or is empty
        MissingColumnError — required column not found after alias resolution
    """
    try:
        df = pd.read_csv(filepath, encoding="utf-8", on_bad_lines="skip")
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(filepath, encoding="latin-1", on_bad_lines="skip")
        except Exception as e:
            raise InvalidCSVError(detail=f"Cannot decode file: {e}")
    except FileNotFoundError:
        raise InvalidCSVError(detail=f"File not found: {filepath}")
    except Exception as e:
        raise InvalidCSVError(detail=str(e))

    if df.empty:
        raise InvalidCSVError(detail="The CSV file is empty.")

    # Normalise column names
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
        .str.replace("_", " ")
    )
    df = df.rename(columns=_COL_ALIASES)
    df.columns = df.columns.str.replace(" ", "_")

    # Detect date column
    date_col = next((c for c in df.columns if "date" in c), None)
    if date_col is None:
        raise MissingColumnError("date", available=df.columns.tolist())

    df = df.rename(columns={date_col: "date"})

    # Validate required columns
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            raise MissingColumnError(col, available=df.columns.tolist())

    # Parse dates
    try:
        df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    except Exception as e:
        raise InvalidCSVError(detail=f"Date column could not be parsed: {e}")

    bad_dates = df["date"].isna().sum()
    if bad_dates == len(df):
        raise InvalidCSVError(detail="Every row has an unparseable date.")
    if bad_dates > 0:
        logger.warning("Dropped %d rows with unparseable dates.", bad_dates)
        df = df.dropna(subset=["date"])

    # Parse prices
    df["avg_price"] = pd.to_numeric(df["avg_price"], errors="coerce")
    bad_prices = df["avg_price"].isna().sum()
    if bad_prices == len(df):
        raise InvalidCSVError(detail="avg_price column has no numeric values.")
    if bad_prices > 0:
        logger.warning("Dropped %d rows with non-numeric avg_price.", bad_prices)
        df = df.dropna(subset=["avg_price"])

    # Drop zero/negative prices
    invalid_prices = (df["avg_price"] <= 0).sum()
    if invalid_prices > 0:
        logger.warning("Dropped %d rows with zero/negative prices.", invalid_prices)
        df = df[df["avg_price"] > 0]

    if df.empty:
        raise InvalidCSVError(detail="No valid rows remain after cleaning.")

    df["commodity"] = df["commodity"].astype(str).str.strip()
    df = df.sort_values("date").reset_index(drop=True)

    logger.info(
        "Loaded CSV: %d rows, %d commodities, date range %s to %s",
        len(df),
        df["commodity"].nunique(),
        df["date"].min().date(),
        df["date"].max().date(),
    )
    return df

# Series preparation

def prepare_series(df: pd.DataFrame, commodity: str) -> pd.Series:
    """
    Extract a clean daily price series for one commodity.

    Raises:
        CommodityNotFoundError  — commodity not in dataset
        InsufficientDataError   — fewer than MIN_TRAIN_DAYS rows
    """
    available = df["commodity"].unique().tolist()
    matches = df[df["commodity"].str.lower() == commodity.strip().lower()]

    if matches.empty:
        # Try partial match
        partial = df[
            df["commodity"]
            .str.lower()
            .str.contains(commodity.strip().lower(), na=False)
        ]
        if partial.empty:
            raise CommodityNotFoundError(commodity, available=available)
        commodity = partial["commodity"].iloc[0]
        matches = partial
        logger.info("Partial match: '%s' resolved to '%s'", commodity, commodity)

    sub = matches.set_index("date")[["avg_price"]]
    sub = sub[~sub.index.duplicated(keep="last")]

    # Fill daily gaps (forward-fill up to 3 consecutive missing days)
    full_idx = pd.date_range(sub.index.min(), sub.index.max(), freq="D")
    sub = sub.reindex(full_idx)
    filled = sub["avg_price"].isna().sum()
    sub["avg_price"] = sub["avg_price"].ffill(limit=3)

    # Drop rows that couldn't be filled (gaps > 3 days)
    sub = sub.dropna()

    if filled > 0:
        logger.info("Forward-filled %d missing days for '%s'.", filled, commodity)

    n = len(sub)
    if n < MIN_TRAIN_DAYS:
        raise InsufficientDataError(commodity, got=n, need=MIN_TRAIN_DAYS)

    return sub["avg_price"].rename("avg_price")

# Feature engineering

def build_features(series: pd.Series) -> pd.DataFrame:
    """
    Build feature matrix for LightGBM.
    All lag/rolling features shift by 1 to prevent data leakage.

    Returns DataFrame with features + 'avg_price' target column.
    """
    df = series.to_frame()

    # Lag features
    for lag in [1, 2, 3, 7, 14, 21, 30]:
        df[f"lag_{lag}"] = df["avg_price"].shift(lag)

    # Rolling statistics (shifted to avoid leakage)
    for win in [7, 14, 30]:
        base = df["avg_price"].shift(1)
        df[f"roll_mean_{win}"] = base.rolling(win).mean()
        df[f"roll_std_{win}"] = base.rolling(win).std().fillna(0)
        df[f"roll_min_{win}"] = base.rolling(win).min()
        df[f"roll_max_{win}"] = base.rolling(win).max()

    # Exponential weighted mean
    df["ewm_7"] = df["avg_price"].shift(1).ewm(span=7, min_periods=3).mean()
    df["ewm_14"] = df["avg_price"].shift(1).ewm(span=14, min_periods=7).mean()

    # Calendar features
    df["dayofweek"] = df.index.dayofweek
    df["month"] = df.index.month
    df["quarter"] = df.index.quarter
    df["weekofyear"] = df.index.isocalendar().week.astype(int)
    df["is_weekend"] = (df.index.dayofweek >= 5).astype(int)

    # Nepal festival flag
    df["is_festival"] = [_festival_flag(d) for d in df.index]

    # Price momentum (percentage change, clipped to ±100%)
    df["pct_change_7"] = df["avg_price"].pct_change(7).shift(1).clip(-1, 1).fillna(0)
    df["pct_change_30"] = df["avg_price"].pct_change(30).shift(1).clip(-1, 1).fillna(0)

    return df.dropna()


def get_feature_columns() -> list:
    cols = []
    for lag in [1, 2, 3, 7, 14, 21, 30]:
        cols.append(f"lag_{lag}")
    for win in [7, 14, 30]:
        cols += [
            f"roll_mean_{win}",
            f"roll_std_{win}",
            f"roll_min_{win}",
            f"roll_max_{win}",
        ]
    cols += [
        "ewm_7",
        "ewm_14",
        "dayofweek",
        "month",
        "quarter",
        "weekofyear",
        "is_weekend",
        "is_festival",
        "pct_change_7",
        "pct_change_30",
    ]
    return cols


def train_test_split_ts(series: pd.Series, test_days: int = 60):
    """Time-aware split — last `test_days` are held out for evaluation."""
    if len(series) < test_days + MIN_TRAIN_DAYS:
        test_days = max(14, len(series) // 5)
        logger.warning("Short dataset: reducing test window to %d days.", test_days)
    train = series.iloc[:-test_days]
    test = series.iloc[-test_days:]
    return train, test


def evaluate_metrics(y_true, y_pred) -> dict:
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)

    if len(y_true) == 0 or len(y_pred) == 0:
        return {"mae": None, "rmse": None, "mape": None}

    mae = float(np.mean(np.abs(y_true - y_pred)))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

    nonzero = y_true != 0
    mape = (
        float(
            np.mean(np.abs((y_true[nonzero] - y_pred[nonzero]) / y_true[nonzero])) * 100
        )
        if nonzero.any()
        else None
    )

    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "mape": round(mape, 4) if mape is not None else None,
    }

# Internal alias so load_from_db() can use F() without a top-level ORM import
def _F(field):
    """Lazy wrapper around django.db.models.F to avoid import at module load."""
    from django.db.models import F

    return F(field)
