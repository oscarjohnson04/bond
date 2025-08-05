import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fredapi import Fred
import datetime as dt
import requests

# Initialize FRED
fred = Fred(api_key='00edddc751dd47fb05bd7483df1ed0a3')

start = dt.datetime(2015, 1, 1)
end = dt.datetime.now()

@st.cache_data(show_spinner=False)
def fetch_multiple_latest_series(series_ids):
    data = {}
    for name, code in series_ids.items():
        try:
            series = fred.get_series(code, start, end)
            data[name] = series.iloc[-1]
        except:
            data[name] = np.nan
    return data

sidebar_series_ids = {
    "Real GDP (In Billions)": "GDPC1",
    "Unemployment Rate": "DGS3MO",
    "CPI": "MEDCPIM158SFRBCLE",
    "Debt/GDP Ratio": "GFDEGDQ188S",
    "Federal Reserve Interest Rate": "DFEDTARU",
    "Federal Funds Rate": "DFF",
    "3 month T-Bill yield": "DGS3MO",
    "10 year bond yield": "DGS10",
    "30 year bond yield": "DGS30",
    "Moody's AAA Corporate Bond Yield": "DAAA",
    "VIX": "VIXCLS",
    "US Economic Policy Uncertainty": "USEPUINDXD",
    "Global Economic Policy Uncertainty": "GEPUCURRENT"
}

latest_data = fetch_multiple_latest_series(sidebar_series_ids)

for label, value in latest_data.items():
    suffix = "%" if "Rate" in label or "Yield" in label or "CPI" in label else ""
    prefix = "$" if "GDP" in label else ""
    st.sidebar.metric(label, f"{prefix}{value:.2f}{suffix}")

# All available Treasury series
series_ids = {
    '1 Month': 'DGS1MO',
    '3 Month': 'DGS3MO',
    '6 Month': 'DGS6MO',
    '1 Year': 'DGS1',
    '2 Year': 'DGS2',
    '3 Year': 'DGS3',
    '5 Year': 'DGS5',
    '7 Year': 'DGS7',
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

st.title("US Treasury Yield and other bonds Explorer")

# Tabs for the two functionalities
tab1, tab2, tab3 = st.tabs(["Yield Curve on Selected Date", "Historical Yields", "News"])

# --------------------------------------------------------
# Tab 1: Yield Curve on Selected Date
# --------------------------------------------------------
with tab1:
    st.subheader("Yield Curve on a Specific Date")

    # Smart default date (weekday)
    today = dt.datetime.today()
    if today.weekday() >= 5:
        today -= dt.timedelta(days=today.weekday() - 4)

    date1 = st.date_input("Select first date", value=today, min_value=dt.date(2002, 1, 1), key="date1")
    date2 = st.date_input("Select second date", value=today - dt.timedelta(days=365), min_value=dt.date(2002, 1, 1), key="date2")

    date1 = pd.to_datetime(date1)
    date2 = pd.to_datetime(date2)
    
    @st.cache_data(show_spinner=False)
    def fetch_yield_curve(date):
        data = {}
        for label, code in series_ids.items():
            try:
                value = fred.get_series(code).get(date, np.nan)
            except:
                value = np.nan
            data[label] = value
        return pd.DataFrame([data])

    df1 = fetch_yield_curve(date1)
    df2 = fetch_yield_curve(date2)

    df1_t = df1.T.reset_index()
    df1_t.columns = ['Maturity', 'Rate1']

    df2_t = df2.T.reset_index()
    df2_t.columns = ['Maturity', 'Rate2']

    df_combined = pd.merge(df1_t, df2_t, on='Maturity')

    st.dataframe(df_combined.set_index("Maturity"), use_container_width=True)

    # Plot both curves
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_combined['Maturity'],
        y=df_combined['Rate1'],
        mode='lines+markers',
        name=f'Yields on {date1.strftime("%Y-%m-%d")}',
        line=dict(color='royalblue')
    ))
    fig.add_trace(go.Scatter(
        x=df_combined['Maturity'],
        y=df_combined['Rate2'],
        mode='lines+markers',
        name=f'Yields on {date2.strftime("%Y-%m-%d")}',
        line=dict(color='firebrick')
    ))

    fig.update_layout(
        title='US Treasury Yield Curves Comparison',
        xaxis_title='Maturity',
        yaxis_title='Yield (%)',
        template='plotly_white'
    )

    st.plotly_chart(fig, use_container_width=True)

    csv_curve = df_combined.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download yield curve data as CSV",
        data=csv_curve,
        file_name=f'yield_curve_comparison_{date1.date()}_vs_{date2.date()}.csv',
        mime='text/csv'
    )

