#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.metrics import confusion_matrix, classification_report


DEFAULT_FEATURES = "evaluation/lucid/results/lucid_feature_table.csv"
DEFAULT_OUTPUT = "evaluation/lucid/results/lucid_final_labels.csv"

FEATURES = {
    "lucid_faithful": [
        "peak_memory_mib",
        "memory_fraction",
        "horus_gpu_util_mean",
        "amp_enabled",
    ],
    "extended": [
        "peak_memory_mib",
        "memory_fraction",
        "horus_gpu_util_mean",
        "amp_enabled",
        "avg_smact",
        "avg_smocc",
        "avg_drama",
        "horus_gpu_util_p95",
        "horus_gpu_util_max",
    ],
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train Lucid-style classifier and predict missing labels.")
    p.add_argument("--features-csv", default=DEFAULT_FEATURES)
    p.add_argument("--output-csv", default=DEFAULT_OUTPUT)
    p.add_argument("--feature-set", choices=sorted(FEATURES), default="lucid_faithful")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main() -> int:
    args = parse_args()

    df = pd.read_csv(args.features_csv)
    feature_cols = FEATURES[args.feature_set]

    train = df[df["lucid_label_usable"] == True].copy()
    predict = df[df["lucid_label_usable"] != True].copy()

    if train.empty:
        raise ValueError("No usable measured Lucid labels found for training")

    X_train = train[feature_cols]
    y_train = train["lucid_ss"].astype(int)

    model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "clf",
                RandomForestClassifier(
                    n_estimators=200,
                    random_state=args.seed,
                    class_weight="balanced",
                    min_samples_leaf=1,
                ),
            ),
        ]
    )

    model.fit(X_train, y_train)

    if len(train) >= 3:
        loo = LeaveOneOut()
        y_pred_cv = cross_val_predict(model, X_train, y_train, cv=loo)

        print("\nLeave-one-out classification report:")
        print(classification_report(y_train, y_pred_cv, zero_division=0))

        print("\nLeave-one-out confusion matrix [0=tiny, 1=medium, 2=jumbo]:")
        print(confusion_matrix(y_train, y_pred_cv, labels=[0, 1, 2]))

    out = df.copy()
    out["lucid_final_ss"] = out["lucid_ss"]
    out["lucid_final_class"] = out["lucid_class"]
    out["lucid_final_label_source"] = out["lucid_label_source"]

    if not predict.empty:
        X_pred = predict[feature_cols]
        pred_ss = model.predict(X_pred)

        ss_to_class = {0: "tiny", 1: "medium", 2: "jumbo"}

        out.loc[predict.index, "lucid_final_ss"] = pred_ss
        out.loc[predict.index, "lucid_final_class"] = [ss_to_class[int(x)] for x in pred_ss]
        out.loc[predict.index, "lucid_final_label_source"] = f"predicted_classifier_{args.feature_set}"

    proba = model.predict_proba(df[feature_cols])
    classes = list(model.named_steps["clf"].classes_)

    for i, cls in enumerate(classes):
        out[f"lucid_pred_proba_ss{int(cls)}"] = proba[:, i]

    importances = model.named_steps["clf"].feature_importances_
    print("\nFeature importances:")
    for name, value in sorted(zip(feature_cols, importances), key=lambda x: x[1], reverse=True):
        print(f"{name}: {value:.4f}")
              
    Path(args.output_csv).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output_csv, index=False)

    print(f"Training rows: {len(train)}")
    print(f"Predicted rows: {len(predict)}")
    print(f"Feature set: {args.feature_set}")
    print(f"Wrote {len(out)} rows to {args.output_csv}")
    print(out[[
        "spec_key",
        "lucid_label_usable",
        "lucid_final_class",
        "lucid_final_ss",
        "lucid_final_label_source",
    ]].to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())