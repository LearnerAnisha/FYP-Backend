"""
Ensemble: SARIMAX + LightGBM weighted combination.
Weights are optimised per commodity by minimising MAE on the validation set.
"""

import logging
import numpy as np
import joblib
from pathlib import Path
from scipy.optimize import minimize

from ..exceptions import ForecastFailedError

logger = logging.getLogger(__name__)

DEFAULT_WEIGHTS = {"sarimax": 0.55, "lgbm": 0.45}


def weighted_ensemble(
    sarimax_preds: list,
    lgbm_preds: list,
    weights: dict = None,
) -> list:
    """
    Combine SARIMAX and LightGBM forecasts using weighted average.

    Args:
        sarimax_preds: Point predictions from SARIMAX.
        lgbm_preds:    Point predictions from LightGBM.
        weights:       Dict {'sarimax': w1, 'lgbm': w2}. Must sum to 1.

    Returns:
        List of ensemble predictions.

    Raises:
        ForecastFailedError — mismatched prediction lengths
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    n_sarimax = len(sarimax_preds)
    n_lgbm = len(lgbm_preds)
    if n_sarimax != n_lgbm:
        raise ForecastFailedError(
            "ensemble",
            detail=f"Prediction length mismatch: SARIMAX={n_sarimax}, LightGBM={n_lgbm}.",
        )

    ws = weights.get("sarimax", 0.55)
    wl = weights.get("lgbm", 0.45)
    total = ws + wl
    if total == 0:
        raise ForecastFailedError("ensemble", detail="Ensemble weights sum to zero.")
    ws, wl = ws / total, wl / total

    combined = [
        ws * float(sarimax_preds[i]) + wl * float(lgbm_preds[i])
        for i in range(n_sarimax)
    ]
    return [round(max(0.0, v), 2) for v in combined]


def optimize_weights(
    sarimax_val: np.ndarray,
    lgbm_val: np.ndarray,
    y_true: np.ndarray,
) -> dict:
    """
    Find optimal ensemble weights by minimising MAE on the validation set.

    Falls back to DEFAULT_WEIGHTS if optimisation fails.
    """

    def mae_loss(w):
        w = np.clip(w, 0, 1)
        total = w.sum()
        if total == 0:
            return 1e9
        w = w / total
        ensemble = w[0] * sarimax_val + w[1] * lgbm_val
        return float(np.mean(np.abs(y_true - ensemble)))

    try:
        constraints = {"type": "eq", "fun": lambda w: w.sum() - 1}
        bounds = [(0.0, 1.0)] * 2
        init = np.array([0.5, 0.5])

        result = minimize(
            mae_loss,
            init,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-6, "maxiter": 200},
        )

        if not result.success:
            logger.warning(
                "Weight optimisation did not fully converge: %s", result.message
            )

        w = np.clip(result.x, 0, 1)
        w = w / w.sum()

        optimised = {
            "sarimax": round(float(w[0]), 4),
            "lgbm": round(float(w[1]), 4),
        }
        logger.info("Optimised weights: %s", optimised)
        return optimised

    except Exception as e:
        logger.warning("Weight optimisation failed (%s). Using defaults.", e)
        return DEFAULT_WEIGHTS.copy()


def ensemble_with_ci(
    sarimax_result: dict,
    lgbm_preds: list,
    weights: dict = None,
) -> dict:
    preds = weighted_ensemble(
        sarimax_result["predictions"],
        lgbm_preds,
        weights,
    )

    lower_list = sarimax_result.get("lower", sarimax_result["predictions"])
    upper_list = sarimax_result.get("upper", sarimax_result["predictions"])

    lower, upper = [], []
    steps = len(preds)

    for i, p in enumerate(preds):
        s_pred = float(sarimax_result["predictions"][i])
        l_pred = float(lgbm_preds[i])

        # Base CI half-width from SARIMAX — cap at 15% of predicted price
        ci_half_lo = min(s_pred - float(lower_list[i]), p * 0.15)
        ci_half_hi = min(float(upper_list[i]) - s_pred, p * 0.15)

        # Disagreement contribution decays over forecast horizon
        # Step 1 = full disagreement, step 7 = 40% of disagreement
        decay = max(0.4, 1.0 - (i / steps) * 0.6)
        disagreement = abs(s_pred - l_pred) * 0.25 * decay

        lower.append(round(max(0.0, p - ci_half_lo - disagreement), 2))
        upper.append(round(p + ci_half_hi + disagreement, 2))

    return {
        "predictions": preds,
        "lower": lower,
        "upper": upper,
    }


def save_weights(weights: dict, path: Path):
    try:
        joblib.dump(weights, path)
    except Exception as e:
        logger.error("Failed to save weights to %s: %s", path, e)


def load_weights(path: Path) -> dict:
    try:
        return joblib.load(path)
    except FileNotFoundError:
        logger.info("No saved weights at %s — using defaults.", path)
        return DEFAULT_WEIGHTS.copy()
    except Exception as e:
        logger.warning("Could not load weights (%s) — using defaults.", e)
        return DEFAULT_WEIGHTS.copy()
