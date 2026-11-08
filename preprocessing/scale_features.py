import pandas as pd
import json
import joblib
import os

from sklearn.preprocessing import StandardScaler

TRAIN_FILE = "data/processed/train_features.csv"
VAL_FILE = "data/processed/validation_features.csv"
TEST_FILE = "data/processed/test_features.csv"

OUTPUT_DIR = "data/processed/scaled"

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Loading features...")

train = pd.read_csv(TRAIN_FILE)
validation = pd.read_csv(VAL_FILE)
test = pd.read_csv(TEST_FILE)

print("Train:", train.shape)
print("Validation:", validation.shape)
print("Test:", test.shape)

# Make sure all datasets have identical columns
assert list(train.columns) == list(validation.columns)
assert list(train.columns) == list(test.columns)

feature_columns = list(train.columns)

# Create scaler
scaler = StandardScaler()

# IMPORTANT:
# Fit ONLY on training data
X_train = scaler.fit_transform(train)

# Apply same scaler to validation and test
X_validation = scaler.transform(validation)
X_test = scaler.transform(test)

# Convert back to DataFrames
train_scaled = pd.DataFrame(
    X_train,
    columns=feature_columns
)

validation_scaled = pd.DataFrame(
    X_validation,
    columns=feature_columns
)

test_scaled = pd.DataFrame(
    X_test,
    columns=feature_columns
)

# Save
train_scaled.to_csv(
    f"{OUTPUT_DIR}/train_scaled.csv",
    index=False
)

validation_scaled.to_csv(
    f"{OUTPUT_DIR}/validation_scaled.csv",
    index=False
)

test_scaled.to_csv(
    f"{OUTPUT_DIR}/test_scaled.csv",
    index=False
)

# Save scaler
joblib.dump(
    scaler,
    f"{OUTPUT_DIR}/scaler.pkl"
)

# Save feature names
with open(
    f"{OUTPUT_DIR}/feature_columns.json",
    "w"
) as f:
    json.dump(feature_columns, f, indent=2)

print("\n========== SCALING COMPLETE ==========")

print("Train scaled:", train_scaled.shape)
print("Validation scaled:", validation_scaled.shape)
print("Test scaled:", test_scaled.shape)

print("\nTraining feature means:")
print(train_scaled.mean().round(4))

print("\nTraining feature standard deviations:")
print(train_scaled.std().round(4))

print("\nSaved:")
print(f"{OUTPUT_DIR}/train_scaled.csv")
print(f"{OUTPUT_DIR}/validation_scaled.csv")
print(f"{OUTPUT_DIR}/test_scaled.csv")
print(f"{OUTPUT_DIR}/scaler.pkl")
print(f"{OUTPUT_DIR}/feature_columns.json")