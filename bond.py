import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fredapi import Fred
import datetime as dt
import requests

st.set_page_config(page_title="US Yields & Macro Explorer", layout="wide")
st.title("US Yields & Macro Explorer")
tab1, tab2, tab3 = st.tabs(["Yield Curve on Selected Date", "Historical Yields", "News"])

# =========================
# CONFIG / CLIENTS
# =========================
FRED_API_KEY = "00edddc751dd47fb05bd7483df1ed0a3"
NEWS_API_KEY = "80f3080a10da4d91809c5e53cf0d9828"

fred = Fred(api_key=FRED_API_KEY)
START = dt.date(2015, 1, 1)
END = dt.date.today()


# =========================
# HELPERS (CACHED)
# =========================
@st.cache_data(show_spinner=False)
def fetch_multiple_latest_series(series_ids: dict, start: dt.date, end: dt.date) -> dict:
    """Fetch the last available value for each series id in series_ids."""
    out = {}
    for label, code in series_ids.items():
        try:
            s = fred.get_series(code, start, end)
            if len(s) == 0:
                out[label] = np.nan
            else:
                out[label] = float(s.iloc[-1])
        except Exception:
            out[label] = np.nan
    return out

@st.cache_data(show_spinner=False)
def fetch_yield_curve_for_date(date_: dt.date, series_map: dict) -> pd.DataFrame:
    """
    Return single-row DataFrame of yields on or before the given date (nearest available value up to that date).
    """
    row = {}
    for label, code in series_map.items():
        try:
            s = fred.get_series(code)
            # take last available value up to date_
            s = s[:pd.Timestamp(date_)]
            val = float(s.dropna().iloc[-1]) if not s.dropna().empty else np.nan
        except Exception:
            val = np.nan
        row[label] = val
    return pd.DataFrame([row])

@st.cache_data(show_spinner=True)
def fetch_historical_yields(start: dt.date, end: dt.date, selected_labels: list, id_map: dict) -> pd.DataFrame:
    """
    Return a DataFrame of selected series between start and end (inner-joined on the index).
    """
    df = pd.DataFrame()
    for label in selected_labels:
        code = id_map[label]
        try:
            s = fred.get_series(code, start, end).rename(label)
            df = pd.concat([df, s], axis=1)
        except Exception:
            # skip failing series
            continue
    return df

@st.cache_data(show_spinner=True, ttl=60 * 15)
def fetch_news(query: str, page_size: int, sort_by: str, use_dates: bool, from_date, to_date):
    """
    Fetch news from NewsAPI's /everything endpoint. Optionally filter by date.
    """
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "en",
        "pageSize": int(page_size),
        "sortBy": sort_by,
        "apiKey": NEWS_API_KEY
    }
    if use_dates and from_date:
        params["from"] = str(from_date)
    if use_dates and to_date:
        params["to"] = str(to_date)

    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        payload = r.json()
        if payload.get("status") != "ok":
            return [], f"NewsAPI error: {payload.get('message', 'Unknown error')}"
        return payload.get("articles", []), None
    except Exception as e:
        return [], f"Request failed: {e}"

# =========================
# SERIES MAPS
# =========================
treasury_series = {
    '1 Month': 'DGS1MO',
    '3 Month': 'DGS3MO',
    '6 Month': 'DGS6MO',
    '1 Year':  'DGS1',
    '2 Year':  'DGS2',
    '3 Year':  'DGS3',
    '5 Year':  'DGS5',
    '7 Year':  'DGS7',
    '10 Year': 'DGS10',
    '20 Year': 'DGS20',
    '30 Year': 'DGS30'
}

