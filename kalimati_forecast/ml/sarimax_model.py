"""
SARIMAX model — weekly seasonality + Nepal festival exogenous variables.
All errors are raised as typed ForecastAPIError subclasses.
"""

import logging
import warnings
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from statsmodels.tsa.statespace.sarimax import SARIMAX

from ..exceptions import TrainingFailedError, ForecastFailedError, ModelLoadError

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)


def _build_exog(index: pd.DatetimeIndex) -> pd.DataFrame:
    """Build exogenous variable matrix (festival flag + cyclical calendar features)."""
    from .preprocess import _festival_flag

    exog = pd.DataFrame(index=index)
    exog["is_festival"] = [_festival_flag(d) for d in index]
    exog["month_sin"] = np.sin(2 * np.pi * index.month / 12)
    exog["month_cos"] = np.cos(2 * np.pi * index.month / 12)
    exog["dow_sin"] = np.sin(2 * np.pi * index.dayofweek / 7)
    exog["dow_cos"] = np.cos(2 * np.pi * index.dayofweek / 7)
    return exog.astype(float)


# Orders to try when the primary order fails
_FALLBACK_ORDERS = [
    ((1, 1, 1), (1, 1, 1, 7)),
    ((1, 1, 0), (1, 1, 0, 7)),
    ((0, 1, 1), (0, 1, 1, 7)),
    ((1, 1, 1), (0, 1, 1, 7)),
    ((2, 1, 1), (1, 1, 0, 7)),
    ((1, 1, 2), (0, 0, 1, 7)),
    ((1, 1, 1), (0, 0, 0, 0)),  # last resort — plain ARIMA
]


def fit_sarimax(series: pd.Series) -> object:
    """
    Fit SARIMAX with weekly seasonality and exogenous festival variables.
    Tries multiple (p,d,q)(P,D,Q,s) orders until one converges.

    Raises:
        TrainingFailedError — all candidate orders failed to converge
    """
    if len(series) < 50:
        raise TrainingFailedError(
            "SARIMAX", detail=f"Need at least 50 observations, got {len(series)}."
        )

    exog = _build_exog(series.index)
    errors = []

    for order, seasonal_order in _FALLBACK_ORDERS:
        try:
            logger.info("Trying SARIMAX%s x %s ...", order, seasonal_order)
            model = SARIMAX(
                series,
                exog=exog,
                order=order,
                seasonal_order=seasonal_order,
                enforce_stationarity=False,
                enforce_invertibility=False,
                trend="n",
            )
            fitted = model.fit(
                disp=False,
                maxiter=300,
                method="lbfgs",
                optim_score=None,
            )

            # Reject degenerate fits (all NaN params)
            if np.isnan(fitted.params).all():
                raise ValueError("All parameters are NaN — model did not converge.")

            logger.info(
                "SARIMAX converged: order=%s seasonal=%s AIC=%.2f",
                order,
                seasonal_order,
                fitted.aic,
            )
            return fitted

        except Exception as e:
            msg = f"order={order} seasonal={seasonal_order}: {e}"
            logger.warning("SARIMAX attempt failed — %s", msg)
            errors.append(msg)
            continue

    raise TrainingFailedError(
        "SARIMAX",
        detail="All candidate orders failed. Errors: " + " | ".join(errors[-3:]),
    )


def forecast_sarimax(fitted_model, steps: int = 7) -> dict:
    """
    Generate point forecast + 95% confidence interval.

    Returns:
        {
            'predictions': [float, ...],
            'lower':       [float, ...],
            'upper':       [float, ...],
        }

    Raises:
        ForecastFailedError — statsmodels forecast raised an exception
    """
    if steps < 1 or steps > 60:
        raise ForecastFailedError(
            "SARIMAX", detail=f"steps must be between 1 and 60, got {steps}."
        )

    try:
        last_date = fitted_model.data.orig_endog.index[-1]
        future_idx = pd.date_range(
            start=last_date + pd.Timedelta(days=1),
            periods=steps,
            freq="D",
        )
        future_exog = _build_exog(future_idx)

        forecast = fitted_model.get_forecast(steps=steps, exog=future_exog)
        pred_mean = forecast.predicted_mean.values
        conf_int = forecast.conf_int(alpha=0.05)

        # Sanity-check for NaN / Inf
        if not np.isfinite(pred_mean).all():
            nan_count = (~np.isfinite(pred_mean)).sum()
            logger.warning(
                "SARIMAX produced %d non-finite forecasts. Interpolating.", nan_count
            )
            pred_series = pd.Series(pred_mean)
            pred_mean = pred_series.interpolate(method="linear").ffill().bfill().values

        pred_mean = np.clip(pred_mean, 0, None)

        lower = np.clip(conf_int.iloc[:, 0].values, 0, None)
        upper = conf_int.iloc[:, 1].values

        return {
            "predictions": [round(float(v), 2) for v in pred_mean],
            "lower": [round(float(v), 2) for v in lower],
            "upper": [round(float(v), 2) for v in upper],
        }

    except ForecastFailedError:
        raise
    except Exception as e:
        logger.exception("SARIMAX forecast error")
        raise ForecastFailedError("SARIMAX", detail=str(e))


def save_sarimax(model, path: Path):
    try:
        joblib.dump(model, path)
        logger.info("SARIMAX model saved to %s", path)
    except Exception as e:
        logger.error("Failed to save SARIMAX model: %s", e)
        raise


def load_sarimax(path: Path):
    try:
        return joblib.load(path)
    except FileNotFoundError:
        raise ModelLoadError("SARIMAX", detail=f"File not found: {path}")
    except Exception as e:
        raise ModelLoadError("SARIMAX", detail=str(e))
