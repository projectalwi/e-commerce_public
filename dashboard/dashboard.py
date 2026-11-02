"""E-Commerce Public Dashboard (Streamlit).

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

# navigation entries: the emoji works as the icon of each menu item
PAGE_HOME = "🏠  Overview"
PAGE_QUALITY = "⭐  Product Quality"
PAGE_REVENUE = "📈  Revenue Trend & Forecast"
PAGE_RFM = "👥  Customer Segments (RFM)"
PAGES = [PAGE_HOME, PAGE_QUALITY, PAGE_REVENUE, PAGE_RFM]

st.set_page_config(page_title="E-Commerce Public Dashboard", page_icon="🛒", layout="wide")

# ----------------------------------------------------------------------------- styling
st.markdown(
    """
    <style>
    /* navigation items: left aligned, rounded, coloured when hovered or selected */
    section[data-testid="stSidebar"] div[role="radiogroup"] { gap: 0.25rem; }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label {
        width: 100%;
        padding: 0.55rem 0.8rem;
        border-radius: 0.5rem;
        cursor: pointer;
        transition: background-color 0.2s ease, transform 0.2s ease;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
        background-color: rgba(41, 128, 185, 0.22);
        transform: translateX(3px);
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
        background-color: rgba(41, 128, 185, 0.38);
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


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


@st.cache_data
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

# ----------------------------------------------------------------------------- data loading
try:
    data = load_data()
except FileNotFoundError:
    st.error(f"`{DATA_PATH.name}` was not found. Run the last cell of the notebook to export it.")
    st.stop()

# ----------------------------------------------------------------------------- sidebar
with st.sidebar:
    # 1. centered title + small caption
    st.markdown("<h2 style='text-align:center; margin-bottom:0;'>Dashboard Menu</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; font-size:0.85rem; opacity:0.7; margin-top:0.2rem;'>"
                "Pick a page to explore the e-commerce analysis</p>", unsafe_allow_html=True)

    # 2. divider between the header and the (left aligned) navigation
    st.divider()

    # 3. navigation bar with icons
    page = st.radio("Navigation", PAGES, key="page", label_visibility="collapsed")

    st.divider()

    # 4. page specific controls, each one chosen to suit its visualization
    if page == PAGE_QUALITY:
        st.markdown("**⚙️ Quality options**")
        sort_label = st.selectbox("Rank categories by", [
            "Priority (score + bad review %)", "Lowest average score",
            "Highest bad review %", "Most bad-review orders"])
        top_n = st.slider("Categories to show", 5, 20, 10)
        min_orders = st.slider("Minimum reviewed orders", 30, 500, 100, step=10)
    elif page == PAGE_REVENUE:
        st.markdown("**⚙️ Revenue options**")
        show_ma = st.checkbox("Show 3-month moving average", value=True)
        show_forecast = st.checkbox("Show 2-quarter forecast", value=True)
        show_top5 = st.checkbox("Show top 5 categories chart", value=True)
        chosen_categories = st.multiselect("Filter categories (empty = all)",
                                           sorted(data["product_category_name_english"].unique()),
                                           placeholder="Choose categories")
    elif page == PAGE_RFM:
        st.markdown("**⚙️ Segment options**")
        chosen_segments = st.multiselect("Segments to display", SEGMENT_ORDER, default=SEGMENT_ORDER)
        show_table = st.checkbox("Show segment summary table", value=True)

    # global date filter
    with st.expander("📅 Purchase date filter", expanded=False):
        date_range = st.date_input("Purchase date range", value=(MIN_DATE.date(), MAX_DATE.date()),
                                   min_value=MIN_DATE.date(), max_value=MAX_DATE.date())
        st.caption("Revenue trend uses Jan 2017 - Aug 2018 and RFM uses Sep 2016 - Sep 2018, "
                   "because the other months are incomplete.")

# st.date_input returns one date while the user is still picking the second one
start_date, end_date = date_range if len(date_range) == 2 else (date_range[0], MAX_DATE.date())
mask = (data["order_purchase_timestamp"] >= pd.Timestamp(start_date)) & \
       (data["order_purchase_timestamp"] < pd.Timestamp(end_date) + pd.Timedelta(days=1))
df = data[mask]

# ----------------------------------------------------------------------------- main header (centered)
st.markdown("<h1 style='text-align:center; margin-bottom:0;'>E-Commerce Public Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; opacity:0.7;'>Brazilian marketplace, September 2016 - September 2018. "
            "Revenue = product price + freight.</p>", unsafe_allow_html=True)
st.divider()

if df.empty:
    st.warning("No data in the selected range.")
    st.stop()


# ----------------------------------------------------------------------------- pages
def page_overview():
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total revenue", f"{df['revenue'].sum() / 1e6:.2f}M BRL")
    c2.metric("Orders", f"{df['order_id'].nunique():,}")
    c3.metric("Customers", f"{df['customer_unique_id'].nunique():,}")
    c4.metric("Avg review score", f"{df.drop_duplicates('order_id')['review_score'].mean():.2f}")
    st.markdown("### What can you explore?")
    a, b, c = st.columns(3)
    a.info("**⭐ Product Quality**\n\nWhich categories have the lowest scores and most bad reviews, and should be evaluated first?")
    b.info("**📈 Revenue Trend & Forecast**\n\nHow monthly revenue changes per category and what to expect in the next two quarters.")
    c.info("**👥 Customer Segments (RFM)**\n\nWhich customer groups bring the most revenue and which should be retained or won back.")


def page_quality():
    st.subheader("Which product categories need a quality evaluation first?")
    quality = category_quality(df, min_orders)
    if quality.empty:
        st.warning("No category has enough reviewed orders. Lower the minimum in the sidebar.")
        return
    sorters = {
        "Priority (score + bad review %)": None,
        "Lowest average score": ("avg_review_score", True),
        "Highest bad review %": ("bad_review_pct", False),
        "Most bad-review orders": ("bad_orders", False),
    }
    if sorters[sort_label]:
        col, asc = sorters[sort_label]
        quality = quality.sort_values(col, ascending=asc).reset_index(drop=True)

    overall = df.dropna(subset=["review_score"]).drop_duplicates("order_id")
    overall_avg, overall_bad = overall["review_score"].mean(), (overall["review_score"] <= 2).mean() * 100

    top = quality.head(top_n)
    labels = top["product_category_name_english"] + " (n=" + top["total_orders"].astype(str) + ")"
    colors = ["#c0392b" if i < 3 else "#95a5a6" for i in range(len(top))]
    fig, axes = plt.subplots(1, 2, figsize=(14, 0.55 * len(top) + 2), sharey=True)
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
    st.pyplot(fig)
    plt.close(fig)
    st.dataframe(top.drop(columns="priority_rank").round(2), width="stretch", hide_index=True)
    st.info("The three red bars are the first in the chosen ranking. Categories with a small sample (n < 150) "
            "should be monitored before taking large action.")


def page_revenue():
    st.subheader("How does monthly revenue change, and what can we expect next?")
    # Same window as the notebook: Sep-Dec 2016 (5 orders) and Sep 2018 (16 orders) are incomplete months
    trend_df = df[(df["order_purchase_timestamp"] >= "2017-01-01") & (df["order_purchase_timestamp"] < "2018-09-01")]
    if trend_df.empty:
        st.warning("The selected date range has no complete months between January 2017 and August 2018.")
        return
    default_top5 = trend_df.groupby("product_category_name_english")["revenue"].sum().nlargest(5).index.tolist()
    view = trend_df[trend_df["product_category_name_english"].isin(chosen_categories)] if chosen_categories else trend_df

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
        if show_ma:
            ax.plot(ma3.index.to_timestamp(), ma3.values, color="#e67e22", linewidth=2.5, label="3-month moving average")
        if show_forecast:
            ax.plot(future.to_timestamp(), np.repeat(forecast_value, horizon), "--o", color="#27ae60",
                    label="Forecast (3-month MA, flat)")
            ax.fill_between(future.to_timestamp(), forecast_value * (1 - error_band), forecast_value * (1 + error_band),
                            color="#27ae60", alpha=0.2, label=f"Error band (+/-{error_band * 100:.0f}%)")
        ax.yaxis.set_major_formatter(million)
        ax.set_xlabel("Month"); ax.set_ylabel("Revenue (BRL)"); ax.legend(loc="upper left")
        plt.tight_layout(); st.pyplot(fig); plt.close(fig)

        quarter_fc = forecast_value * 3
        m1, m2, m3 = st.columns(3)
        m1.metric(f"Forecast {future[0].strftime('%b %Y')} - {future[2].strftime('%b %Y')}", f"{quarter_fc / 1e6:.2f}M BRL",
                  f"range {quarter_fc * (1 - error_band) / 1e6:.2f}-{quarter_fc * (1 + error_band) / 1e6:.2f}M", delta_color="off")
        m2.metric(f"Forecast {future[3].strftime('%b %Y')} - {future[5].strftime('%b %Y')}", f"{quarter_fc / 1e6:.2f}M BRL",
                  f"range {quarter_fc * (1 - error_band) / 1e6:.2f}-{quarter_fc * (1 + error_band) / 1e6:.2f}M", delta_color="off")
        last_mom = (monthly.iloc[-1] / monthly.iloc[-2] - 1) * 100
        m3.metric("Last month vs previous month", f"{monthly.iloc[-1] / 1e6:.2f}M BRL", f"{last_mom:+.1f}%")
        st.info("The forecast is a flat baseline (average of the last 3 months). It does not include seasonality: "
                "November 2017 jumped 53% over October, so November 2018 may be higher. In a backtest this method "
                "had 9-13% error versus 24-35% for a linear trend, because growth slowed after March 2018.")

    if show_top5:
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


def page_rfm():
    st.subheader("Which customer groups should we retain or win back?")
    st.caption("Recency = days since last purchase, Monetary = total spending. Frequency is not used because ~97% "
               "of customers purchased only once. Scores are quartiles (4 = best).")
    snapshot = min(pd.Timestamp(end_date), RFM_LAST_DAY) + pd.Timedelta(days=1)
    rfm_source = df[df["order_purchase_timestamp"] < snapshot]
    if rfm_source.empty:
        st.warning("No orders in the selected range.")
        return
    rfm = rfm_table(rfm_source, snapshot)
    summary = (rfm.groupby("segment")
                  .agg(customers=("customer_unique_id", "count"), avg_recency_days=("recency", "mean"),
                       avg_monetary=("monetary", "mean"), total_revenue=("monetary", "sum"))
                  .reindex(SEGMENT_ORDER))
    summary["pct_customers"] = summary["customers"] / summary["customers"].sum() * 100
    summary["pct_revenue"] = summary["total_revenue"] / summary["total_revenue"].sum() * 100

    shown = summary.loc[[s for s in SEGMENT_ORDER if s in chosen_segments]]
    if shown.empty:
        st.warning("Choose at least one segment in the sidebar.")
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))
    cols = [SEGMENT_COLORS[s] for s in shown.index]
    axes[0].bar(shown.index, shown["customers"], color=cols)
    axes[0].bar_label(axes[0].containers[0], labels=[f"{v:,.0f}\n({p:.0f}%)" for v, p in zip(shown["customers"], shown["pct_customers"])], padding=3)
    axes[0].set_ylim(0, shown["customers"].max() * 1.25); axes[0].set_title("Number of customers")
    axes[1].bar(shown.index, shown["pct_revenue"], color=cols)
    axes[1].bar_label(axes[1].containers[0], fmt="%.1f%%", padding=3)
    axes[1].set_ylim(0, shown["pct_revenue"].max() * 1.25); axes[1].set_title("Revenue contribution (%)")
    for ax in axes:
        ax.tick_params(axis="x", rotation=15)
    plt.tight_layout(); st.pyplot(fig); plt.close(fig)

    if show_table:
        st.dataframe(shown.round(1).rename_axis("segment").reset_index(), width="stretch", hide_index=True)
    st.markdown(
        "- **Champions**: recent and high spenders, so keep them with loyalty perks.\n"
        "- **At-Risk Big Spenders**: high spenders who have not purchased for a long time, the **first priority for win-back campaigns**.\n"
        "- **Potential Customers**: recent but low spenders, so raise their basket size (bundles, free-shipping thresholds).\n"
        "- **Lost Low-Value**: low spenders who are inactive, so use low-cost reactivation only.")


{PAGE_HOME: page_overview, PAGE_QUALITY: page_quality, PAGE_REVENUE: page_revenue, PAGE_RFM: page_rfm}[page]()