yield_series_ids = {
    'Federal Funds Rate': 'DFF',
    'US 1 Month': 'DGS1MO',
    'US 3 Month': 'DGS3MO',
    'US 6 Month': 'DGS6MO',
    'US 1 Year': 'DGS1',
    'US 2 Year': 'DGS2',
    'US 3 Year': 'DGS3',
    'US 5 Year': 'DGS5',
    'US 7 Year': 'DGS7',
    'US 10 Year': 'DGS10',
    'US 20 Year': 'DGS20',
    'US 30 Year': 'DGS30',
    'Moody AAA Corporate': 'DAAA',
    'Moody BAA Corporate': 'DBAA',
    'ICE BofA BBB Corporate': 'BAMLC0A4CBBBEY',
    'ICE BofA CCC Corporate': 'BAMLH0A3HYCEY',
}

sidebar_series_ids = {
    "Real GDP (Billions, chained 2017$)": "GDPC1",
    "Unemployment Rate": "UNRATE",
    "Core Median CPI": "MEDCPIM158SFRBCLE",
    "Debt/GDP Ratio": "GFDEGDQ188S",
    "Fed Target Upper Bound": "DFEDTARU",
    "Effective Fed Funds Rate": "DFF",
    "3M T-Bill Yield": "DGS3MO",
    "10Y Treasury Yield": "DGS10",
    "30Y Treasury Yield": "DGS30",
    "Moody's AAA Corp Yield": "DAAA",
    "VIX": "VIXCLS",
    "US Econ Policy Uncertainty": "USEPUINDXD",
    "Global Econ Policy Uncertainty": "GEPUCURRENT"
}

# =========================
# SIDEBAR: LATEST METRICS
# =========================
st.sidebar.title("Latest US Macro Data")
latest_data = fetch_multiple_latest_series(sidebar_series_ids, START, END)
for label, value in latest_data.items():
    suffix = "%" if any(k in label.lower() for k in ["rate", "yield", "cpi", "target"]) else ""
    prefix = "$" if "real gdp" in label.lower() else ""
    if np.isnan(value):
        st.sidebar.metric(label, "N/A")
    else:
        st.sidebar.metric(label, f"{prefix}{value:,.2f}{suffix}")

# =========================
# TABS
# =========================

# ---------------- TAB 1 ----------------
with tab1:
    st.subheader("Yield Curve on Selected Dates")

    # Smart weekday default for today
    today = dt.date.today()
    if today.weekday() >= 5:  # Sat/Sun -> move back to Friday
        today = today - dt.timedelta(days=today.weekday() - 4)

    c1, c2 = st.columns(2)
    with c1:
        date1 = st.date_input("First date", value=today, min_value=dt.date(2002, 1, 1), key="yc_d1")
    with c2:
        date2 = st.date_input("Second date", value=today - dt.timedelta(days=365), min_value=dt.date(2002, 1, 1), key="yc_d2")

    df1 = fetch_yield_curve_for_date(date1, treasury_series)
    df2 = fetch_yield_curve_for_date(date2, treasury_series)

    df1_t = df1.T.reset_index()
    df1_t.columns = ['Maturity', 'Rate1']
    df2_t = df2.T.reset_index()
    df2_t.columns = ['Maturity', 'Rate2']

    df_combined = pd.merge(df1_t, df2_t, on='Maturity')

    st.dataframe(df_combined.set_index("Maturity"), use_container_width=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_combined['Maturity'], y=df_combined['Rate1'],
        mode='lines+markers', name=f"{date1}",
    ))
    fig.add_trace(go.Scatter(
        x=df_combined['Maturity'], y=df_combined['Rate2'],
        mode='lines+markers', name=f"{date2}",
    ))
    fig.update_layout(
        title="US Treasury Yield Curves Comparison",
        xaxis_title="Maturity", yaxis_title="Yield (%)", template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)

    # Download
    csv_curve = df_combined.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download yield curve data (CSV)",
        data=csv_curve,
        file_name=f"yield_curve_{date1}_vs_{date2}.csv",
        mime="text/csv"
    )

