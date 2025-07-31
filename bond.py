import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fredapi import Fred
import datetime as dt

# FRED API setup
fred = Fred(api_key='00edddc751dd47fb05bd7483df1ed0a3')

# All available bond maturities
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

# --- Streamlit UI ---
st.title("📊 Custom US Treasury Yield Curve Viewer")

# Date picker
default_date = dt.datetime.today()
if default_date.weekday() >= 5:  # If weekend, set to Friday
    default_date -= dt.timedelta(days=default_date.weekday() - 4)
selected_date = st.date_input("Select date", value=default_date, min_value=dt.date(2002, 1, 1))
date = pd.to_datetime(selected_date)

# Bond selection
selected_bonds = st.multiselect(
    "Select bond maturities to display:",
    options=list(series_ids.keys()),
    default=list(series_ids.keys())  # Default: all selected
)

# If nothing is selected, don't proceed
if not selected_bonds:
    st.warning("Please select at least one bond maturity.")
    st.stop()

# --- Fetch data ---
@st.cache_data(show_spinner=False)
def fetch_selected_yields(date, selected_bonds):
    data = {}
    for label in selected_bonds:
        code = series_ids[label]
        try:
            value = fred.get_series(code).get(date, np.nan)
        except:
            value = np.nan
        data[label] = value
    return pd.DataFrame([data])

df = fetch_selected_yields(date, selected_bonds)

# --- Format data for plotting ---
df_t = df.T
df_t.columns = ['Rate']
df_t = df_t.reset_index().rename(columns={'index': 'Maturity'})

# Show table
st.subheader(f"Yield Data on {date.strftime('%Y-%m-%d')}")
st.dataframe(df_t.set_index("Maturity"), use_container_width=True)

# --- Plot ---
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
    title=f"US Treasury Yields on {date.strftime('%Y-%m-%d')}",
    xaxis_title='Maturity',
    yaxis_title='Yield (%)',
    template='plotly_white',
    height=500
)

st.plotly_chart(fig, use_container_width=True)
