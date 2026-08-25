import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import json

plt.rcParams["font.family"] = "DejaVu Sans"
COLORS = ["#2C5F7C", "#E07A5F", "#81B29A", "#F2CC8F", "#3D405B", "#BC6C25"]

df = pd.read_csv("data/superstore_clean.csv")
df.columns = [c.strip() for c in df.columns]
df["Order Date"] = pd.to_datetime(df["Order Date"], format="%m/%d/%Y")
df = df.dropna(subset=["Order Date", "Sales", "Order Quantity"])
df = df[df["Order Date"] >= "2009-01-01"]

# ---------- Top sub-categories by revenue ----------
top_sub = (
    df.groupby(["Product Category", "Product Sub-Category"])["Sales"]
    .sum()
    .reset_index()
    .sort_values("Sales", ascending=False)
    .head(10)
)

fig, ax = plt.subplots(figsize=(10, 5.5))
labels = top_sub["Product Sub-Category"] + " (" + top_sub["Product Category"].str[:4] + ")"
bars = ax.barh(labels[::-1], top_sub["Sales"][::-1] / 1000, color=COLORS[0])
ax.set_xlabel("Total Revenue ($ thousands)")
ax.set_title("Top 10 Sub-Categories by Revenue", fontsize=13, loc="left", fontweight="bold")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}K"))
ax.grid(axis="x", alpha=0.3)
for b in bars:
    ax.text(b.get_width() + 5, b.get_y() + b.get_height()/2, f"${b.get_width():,.0f}K",
            va="center", fontsize=9)
plt.tight_layout()
plt.savefig("charts/top_subcategories_revenue.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved charts/top_subcategories_revenue.png")

# ---------- Regional demand share ----------
regional = df.groupby("Region")["Order Quantity"].sum().sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(8, 5))
ax.bar(regional.index, regional.values, color=COLORS[1])
ax.set_ylabel("Total Units Sold")
ax.set_title("Units Sold by Region", fontsize=13, loc="left", fontweight="bold")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
plt.xticks(rotation=30, ha="right")
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig("charts/units_by_region.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved charts/units_by_region.png")

# ---------- Reorder recommendation table (from forecast results) ----------
with open("outputs/forecast_results.json") as f:
    results = json.load(f)

rows = []
for cat, r in results.items():
    rows.append({
        "Category": cat,
        "Avg Monthly Demand (last 6mo)": int(r["avg_monthly_units_last_6mo"]),
        "Forecast Next 3 Months (units)": ", ".join(str(int(x)) for x in r["next_3mo_forecast"]),
        "Forecast MAPE": f"{r['mape_pct']}%",
        "Recommended Reorder Qty (+15% safety stock)": int(r["recommended_reorder_qty"]),
    })
table = pd.DataFrame(rows)
table.to_csv("outputs/reorder_recommendations.csv", index=False)
print(table.to_string(index=False))
