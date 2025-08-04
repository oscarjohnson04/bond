import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fredapi import Fred
import datetime as dt

# Initialize FRED
fred = Fred(api_key='00edddc751dd47fb05bd7483df1ed0a3')

start = dt.datetime(2015, 1, 1)
end = dt.datetime.now()

realgdp = fred.get_series('GDPC1', start, end).iloc[-1]
unrate = fred.get_series('DGS3MO', start, end).iloc[-1]
cpi = fred.get_series('MEDCPIM158SFRBCLE', start, end).iloc[-1]
debtgdp = fred.get_series('GFDEGDQ188S', start, end).iloc[-1]
fedrate = fred.get_series('DFEDTARU', start, end).iloc[-1]
fedfundrate = fred.get_series('DFF', start, end).iloc[-1]
trate = fred.get_series('DGS3MO', start, end).iloc[-1]
tenrate = fred.get_series('DGS10', start, end).iloc[-1]
longrate = fred.get_series('DGS30', start, end).iloc[-1]
corprate = fred.get_series('DAAA', start, end).iloc[-1]
vix = fred.get_series('VIXCLS', start, end).iloc[-1]
usu = fred.get_series('USEPUINDXD', start, end).iloc[-1]
gu = fred.get_series('GEPUCURRENT', start, end).iloc[-1]

st.sidebar.title("Latest US Macro Data")
st.sidebar.metric("Real GDP (In Billions)", f"${realgdp:.2f}")
st.sidebar.metric("Unemployment Rate", f"{unrate:.2f}%")
st.sidebar.metric("CPI", f"{cpi:.2f}%")
st.sidebar.metric("Debt/GDP Ratio", f"{debtgdp:.2f}")
st.sidebar.metric("Federal Reserve Interest Rate", f"{fedrate:.2f}%")
st.sidebar.metric("Federal Funds Rate", f"{fedfundrate:.2f}%")
st.sidebar.metric("3 month T-Bill yield", f"{trate:.2f}%")
st.sidebar.metric("10 year bond yield", f"{tenrate:.2f}%")
st.sidebar.metric("30 year bond yield", f"{longrate:.2f}%")
st.sidebar.metric("Moody's AAA Corporate Bond Yield", f"{corprate:.2f}%")
st.sidebar.metric("VIX", f"{vix:.2f}")
st.sidebar.metric("US Economic Policy Uncertainty", f"{usu:.2f}")
st.sidebar.metric("Global Economic Policy Uncertainty", f"{gu:.2f}")

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
tab1, tab2 = st.tabs(["Yield Curve on Selected Date", "Historical Yields"])

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

        df_hist['Spread'] = df_hist.iloc[:,0] - df_hist.iloc[:,1]

        st.dataframe(df_hist.tail(), use_container_width=True)

        fig_hist = go.Figure()
        for label in df_hist.columns[:-1]:
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

        fig2= go.Figure()
        fig2.add_trace(go.Scatter(
            x=df_hist.index,
            y=df_hist['Spread'],
            mode='lines',
            name='Yield Spread'
        ))

        fig2.update_layout(
            title = "Yield Spread of your Selected Bonds",
            xaxis_title = "Date", 
            yaxis_title = "Spread",
            template="plotly_white"
        )

        st.plotly_chart(fig2, use_container_width=True)
            
    else:
        st.info("Select at least one bond maturity to plot historical yields.")
