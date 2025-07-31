import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fredapi import Fred
import datetime as dt

# Initialize FRED
fred = Fred(api_key='00edddc751dd47fb05bd7483df1ed0a3')

# --- Streamlit UI ---
st.title("📈 US Treasury Yield Curve Explorer")
st.write("Select a date to view the yield curve for US Treasuries.")

# Date picker (default: recent weekday)
default_date = dt.datetime.today()
if default_date.weekday() >= 5:  # if Saturday or Sunday
    default_date -= dt.timedelta(days=default_date.weekday() - 4)  # move to Friday

selected_date = st.date_input("Select date", value=default_date, min_value=dt.date(2002, 1, 1))
date = pd.to_datetime(selected_date)

# Series codes for Treasury maturities
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

# --- Fetch Data ---
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

# Transpose for plotting
df_t = df.T
df_t.columns = ['Rate']
df_t = df_t.reset_index().rename(columns={'index': 'Maturity'})

# --- Display Results ---
st.subheader(f"Yield Curve on {date.strftime('%Y-%m-%d')}")
st.dataframe(df_t.set_index("Maturity"), use_container_width=True)

# Plot
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=df_t['Maturity'],
    y=df_t['Rate'],
    mode='lines+markers',
    line=dict(color='royalblue', width=3),
    marker=dict(size=8),
    name=f'Yield Curve on {date.strftime("%Y-%m-%d")}'
))

fig.update_layout(
    xaxis_title='Maturity',
    yaxis_title='Yield (%)',
    template='plotly_white',
    height=500
)

st.plotly_chart(fig, use_container_width=True)
