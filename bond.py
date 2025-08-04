import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fredapi import Fred
import datetime as dt

# Initialize FRED
fred = Fred(api_key='00edddc751dd47fb05bd7483df1ed0a3')

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
    default_date = dt.datetime.today()
    if default_date.weekday() >= 5:
        default_date -= dt.timedelta(days=default_date.weekday() - 4)
    selected_date = st.date_input("Select a date", value=default_date, min_value=dt.date(2002, 1, 1))
    date = pd.to_datetime(selected_date)
    
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

    df = fetch_yield_curve(date)
    
    df_t = df.T
    df_t.columns = ['Rate']
    df_t = df_t.reset_index().rename(columns={'index': 'Maturity'})

    st.dataframe(df_t.set_index("Maturity"), use_container_width=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_t['Maturity'],
        y=df_t['Rate'],
        mode='lines+markers',
        line=dict(color='royalblue', width=3),
        marker=dict(size=8),
        name=f'Yields on {date.strftime("%Y-%m-%d")}'
    ))
    fig.update_layout(
        title=f'US Treasury Yield Curve on {date.strftime("%Y-%m-%d")}',
        xaxis_title='Maturity',
        yaxis_title='Yield (%)',
        template='plotly_white'
    )
    st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------------
# Tab 2: Historical Yield Plotter
# --------------------------------------------------------
with tab2:
    st.subheader("Historical Yield Plotter")

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
        for label in df_hist.columns:
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
