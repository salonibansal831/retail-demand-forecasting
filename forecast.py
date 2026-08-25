"""
Retail Demand Forecasting & Inventory Planning
Business Data Analytics project - Saloni Bansal

Pipeline:
1. Load & clean raw transaction data
2. Build monthly demand time series by product category
3. Train/test split, forecast with Holt-Winters exponential smoothing
4. Evaluate forecast accuracy (MAPE)
5. Translate forecasts into inventory/reorder recommendations
6. Export charts + summary tables
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import json
import warnings
warnings.filterwarnings("ignore")

plt.rcParams["font.family"] = "DejaVu Sans"
COLORS = ["#2C5F7C", "#E07A5F", "#81B29A", "#F2CC8F", "#3D405B", "#BC6C25"]

# ---------- 1. Load & clean ----------
df = pd.read_csv("data/superstore_clean.csv")
df.columns = [c.strip() for c in df.columns]
df["Order Date"] = pd.to_datetime(df["Order Date"], format="%m/%d/%Y")
df = df.dropna(subset=["Order Date", "Sales", "Order Quantity"])
df = df[df["Order Date"] >= "2009-01-01"]  # trim sparse early data

print(f"Rows after cleaning: {len(df):,}")
print(f"Date range: {df['Order Date'].min().date()} to {df['Order Date'].max().date()}")
print(f"Categories: {df['Product Category'].unique().tolist()}")

# ---------- 2. Monthly demand by category ----------
df["Month"] = df["Order Date"].dt.to_period("M").dt.to_timestamp()
monthly = (
    df.groupby(["Month", "Product Category"])
    .agg(units=("Order Quantity", "sum"), revenue=("Sales", "sum"))
    .reset_index()
)

categories = df["Product Category"].unique().tolist()
results = {}

fig, axes = plt.subplots(len(categories), 1, figsize=(11, 3.2 * len(categories)), sharex=False)
if len(categories) == 1:
    axes = [axes]

for i, cat in enumerate(categories):
    series = (
        monthly[monthly["Product Category"] == cat]
        .set_index("Month")["units"]
        .asfreq("MS")
        .fillna(0)
    )
    # keep only full months in range, drop trailing partial month if present
    series = series[series.index <= df["Month"].max()]

    n_test = 6
    train, test = series.iloc[:-n_test], series.iloc[-n_test:]

    model = ExponentialSmoothing(
        train, trend="add", seasonal="add", seasonal_periods=12,
        initialization_method="estimated"
    ).fit()
    forecast = model.forecast(n_test)

    mape = float(np.mean(np.abs((test.values - forecast.values) / np.maximum(test.values, 1))) * 100)

    # forecast next 3 months beyond full data for reorder planning
    full_model = ExponentialSmoothing(
        series, trend="add", seasonal="add", seasonal_periods=12,
        initialization_method="estimated"
    ).fit()
    future = full_model.forecast(3)

    results[cat] = {
        "mape_pct": round(mape, 1),
        "avg_monthly_units_last_6mo": round(float(test.mean()), 0),
        "next_3mo_forecast": [round(float(x), 0) for x in future.values],
        "recommended_reorder_qty": round(float(future.mean()) * 1.15, 0),  # +15% safety stock
    }

    ax = axes[i]
    ax.plot(train.index, train.values, color=COLORS[i % len(COLORS)], label="Actual (train)", linewidth=1.6)
    ax.plot(test.index, test.values, color=COLORS[i % len(COLORS)], linewidth=1.6, linestyle="-")
    ax.plot(test.index, forecast.values, color="#B0B0B0", linewidth=2, linestyle="--", label="Forecast (test)")
    ax.plot(future.index, future.values, color="#B0413E", linewidth=2, linestyle="--", label="Forecast (next 3mo)")
    ax.axvline(test.index[0], color="gray", linewidth=0.8, linestyle=":")
    ax.set_title(f"{cat} — Monthly Units Sold (MAPE: {mape:.1f}%)", fontsize=11, loc="left")
    ax.legend(fontsize=8, loc="upper left")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.grid(alpha=0.25)

plt.tight_layout()
plt.savefig("charts/demand_forecast_by_category.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved charts/demand_forecast_by_category.png")

with open("outputs/forecast_results.json", "w") as f:
    json.dump(results, f, indent=2)

print(json.dumps(results, indent=2))