# ---------------- TAB 2 ----------------
with tab2:
    st.subheader("Historical Yield Plotter")

    selected_bonds = st.multiselect(
        "Choose bonds/series to plot",
        options=list(yield_series_ids.keys()),
        default=["US 10 Year", "US 1 Year"]
    )

    col_left, col_right = st.columns(2)
    with col_left:
        start_date = st.date_input("Start date", value=START, key="hist_start")
    with col_right:
        end_date = st.date_input("End date", value=END, key="hist_end")

    if start_date >= end_date:
        st.warning("Start date must be before end date.")
    elif len(selected_bonds) == 0:
        st.info("Select at least one series to plot.")
    else:
        df_hist = fetch_historical_yields(start_date, end_date, selected_bonds, yield_series_ids)

        # Only compute spread when exactly two series are present
        if df_hist.shape[1] == 2:
            df_hist['Spread'] = df_hist.iloc[:, 0] - df_hist.iloc[:, 1]

        st.dataframe(df_hist.tail(), use_container_width=True)

        # Plot all series except 'Spread'
        fig_hist = go.Figure()
        for col in df_hist.columns:
            if col != "Spread":
                fig_hist.add_trace(go.Scatter(x=df_hist.index, y=df_hist[col], mode="lines", name=col))
        fig_hist.update_layout(
            title="Historical Yields",
            xaxis_title="Date", yaxis_title="Yield (%)", template="plotly_white"
        )
        st.plotly_chart(fig_hist, use_container_width=True)

        # Plot spread if exists
        if "Spread" in df_hist.columns:
            fig_spread = go.Figure()
            fig_spread.add_trace(go.Scatter(x=df_hist.index, y=df_hist["Spread"], mode="lines", name="Spread"))
            fig_spread.update_layout(
                title=f"Spread: {df_hist.columns[0]} - {df_hist.columns[1]}",
                xaxis_title="Date", yaxis_title="Spread (pp)", template="plotly_white"
            )
            st.plotly_chart(fig_spread, use_container_width=True)

        # Download
        csv_hist = df_hist.to_csv().encode("utf-8")
        st.download_button(
            label="Download historical data (CSV)",
            data=csv_hist,
            file_name="historical_yields.csv",
            mime="text/csv"
        )

# ---------------- TAB 3 ----------------
with tab3:
    st.subheader("Latest News on Bonds, Rates & Macro")

    colq1, colq2, colq3 = st.columns([2, 1, 1])
    with colq1:
        query = st.text_input("Search query", value="US Treasury yields OR bond market OR Federal Reserve")
    with colq2:
        page_size = st.number_input("Articles to show", min_value=3, max_value=30, value=10, step=1)
    with colq3:
        sort_by = st.selectbox("Sort by", ["Date", "Relevancy", "Popularity"], index=0)

    use_dates = st.toggle("Filter by date range", value=False)
    if use_dates:
        c1, c2 = st.columns(2)
        with c1:
            from_date = st.date_input("From date", value=dt.date.today() - dt.timedelta(days=30), key="news_from")
        with c2:
            to_date = st.date_input("To date", value=dt.date.today(), key="news_to")
        if from_date > to_date:
            st.warning("'From date' must be on or before 'To date'.")
    else:
        from_date = None
        to_date = None

    articles, err = fetch_news(query, page_size, sort_by, use_dates, from_date, to_date)

    if err:
        st.error(err)
    elif not articles:
        st.info("No articles found. Try adjusting your query or date range.")
    else:
        compact = st.toggle("Compact view", value=False)
        for a in articles:
            title = a.get("title") or "Untitled"
            url = a.get("url") or ""
            source = (a.get("source") or {}).get("name") or "Unknown source"
            published = (a.get("Date") or "")[:10]
            desc = a.get("description") or ""
            thumb = a.get("urlToImage")

            if compact:
                st.markdown(f"- **[{title}]({url})** — {source} · {published}")
            else:
                with st.container(border=True):
                    if thumb:
                        colA, colB = st.columns([1, 3])
                        with colA:
                            st.image(thumb, use_container_width=True)
                        with colB:
                            st.markdown(f"### [{title}]({url})")
                            st.caption(f"{source} · {published}")
                            if desc:
                                st.write(desc)
                    else:
                        st.markdown(f"### [{title}]({url})")
                        st.caption(f"{source} · {published}")
                        if desc:
                            st.write(desc)

