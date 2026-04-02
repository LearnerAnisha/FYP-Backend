"""
Training pipeline: SARIMAX + LightGBM ensemble for Kalimati price forecasting.

Updated: train_commodity() and retrain_all() now accept an optional `df`
parameter (pre-loaded DataFrame).  When `df` is supplied the CSV path is
ignored entirely, so views can pass the DB-sourced DataFrame directly.

Priority order for data loading:
    1. df   — pre-loaded DataFrame passed by the caller (highest priority)
    2. csv_path — explicit CSV path (CLI / legacy use)
    3. load_from_db() — live DB query (default when nothing else is given)

Usage (CLI):
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
    models_dir: Path,
    csv_path: str = None, 
    df=None, 
    test_days: int = 60,
) -> dict:
    """
    Full training pipeline for one commodity.

    Data-loading priority:
        1. df        — pre-loaded DataFrame (from DB or any other source)
        2. csv_path  — load from CSV file
        3. (default) — query price_predictor.DailyPriceHistory via load_from_db()

    Steps:
        1. Resolve data source
        2. Prepare daily series (clean, fill gaps)
        3. Train/test split (last `test_days` days held out)
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
        load_from_db,
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

    # 1. Resolve data source
    if df is None:
        if csv_path:
            logger.info("Loading data from CSV: %s", csv_path)
            df = load_csv(csv_path)
        else:
            logger.info("No CSV path supplied — loading from price_predictor DB.")
            df = load_from_db()

    # 2. Prepare series 
    series = prepare_series(df, commodity)

    print(
        f"  Data: {series.index[0].date()} → {series.index[-1].date()} ({len(series)} days)"
    )

    # 3. Train / test split 
    train_series, test_series = train_test_split_ts(series, test_days=test_days)
    print(f"  Split: {len(train_series)} train / {len(test_series)} test days")

    models_dir.mkdir(parents=True, exist_ok=True)
    paths = _model_paths(commodity, models_dir)
    metrics = {}
    sarimax_model = None
    lgbm_model = None

    # 4. Fit SARIMAX 
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

    # 5. Fit LightGBM 
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

    # 6. Both models failed 
    if sarimax_preds is None and lgbm_preds is None:
        raise TrainingFailedError(
            "ensemble",
            detail=(
                f"Both SARIMAX and LightGBM failed for '{commodity}'. "
                "Check data quality and logs for details."
            ),
        )

    # 7. Ensemble weights 
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
        weights = {"sarimax": 0.0, "lgbm": 1.0}
        metrics["ensemble"] = metrics["lgbm"]
        print("\n  Only LightGBM available — using as sole model.")

    else:
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
    models_dir: Path,
    csv_path: str = None,  
    df=None,  
    commodities: list = None,
) -> dict:
    """
    Retrain all commodities found in the data source (or a filtered subset).

    Data-loading priority (same as train_commodity):
        1. df        — pre-loaded DataFrame
        2. csv_path  — load from CSV file
        3. (default) — query price_predictor.DailyPriceHistory
    """
    from .preprocess import load_csv, load_from_db

    # Resolve data once — all commodities share the same DataFrame
    if df is None:
        if csv_path:
            logger.info("retrain_all: loading data from CSV: %s", csv_path)
            df = load_csv(csv_path)
        else:
            logger.info("retrain_all: loading data from price_predictor DB.")
            df = load_from_db()

    all_commodities = df["commodity"].unique().tolist()

    if commodities:
        missing = [c for c in commodities if c not in all_commodities]
        if missing:
            logger.warning("Requested commodities not found in data: %s", missing)
        all_commodities = [c for c in commodities if c in all_commodities]

    if not all_commodities:
        raise ValueError("No commodities to train.")

    results = {}
    for commodity in all_commodities:
        try:
            # Pass the already-loaded df so we don't hit the DB / disk again
            result = train_commodity(commodity, models_dir, df=df)
            results[commodity] = result
        except Exception as e:
            logger.error("Failed to train '%s': %s", commodity, e)
            results[commodity] = {"status": "failed", "error": str(e)}

    success = sum(1 for r in results.values() if r.get("status") == "success")
    print(f"\n{'='*60}")
    print(f"  Retrain complete: {success}/{len(results)} succeeded.")
    print(f"{'='*60}")
    return results

# CLI entry point
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    # argv: script.py [csv_file] [commodity] [models_dir]
    csv_file = sys.argv[1] if len(sys.argv) > 1 else None
    models_out = Path(sys.argv[3] if len(sys.argv) > 3 else "models_ml")

    if len(sys.argv) > 2:
        train_commodity(sys.argv[2], models_out, csv_path=csv_file)
    else:
        retrain_all(models_out, csv_path=csv_file)
