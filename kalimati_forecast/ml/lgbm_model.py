"""
LightGBM model for Kalimati price forecasting.
Uses recursive multi-step forecasting with time-series cross-validation.
All errors raised as typed ForecastAPIError subclasses.
"""

import logging
import warnings
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.model_selection import TimeSeriesSplit

from ..exceptions import TrainingFailedError, ForecastFailedError, ModelLoadError

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


def fit_lightgbm(feature_df: pd.DataFrame) -> object:
    """
    Train LightGBM regressor with time-series cross-validation.

    Args:
        feature_df: DataFrame from preprocess.build_features() with 'avg_price' target.

    Returns:
        Trained LGBMRegressor.

    Raises:
        TrainingFailedError — lightgbm not installed or training error
    """
    try:
        import lightgbm as lgb
    except ImportError:
        raise TrainingFailedError(
            'LightGBM',
            detail="lightgbm package is not installed. Run: pip install lightgbm"
        )

    from .preprocess import get_feature_columns

    feature_cols = get_feature_columns()

    # Validate feature columns exist
    missing_cols = [c for c in feature_cols if c not in feature_df.columns]
    if missing_cols:
        raise TrainingFailedError(
            'LightGBM',
            detail=f"Feature columns missing from data: {missing_cols}. "
                   "Ensure build_features() was called before fit_lightgbm()."
        )

    if len(feature_df) < 30:
        raise TrainingFailedError(
            'LightGBM',
            detail=f"Need at least 30 feature rows, got {len(feature_df)}."
        )

    X = feature_df[feature_cols]
    y = feature_df['avg_price']

    if y.isna().any():
        raise TrainingFailedError('LightGBM', detail="Target column 'avg_price' contains NaN values.")

    try:
        n_splits = min(3, len(X) // 30)
        if n_splits < 2:
            logger.warning("Dataset too small for cross-validation. Training without CV.")
            n_splits = None

        model = lgb.LGBMRegressor(
            n_estimators=500,
            learning_rate=0.03,
            max_depth=5,
            num_leaves=31,
            min_child_samples=max(5, len(X) // 50),  # scale to dataset size
            subsample=0.8,
            subsample_freq=1,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=0.1,
            random_state=42,
            verbose=-1,
        )

        if n_splits:
            tscv = TimeSeriesSplit(n_splits=n_splits)
            cv_scores = []

            for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
                X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
                y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]

                model.fit(
                    X_tr, y_tr,
                    eval_set=[(X_val, y_val)],
                    callbacks=[
                        lgb.early_stopping(50, verbose=False),
                        lgb.log_evaluation(period=-1),
                    ],
                )
                preds = model.predict(X_val)
                mae   = float(np.mean(np.abs(y_val.values - preds)))
                cv_scores.append(mae)
                logger.info("  LightGBM fold %d/%d — MAE: %.2f", fold + 1, n_splits, mae)

            logger.info(
                "LightGBM CV complete. Mean MAE: %.2f ± %.2f",
                np.mean(cv_scores), np.std(cv_scores)
            )

        # Final fit on all available data
        model.fit(X, y)
        logger.info("LightGBM trained on %d samples with %d features.", len(X), len(feature_cols))
        return model

    except TrainingFailedError:
        raise
    except Exception as e:
        logger.exception("LightGBM training error")
        raise TrainingFailedError('LightGBM', detail=str(e))


def forecast_lightgbm(model, series: pd.Series, steps: int = 7) -> dict:
    """
    Recursive multi-step forecast.
    Each future step is predicted using the previous predictions as lag features.

    Args:
        model:  Trained LGBMRegressor.
        series: Historical price series (seeds the lag features).
        steps:  Days to forecast (1–60).

    Returns:
        {'predictions': [float, ...]}

    Raises:
        ForecastFailedError — model.predict failed or series too short
    """
    if steps < 1 or steps > 60:
        raise ForecastFailedError(
            'LightGBM',
            detail=f"steps must be between 1 and 60, got {steps}."
        )

    if len(series) < 30:
        raise ForecastFailedError(
            'LightGBM',
            detail=f"Historical series too short to build lag features. Got {len(series)} days, need 30."
        )

    from .preprocess import get_feature_columns, _festival_flag

    feature_cols = get_feature_columns()

    try:
        history = list(series.values.astype(float))
        dates   = list(series.index)
        predictions = []

        for step in range(steps):
            next_date = dates[-1] + pd.Timedelta(days=1)
            dates.append(next_date)
            h = np.array(history)

            def safe_lag(lag):
                return float(h[-lag]) if len(h) >= lag else float(h[0])

            def safe_window(win):
                w = h[-win:] if len(h) >= win else h
                return w if len(w) > 0 else np.array([h[-1]])

            row = {}

            # Lag features
            for lag in [1, 2, 3, 7, 14, 21, 30]:
                row[f'lag_{lag}'] = safe_lag(lag)

            # Rolling features
            for win in [7, 14, 30]:
                w = safe_window(win)
                row[f'roll_mean_{win}'] = float(np.mean(w))
                row[f'roll_std_{win}']  = float(np.std(w)) if len(w) > 1 else 0.0
                row[f'roll_min_{win}']  = float(np.min(w))
                row[f'roll_max_{win}']  = float(np.max(w))

            # EWM
            s = pd.Series(h)
            row['ewm_7']  = float(s.ewm(span=7,  min_periods=1).mean().iloc[-1])
            row['ewm_14'] = float(s.ewm(span=14, min_periods=1).mean().iloc[-1])

            # Calendar
            row['dayofweek']  = int(next_date.dayofweek)
            row['month']      = int(next_date.month)
            row['quarter']    = int(next_date.quarter)
            row['weekofyear'] = int(next_date.isocalendar()[1])
            row['is_weekend'] = int(next_date.dayofweek >= 5)
            row['is_festival'] = _festival_flag(next_date)

            # Momentum
            row['pct_change_7']  = float(np.clip(
                (h[-1] - h[-7])  / h[-7]  if len(h) >= 7  and h[-7]  != 0 else 0,
                -1, 1
            ))
            row['pct_change_30'] = float(np.clip(
                (h[-1] - h[-30]) / h[-30] if len(h) >= 30 and h[-30] != 0 else 0,
                -1, 1
            ))

            X_row = pd.DataFrame([row])[feature_cols]
            pred  = float(model.predict(X_row)[0])
            pred  = max(0.0, pred)   # prices can't be negative

            # Sanity check: flag extreme jumps (>200% from last known price)
            last_price = history[-1]
            if last_price > 0 and pred > last_price * 3:
                logger.warning(
                    "Step %d: extreme prediction %.2f vs last %.2f — capping.",
                    step + 1, pred, last_price
                )
                pred = last_price * 1.5

            predictions.append(round(pred, 2))
            history.append(pred)

        return {'predictions': predictions}

    except ForecastFailedError:
        raise
    except Exception as e:
        logger.exception("LightGBM forecast error")
        raise ForecastFailedError('LightGBM', detail=str(e))


def get_feature_importance(model) -> dict:
    """Return top-20 feature importances."""
    from .preprocess import get_feature_columns
    try:
        cols = get_feature_columns()
        imp  = model.feature_importances_
        ranked = sorted(zip(cols, imp.tolist()), key=lambda x: -x[1])[:20]
        return {k: int(v) for k, v in ranked}
    except Exception as e:
        logger.warning("Could not extract feature importance: %s", e)
        return {}


def save_lgbm(model, path: Path):
    try:
        joblib.dump(model, path)
        logger.info("LightGBM model saved to %s", path)
    except Exception as e:
        logger.error("Failed to save LightGBM model: %s", e)
        raise


def load_lgbm(path: Path):
    try:
        return joblib.load(path)
    except FileNotFoundError:
        raise ModelLoadError('LightGBM', detail=f"File not found: {path}")
    except Exception as e:
        raise ModelLoadError('LightGBM', detail=str(e))