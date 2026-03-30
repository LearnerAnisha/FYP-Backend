"""
Training pipeline: SARIMAX + LightGBM ensemble for Kalimati price forecasting.

Usage:
    python forecast/ml/train_pipeline.py data/kalimati.csv Tomato
    python forecast/ml/train_pipeline.py data/kalimati.csv          # trains all
"""

import logging
import sys
import os
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


def _model_paths(commodity: str, models_dir: Path) -> dict:
    slug = commodity.lower().replace(" ", "_")
    return {
        "sarimax": models_dir / f"{slug}_sarimax.pkl",
        "lgbm": models_dir / f"{slug}_lgbm.pkl",
        "weights": models_dir / f"{slug}_weights.pkl",
    }


def train_commodity(
    commodity: str,
    csv_path: str,
    models_dir: Path,
    test_days: int = 60,
) -> dict:
    """
    Full training pipeline for one commodity.

    Steps:
        1. Load and validate CSV
        2. Prepare daily series (clean, fill gaps)
        3. Train/test split (last 60 days held out)
        4. Fit SARIMAX
        5. Fit LightGBM
        6. Evaluate both models on test set
        7. Optimise ensemble weights
        8. Save models + weights to disk

    Returns:
        Dict with status and metrics per model.

    Raises:
        ForecastAPIError subclasses for all recoverable failures.
    """
    from .preprocess import (
        load_csv,
        prepare_series,
        build_features,
        train_test_split_ts,
        evaluate_metrics,
    )
    from .sarimax_model import fit_sarimax, forecast_sarimax, save_sarimax
    from .lgbm_model import fit_lightgbm, forecast_lightgbm, save_lgbm
    from .ensemble import optimize_weights, save_weights
    from ..exceptions import TrainingFailedError

    print(f"\n{'='*60}")
    print(f"  Training: {commodity.upper()}")
    print(f"{'='*60}")

    # 1. Load data 
    df = load_csv(csv_path)  # raises InvalidCSVError if bad
    series = prepare_series(
        df, commodity
    )  # raises CommodityNotFoundError / InsufficientDataError

    print(
        f"  Data: {series.index[0].date()} → {series.index[-1].date()} ({len(series)} days)"
    )

    # 2. Train / test split
    train_series, test_series = train_test_split_ts(series, test_days=test_days)
    print(f"  Split: {len(train_series)} train / {len(test_series)} test days")

    models_dir.mkdir(parents=True, exist_ok=True)
    paths = _model_paths(commodity, models_dir)
    metrics = {}
    sarimax_model = None
    lgbm_model = None

    # 3. Fit SARIMAX 
    print("\n  [1/2] Fitting SARIMAX ...")
    try:
        sarimax_model = fit_sarimax(train_series)
        sarimax_res = forecast_sarimax(sarimax_model, steps=len(test_series))
        sarimax_preds = np.array(sarimax_res["predictions"])
        metrics["sarimax"] = evaluate_metrics(test_series.values, sarimax_preds)
        print(
            f"        MAE={metrics['sarimax']['mae']:.2f}  "
            f"RMSE={metrics['sarimax']['rmse']:.2f}  "
            f"MAPE={metrics['sarimax']['mape']:.2f}%"
        )
        save_sarimax(sarimax_model, paths["sarimax"])

    except Exception as e:
        print(f"        SARIMAX FAILED: {e}")
        logger.error("SARIMAX training failed for '%s': %s", commodity, e)
        metrics["sarimax"] = {"error": str(e)}
        sarimax_preds = None

    #  4. Fit LightGBM 
    print("  [2/2] Fitting LightGBM ...")
    try:
        feature_df = build_features(train_series)
        lgbm_model = fit_lightgbm(feature_df)
        lgbm_res = forecast_lightgbm(lgbm_model, train_series, steps=len(test_series))
        lgbm_preds = np.array(lgbm_res["predictions"])
        metrics["lgbm"] = evaluate_metrics(test_series.values, lgbm_preds)
        print(
            f"        MAE={metrics['lgbm']['mae']:.2f}  "
            f"RMSE={metrics['lgbm']['rmse']:.2f}  "
            f"MAPE={metrics['lgbm']['mape']:.2f}%"
        )
        save_lgbm(lgbm_model, paths["lgbm"])

    except Exception as e:
        print(f"        LightGBM FAILED: {e}")
        logger.error("LightGBM training failed for '%s': %s", commodity, e)
        metrics["lgbm"] = {"error": str(e)}
        lgbm_preds = None

    #  5. Both models failed 
    if sarimax_preds is None and lgbm_preds is None:
        raise TrainingFailedError(
            "ensemble",
            detail=f"Both SARIMAX and LightGBM failed for '{commodity}'. "
            "Check data quality and logs for details.",
        )

    # 6. Ensemble weights 
    if sarimax_preds is not None and lgbm_preds is not None:
        weights = optimize_weights(sarimax_preds, lgbm_preds, test_series.values)

        ensemble_preds = (
            weights["sarimax"] * sarimax_preds + weights["lgbm"] * lgbm_preds
        )
        metrics["ensemble"] = evaluate_metrics(test_series.values, ensemble_preds)
        print(
            f"\n  Optimised weights → SARIMAX: {weights['sarimax']:.2f} | "
            f"LightGBM: {weights['lgbm']:.2f}"
        )
        print(
            f"  ENSEMBLE  MAE={metrics['ensemble']['mae']:.2f}  "
            f"RMSE={metrics['ensemble']['rmse']:.2f}  "
            f"MAPE={metrics['ensemble']['mape']:.2f}%"
        )

    elif sarimax_preds is None:
        # Only LightGBM available
        weights = {"sarimax": 0.0, "lgbm": 1.0}
        metrics["ensemble"] = metrics["lgbm"]
        print("\n  Only LightGBM available — using as sole model.")

    else:
        # Only SARIMAX available
        weights = {"sarimax": 1.0, "lgbm": 0.0}
        metrics["ensemble"] = metrics["sarimax"]
        print("\n  Only SARIMAX available — using as sole model.")

    save_weights(weights, paths["weights"])
    print(f"\n  Saved to: {models_dir}/")

    return {
        "commodity": commodity,
        "status": "success",
        "metrics": metrics,
        "weights": weights,
    }


