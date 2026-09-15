"""
Week 3 - Step 4, 5, 6: Train a simple ML classifier, compare models, evaluate.

Run:
    python train_classifier.py

Produces:
    - models/vectorizer.joblib
    - models/classifier.joblib        (best model, auto-selected)
    - models/model_comparison.txt     (metrics for all 3 models)
    - models/confusion_matrix.png     (for the best model)
"""

import os
import csv
import joblib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    classification_report, confusion_matrix, ConfusionMatrixDisplay
)

from text_utils import clean_text

DATA_PATH = "dataset/documents.csv"
MODEL_DIR = "models"
os.makedirs(MODEL_DIR, exist_ok=True)


def load_data():
    texts, labels = [], []
    with open(DATA_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            texts.append(clean_text(row["text"]))
            labels.append(row["label"])
    return texts, labels


def evaluate(model, X_test, y_test, labels_order):
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, preds, average="macro", zero_division=0
    )
    report = classification_report(y_test, preds, zero_division=0)
    cm = confusion_matrix(y_test, preds, labels=labels_order)
    return {
        "accuracy": acc,
        "precision_macro": precision,
        "recall_macro": recall,
        "f1_macro": f1,
        "report": report,
        "confusion_matrix": cm,
        "preds": preds,
    }


def main():
    texts, labels = load_data()
    labels_order = sorted(set(labels))
    print(f"Loaded {len(texts)} documents across classes: {labels_order}")

    X_train_text, X_test_text, y_train, y_test = train_test_split(
        texts, labels, test_size=0.25, random_state=42, stratify=labels
    )

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),
        max_features=3000,
        min_df=1,
    )
    X_train = vectorizer.fit_transform(X_train_text)
    X_test = vectorizer.transform(X_test_text)

    candidates = {
        "LogisticRegression": LogisticRegression(max_iter=1000),
        "LinearSVM": LinearSVC(),
        "NaiveBayes": MultinomialNB(),
    }

    results = {}
    log_lines = []
    for name, model in candidates.items():
        model.fit(X_train, y_train)
        res = evaluate(model, X_test, y_test, labels_order)
        results[name] = (model, res)
        log_lines.append(f"\n===== {name} =====")
        log_lines.append(f"Accuracy:            {res['accuracy']:.3f}")
        log_lines.append(f"Precision (macro):   {res['precision_macro']:.3f}")
        log_lines.append(f"Recall (macro):      {res['recall_macro']:.3f}")
        log_lines.append(f"F1-score (macro):    {res['f1_macro']:.3f}")
        log_lines.append("\nPer-class report:")
        log_lines.append(res["report"])
        log_lines.append(f"Confusion matrix (rows=true, cols=pred), order={labels_order}:")
        log_lines.append(str(res["confusion_matrix"]))

    # pick best model by macro F1 (not just "most advanced" - per task instructions)
    best_name = max(results, key=lambda n: results[n][1]["f1_macro"])
    best_model, best_res = results[best_name]

    log_lines.append(f"\n\n==> Selected model: {best_name} "
                      f"(F1-macro={best_res['f1_macro']:.3f}) — chosen because it gave "
                      f"the best held-out F1-score, not simply because it is more advanced.")

    summary = "\n".join(log_lines)
    print(summary)

    with open(os.path.join(MODEL_DIR, "model_comparison.txt"), "w") as f:
        f.write(summary)

    # save confusion matrix plot for the best model
    disp = ConfusionMatrixDisplay(
        confusion_matrix=best_res["confusion_matrix"], display_labels=labels_order
    )
    disp.plot(cmap="Blues", values_format="d")
    plt.title(f"Confusion Matrix - {best_name}")
    plt.tight_layout()
    plt.savefig(os.path.join(MODEL_DIR, "confusion_matrix.png"))
    plt.close()

    joblib.dump(vectorizer, os.path.join(MODEL_DIR, "vectorizer.joblib"))
    joblib.dump(best_model, os.path.join(MODEL_DIR, "classifier.joblib"))
    joblib.dump(labels_order, os.path.join(MODEL_DIR, "labels_order.joblib"))
    joblib.dump(best_name, os.path.join(MODEL_DIR, "best_model_name.joblib"))

    print(f"\nSaved best model ({best_name}) and vectorizer to '{MODEL_DIR}/'.")


if __name__ == "__main__":
    main()
