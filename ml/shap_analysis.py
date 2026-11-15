import pandas as pd
import joblib
import shap
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split


# ==========================================
# 1. Load HTRU2 dataset
# ==========================================

df = pd.read_csv(
    "data/htru2/HTRU_2.csv",
    header=None
)


# ==========================================
# 2. Give columns proper names
# ==========================================

df.columns = [
    "Profile_Mean",
    "Profile_Std",
    "Profile_Skewness",
    "Profile_Kurtosis",
    "DM_Mean",
    "DM_Std",
    "DM_Skewness",
    "DM_Kurtosis",
    "Target"
]


# ==========================================
# 3. Separate features and target
# ==========================================

X = df.drop("Target", axis=1)
y = df["Target"]


# ==========================================
# 4. Same 70/30 split
# ==========================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.30,
    stratify=y,
    random_state=42
)


# ==========================================
# 5. Load trained Random Forest model
# ==========================================

model = joblib.load(
    "models/random_forest_htru2.pkl"
)

print("Random Forest model loaded successfully.")


# ==========================================
# 6. Create SHAP explainer
# ==========================================

explainer = shap.TreeExplainer(model)


# ==========================================
# 7. Select 500 test samples
# ==========================================

sample = X_test.iloc[:500]


# ==========================================
# 8. Calculate SHAP values
# ==========================================

shap_values = explainer.shap_values(sample)

print("SHAP calculation completed.")


# ==========================================
# 9. Create SHAP summary plot
# ==========================================

shap.summary_plot(
    shap_values,
    sample,
    show=False
)


# ==========================================
# 10. Save the figure
# ==========================================

plt.tight_layout()

plt.savefig(
    "reports/shap_summary.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()

print("SHAP plot saved successfully:")
print("reports/shap_summary.png")