def retrain_all(
    csv_path: str,
    models_dir: Path,
    commodities: list = None,
) -> dict:
    """Retrain all commodities found in the CSV (or a filtered subset)."""
    from .preprocess import load_csv

    df = load_csv(csv_path)
    all_commodities = df["commodity"].unique().tolist()

    if commodities:
        missing = [c for c in commodities if c not in all_commodities]
        if missing:
            logger.warning("Requested commodities not in data: %s", missing)
        all_commodities = [c for c in commodities if c in all_commodities]

    if not all_commodities:
        raise ValueError("No commodities to train.")

    results = {}
    for commodity in all_commodities:
        try:
            result = train_commodity(commodity, csv_path, models_dir)
            results[commodity] = result
        except Exception as e:
            logger.error("Failed to train '%s': %s", commodity, e)
            results[commodity] = {"status": "failed", "error": str(e)}

    success = sum(1 for r in results.values() if r.get("status") == "success")
    print(f"\n{'='*60}")
    print(f"  Retrain complete: {success}/{len(results)} succeeded.")
    print(f"{'='*60}")
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    csv_file = sys.argv[1] if len(sys.argv) > 1 else "data/kalimati.csv"
    models_out = Path(sys.argv[3] if len(sys.argv) > 3 else "models_ml")

    if len(sys.argv) > 2:
        train_commodity(sys.argv[2], csv_file, models_out)
    else:
        retrain_all(csv_file, models_out)
