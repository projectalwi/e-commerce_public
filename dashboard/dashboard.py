"""E-Commerce Public Dataset dashboard (Streamlit).

Run from the project root:  streamlit run dashboard/dashboard.py
Uses dashboard/main_data.csv, which is exported by the last cell of the notebook.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from matplotlib.ticker import FuncFormatter

DATA_PATH = Path(__file__).parent / "main_data.csv"
MIN_DATE, MAX_DATE = pd.Timestamp("2016-09-01"), pd.Timestamp("2018-10-31")
RFM_LAST_DAY = pd.Timestamp("2018-09-30")  # RFM period ends in September 2018, as in the notebook
SEGMENT_ORDER = ["Champions", "At-Risk Big Spenders", "Potential Customers", "Lost Low-Value"]
SEGMENT_COLORS = {"Champions": "#27ae60", "At-Risk Big Spenders": "#e67e22",
                  "Potential Customers": "#2980b9", "Lost Low-Value": "#95a5a6"}

st.set_page_config(page_title="E-Commerce Dashboard", page_icon="🛒", layout="wide")


# ----------------------------------------------------------------------------- data
@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, parse_dates=["order_purchase_timestamp"])
    # orders that never produced revenue are excluded everywhere, as in the notebook
    return df[~df["order_status"].isin(["canceled", "unavailable"])].copy()


def category_quality(df: pd.DataFrame, min_orders: int) -> pd.DataFrame:
    """Average review score and bad-review % per category (one row per order x category)."""
    reviewed = (df.dropna(subset=["review_score"])
                  .drop_duplicates(["order_id", "product_category_name_english"]))
    reviewed = reviewed.assign(is_bad=reviewed["review_score"] <= 2)
    out = (reviewed.groupby("product_category_name_english")
           .agg(total_orders=("order_id", "nunique"), avg_review_score=("review_score", "mean"),
                bad_orders=("is_bad", "sum"), bad_review_pct=("is_bad", "mean"))
           .reset_index())
    out["bad_review_pct"] *= 100
    out = out[(out["total_orders"] >= min_orders) & (out["product_category_name_english"] != "Unknown")].copy()
    out["priority_rank"] = (out["avg_review_score"].rank(method="min") +
                            out["bad_review_pct"].rank(method="min", ascending=False)) / 2
    return out.sort_values(["priority_rank", "total_orders"], ascending=[True, False]).reset_index(drop=True)


def monthly_revenue(df: pd.DataFrame) -> pd.Series:
    return df.groupby(df["order_purchase_timestamp"].dt.to_period("M"))["revenue"].sum()


def rfm_table(df: pd.DataFrame, snapshot: pd.Timestamp) -> pd.DataFrame:
    orders = (df.groupby(["order_id", "customer_unique_id"], as_index=False)
                .agg(order_date=("order_purchase_timestamp", "min"), order_value=("revenue", "sum")))
    rfm = (orders.groupby("customer_unique_id")
                 .agg(last_purchase=("order_date", "max"), frequency=("order_id", "nunique"),
                      monetary=("order_value", "sum"))
                 .reset_index())
    rfm["recency"] = (snapshot - rfm["last_purchase"]).dt.days
    rfm["R_score"] = pd.qcut(rfm["recency"].rank(method="first"), 4, labels=[4, 3, 2, 1]).astype(int)
    rfm["M_score"] = pd.qcut(rfm["monetary"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)

    def segment(row):
        if row["R_score"] >= 3 and row["M_score"] >= 3:
            return "Champions"
        if row["R_score"] >= 3:
            return "Potential Customers"
        if row["M_score"] >= 3:
            return "At-Risk Big Spenders"
        return "Lost Low-Value"

    rfm["segment"] = rfm.apply(segment, axis=1)
    return rfm


million = FuncFormatter(lambda v, _: f"{v / 1e6:.1f}M")

# ----------------------------------------------------------------------------- layout
st.title("🛒 E-Commerce Public Dataset Dashboard")
st.caption("Brazilian marketplace, September 2016 - September 2018. Revenue = product price + freight.")

try:
    data = load_data()
except FileNotFoundError:
    st.error(f"`{DATA_PATH.name}` was not found. Run the last cell of the notebook to export it.")
    st.stop()

with st.sidebar:
    st.header("Filters")
    date_range = st.date_input("Purchase date range", value=(MIN_DATE.date(), MAX_DATE.date()),
                               min_value=MIN_DATE.date(), max_value=MAX_DATE.date())
    # st.date_input returns one date while the user is still picking the second one
    start_date, end_date = date_range if len(date_range) == 2 else (date_range[0], MAX_DATE.date())
    st.caption("Product quality uses the full range. Revenue trend uses Jan 2017 - Aug 2018 and RFM uses Sep 2016 - Sep 2018, because the last months are incomplete.")

mask = (data["order_purchase_timestamp"] >= pd.Timestamp(start_date)) & \
       (data["order_purchase_timestamp"] < pd.Timestamp(end_date) + pd.Timedelta(days=1))
df = data[mask]
if df.empty:
    st.warning("No data in the selected range.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total revenue", f"{df['revenue'].sum() / 1e6:.2f}M BRL")
c2.metric("Orders", f"{df['order_id'].nunique():,}")
c3.metric("Customers", f"{df['customer_unique_id'].nunique():,}")
c4.metric("Avg review score", f"{df.drop_duplicates('order_id')['review_score'].mean():.2f}")

tab1, tab2, tab3 = st.tabs(["1. Product quality", "2. Revenue trend & forecast", "3. Customer segments (RFM)"])

# ----------------------------------------------------------------------------- tab 1
with tab1:
    st.subheader("Which product categories need a quality evaluation first?")
    left, right = st.columns([1, 3])
    min_orders = left.slider("Minimum reviewed orders per category", 30, 500, 100, step=10)
    top_n = left.slider("Categories to show", 5, 20, 10)
    quality = category_quality(df, min_orders)
    overall = df.dropna(subset=["review_score"]).drop_duplicates("order_id")
    overall_avg, overall_bad = overall["review_score"].mean(), (overall["review_score"] <= 2).mean() * 100

    top = quality.head(top_n)
    labels = top["product_category_name_english"] + " (n=" + top["total_orders"].astype(str) + ")"
    colors = ["#c0392b" if i < 3 else "#95a5a6" for i in range(len(top))]
    fig, axes = plt.subplots(1, 2, figsize=(14, 0.55 * top_n + 2), sharey=True)
    axes[0].barh(labels, top["avg_review_score"], color=colors)
    axes[0].axvline(overall_avg, color="black", linestyle="--", linewidth=1, label=f"All categories: {overall_avg:.2f}")
    axes[0].bar_label(axes[0].containers[0], fmt="%.2f", padding=3)
    axes[0].set_xlim(0, 5); axes[0].invert_yaxis(); axes[0].legend(loc="upper right")
    axes[0].set_title("Average review score (lower = worse)")
    axes[1].barh(labels, top["bad_review_pct"], color=colors)
    axes[1].axvline(overall_bad, color="black", linestyle="--", linewidth=1, label=f"All categories: {overall_bad:.1f}%")
    axes[1].bar_label(axes[1].containers[0], fmt="%.1f%%", padding=3)
    axes[1].set_xlim(0, max(32, top["bad_review_pct"].max() * 1.2)); axes[1].legend(loc="lower right")
    axes[1].set_title("Bad reviews, 1-2 stars (higher = worse)")
    plt.tight_layout()
    right.pyplot(fig)
    plt.close(fig)
    st.dataframe(top.drop(columns="priority_rank").round(2), width="stretch", hide_index=True)
    st.info("Categories are ranked by the average of two ranks: lowest average score and highest bad-review %. "
            "Categories with a small sample (n < 150) should be monitored before taking large action.")

# ----------------------------------------------------------------------------- tab 2
with tab2:
    st.subheader("How does monthly revenue change, and what can we expect next?")
    # Same window as the notebook: Sep-Dec 2016 (5 orders) and Sep 2018 (16 orders) are incomplete months
    # and would distort the moving average and the forecast baseline.
    trend_df = df[(df["order_purchase_timestamp"] >= "2017-01-01") & (df["order_purchase_timestamp"] < "2018-09-01")]
    st.caption("Monthly trend uses January 2017 - August 2018 (months before and after are too incomplete).")
    if trend_df.empty:
        st.warning("The selected date range has no complete months between January 2017 and August 2018.")
        st.stop()
    categories = sorted(trend_df["product_category_name_english"].unique())
    default_top5 = trend_df.groupby("product_category_name_english")["revenue"].sum().nlargest(5).index.tolist()
    chosen = st.multiselect("Product categories (empty = all categories)", categories)
    view = trend_df[trend_df["product_category_name_english"].isin(chosen)] if chosen else trend_df

    monthly = monthly_revenue(view)
    if len(monthly) < 6:
        st.warning("Select a wider date range (at least 6 months) to see the trend and forecast.")
    else:
        ma3 = monthly.rolling(3).mean()
        horizon = 6
        forecast_value = monthly.tail(3).mean()
        future = pd.period_range(monthly.index[-1] + 1, periods=horizon, freq="M")
        error_band = 0.11  # average backtest MAPE of the 3-month moving average (see notebook)

        fig, ax = plt.subplots(figsize=(14, 5))
        ax.plot(monthly.index.to_timestamp(), monthly.values, marker="o", color="#2980b9", label="Monthly revenue")
        ax.plot(ma3.index.to_timestamp(), ma3.values, color="#e67e22", linewidth=2.5, label="3-month moving average")
        ax.plot(future.to_timestamp(), np.repeat(forecast_value, horizon), "--o", color="#27ae60", label="Forecast (3-month MA, flat)")
        ax.fill_between(future.to_timestamp(), forecast_value * (1 - error_band), forecast_value * (1 + error_band),
                        color="#27ae60", alpha=0.2, label=f"Error band (+/-{error_band * 100:.0f}%)")
        ax.yaxis.set_major_formatter(million)
        ax.set_xlabel("Month"); ax.set_ylabel("Revenue (BRL)"); ax.legend(loc="upper left")
        plt.tight_layout(); st.pyplot(fig); plt.close(fig)

        q1_fc, q2_fc = forecast_value * 3, forecast_value * 3
        m1, m2, m3 = st.columns(3)
        m1.metric(f"Forecast {future[0].strftime('%b %Y')} - {future[2].strftime('%b %Y')}", f"{q1_fc / 1e6:.2f}M BRL",
                  f"range {q1_fc * (1 - error_band) / 1e6:.2f}-{q1_fc * (1 + error_band) / 1e6:.2f}M", delta_color="off")
        m2.metric(f"Forecast {future[3].strftime('%b %Y')} - {future[5].strftime('%b %Y')}", f"{q2_fc / 1e6:.2f}M BRL",
                  f"range {q2_fc * (1 - error_band) / 1e6:.2f}-{q2_fc * (1 + error_band) / 1e6:.2f}M", delta_color="off")
        last_mom = (monthly.iloc[-1] / monthly.iloc[-2] - 1) * 100
        m3.metric("Last month vs previous month", f"{monthly.iloc[-1] / 1e6:.2f}M BRL", f"{last_mom:+.1f}%")
        st.info("The forecast is a flat baseline (average of the last 3 months). It does not include seasonality: "
                "November 2017 jumped 53% over October, so November 2018 may be higher. In a backtest this method "
                "had 9-13% error versus 24-35% for a linear trend, because growth slowed after March 2018.")

    st.markdown("**Top 5 categories by revenue in the selected period**")
    top5 = trend_df[trend_df["product_category_name_english"].isin(default_top5)]
    pivot = (top5.groupby([top5["order_purchase_timestamp"].dt.to_period("M"), "product_category_name_english"])["revenue"]
                 .sum().unstack()[default_top5])
    fig, ax = plt.subplots(figsize=(14, 4.5))
    for col in pivot.columns:
        ax.plot(pivot.index.to_timestamp(), pivot[col], marker="o", markersize=4, label=col)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v / 1e3:.0f}K"))
    ax.set_xlabel("Month"); ax.set_ylabel("Revenue (BRL)"); ax.legend(ncol=3)
    plt.tight_layout(); st.pyplot(fig); plt.close(fig)

# ----------------------------------------------------------------------------- tab 3
with tab3:
    st.subheader("Which customer groups should we retain or win back?")
    st.caption("Recency = days since last purchase, Monetary = total spending. Frequency is not used because ~97% "
               "of customers purchased only once. Scores are quartiles (4 = best).")
    snapshot = min(pd.Timestamp(end_date), RFM_LAST_DAY) + pd.Timedelta(days=1)
    rfm_df = df[df["order_purchase_timestamp"] < snapshot]
    if rfm_df.empty:
        st.warning("No orders in the selected range.")
        st.stop()
    rfm = rfm_table(rfm_df, snapshot)
    summary = (rfm.groupby("segment")
                  .agg(customers=("customer_unique_id", "count"), avg_recency_days=("recency", "mean"),
                       avg_monetary=("monetary", "mean"), total_revenue=("monetary", "sum"))
                  .reindex(SEGMENT_ORDER))
    summary["pct_customers"] = summary["customers"] / summary["customers"].sum() * 100
    summary["pct_revenue"] = summary["total_revenue"] / summary["total_revenue"].sum() * 100

    fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))
    cols = [SEGMENT_COLORS[s] for s in summary.index]
    axes[0].bar(summary.index, summary["customers"], color=cols)
    axes[0].bar_label(axes[0].containers[0], labels=[f"{v:,.0f}\n({p:.0f}%)" for v, p in zip(summary["customers"], summary["pct_customers"])], padding=3)
    axes[0].set_ylim(0, summary["customers"].max() * 1.25); axes[0].set_title("Number of customers")
    axes[1].bar(summary.index, summary["pct_revenue"], color=cols)
    axes[1].bar_label(axes[1].containers[0], fmt="%.1f%%", padding=3)
    axes[1].set_ylim(0, summary["pct_revenue"].max() * 1.25); axes[1].set_title("Revenue contribution (%)")
    for ax in axes:
        ax.tick_params(axis="x", rotation=15)
    plt.tight_layout(); st.pyplot(fig); plt.close(fig)

    st.dataframe(summary.round(1).rename_axis("segment").reset_index(), width="stretch", hide_index=True)
    st.markdown(
        "- **Champions**: recent and high spenders, so keep them with loyalty perks.\n"
        "- **At-Risk Big Spenders**: high spenders who have not purchased for a long time, the **first priority for win-back campaigns**.\n"
        "- **Potential Customers**: recent but low spenders, so raise their basket size (bundles, free-shipping thresholds).\n"
        "- **Lost Low-Value**: low spenders who are inactive, so use low-cost reactivation only.")