# --------------------------------------------------------
# Tab 2: Historical Yield Plotter
# --------------------------------------------------------
with tab2:
    st.subheader("Historical Yield Plotter. Please only select two bonds.")

    selected_bonds_hist = st.multiselect(
        "Choose bonds to plot over time:",
        options=list(yield_series_ids.keys()),
        default=["US 10 Year", "US 1 Year"]
    )

    start_date = st.date_input("Start date", value=dt.date(2015, 1, 1), key="start_date")
    end_date = st.date_input("End date", value=dt.date.today(), key="end_date")

    if start_date >= end_date:
        st.warning("Start date must be before end date.")
    elif selected_bonds_hist:
        @st.cache_data(show_spinner=True)
        def fetch_historical_yields(start_date, end_date, selected_bonds):
            df = pd.DataFrame()
            for label in selected_bonds:
                code = yield_series_ids[label]
                try:
                    series = fred.get_series(code, start_date, end_date).rename(label)
                    df = pd.concat([df, series], axis=1)
                except:
                    continue
            return df

        df_hist = fetch_historical_yields(start_date, end_date, selected_bonds_hist)

        if len(df_hist.columns) == 2:
            df_hist['Spread'] = df_hist.iloc[:, 0] - df_hist.iloc[:, 1]
            
        st.dataframe(df_hist.tail(), use_container_width=True)

        fig_hist = go.Figure()
        for label in df_hist.columns:
            if label != 'Spread':
                fig_hist.add_trace(go.Scatter(
                x=df_hist.index,
                y=df_hist[label],
                mode='lines',
                name=label
                ))

        fig_hist.update_layout(
            title="Historical Treasury Yields",
            xaxis_title="Date",
            yaxis_title="Yield (%)",
            template="plotly_white"
        )
        st.plotly_chart(fig_hist, use_container_width=True)

        if 'Spread' in df_hist.columns:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=df_hist.index,
                y=df_hist['Spread'],
                mode='lines',
                name='Yield Spread'
            ))

            fig2.update_layout(
                title="Yield Spread of Your Selected Bonds",
                xaxis_title="Date",
                yaxis_title="Spread (%)",
                template="plotly_white"
            )
            st.plotly_chart(fig2, use_container_width=True)
            
    else:
        st.info("Select at least one bond maturity to plot historical yields.")

    csv = df_hist.to_csv().encode('utf-8')
    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name='historical_yields.csv',
        mime='text/csv'
    )

with tab3:
    st.subheader("Latest News on Bonds, Rates & Macro")

    # --- Config / API Key ---
    NEWS_API_KEY = "80f3080a10da4d91809c5e53cf0d9828"

    # --- Controls ---
    colq1, colq2, colq3 = st.columns([2, 1, 1])
    with colq1:
        query = st.text_input("Search query", value="US Treasury yields OR bond market OR Federal Reserve")
    with colq2:
        page_size = st.number_input("Articles to show", min_value=3, max_value=30, value=10, step=1)
    with colq3:
        sort_by = st.selectbox("Sort by", options=["publishedAt", "relevancy", "popularity"], index=0)

    c1, c2 = st.columns(2)
    with c1:
        from_date = st.date_input("From date (optional)", value=None, key="news_from")
    with c2:
        to_date = st.date_input("To date (optional)", value=None, key="news_to")

    st.caption("Tip: On the free NewsAPI tier, coverage is generally the last ~30 days.")

    # --- Fetcher ---
    @st.cache_data(show_spinner=True, ttl=60 * 15)  # cache 15 minutes
    def fetch_news(query, page_size, sort_by, from_date, to_date):
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "language": "en",
            "pageSize": int(page_size),
            "sortBy": sort_by,
            "apiKey": NEWS_API_KEY
        }
        # Only include dates if provided (NewsAPI expects YYYY-MM-DD)
        if from_date:
            params["from"] = str(from_date)
        if to_date:
            params["to"] = str(to_date)

        try:
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            payload = r.json()
            status = payload.get("status", "error")
            if status != "ok":
                return [], f"NewsAPI error: {payload.get('message', 'Unknown error')}"
            return payload.get("articles", []), None
        except Exception as e:
            return [], f"Request failed: {e}"

    # --- Call API ---
    articles, err = fetch_news(query, page_size, sort_by, from_date, to_date)

    if err:
        st.error(err)
    elif not articles:
        st.info("No articles found. Try adjusting your query or date range.")
    else:
        # Optional: compact toggle
        compact = st.toggle("Compact view", value=False)

        for a in articles:
            title = a.get("title") or "Untitled"
            url = a.get("url") or ""
            source = (a.get("source") or {}).get("name") or "Unknown source"
            published = (a.get("publishedAt") or "")[:10]
            desc = a.get("description") or ""
            thumb = a.get("urlToImage")

            if compact:
                # Single-line compact card
                st.markdown(
                    f"- **[{title}]({url})** — {source} · {published}"
                )
            else:
                with st.container(border=True):
                    if thumb:
                        colA, colB = st.columns([1, 3])
                        with colA:
                            st.image(thumb, use_column_width=True)
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
