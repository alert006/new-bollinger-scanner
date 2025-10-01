import streamlit as st
import pandas as pd
import yfinance as yf
from plotly import graph_objects as go
from plotly.subplots import make_subplots

# --- Configuration and Setup ---
# Use the full width of the browser
st.set_page_config(layout="wide")

# Custom CSS for aesthetics
st.markdown("""
    <style>
    /* Styling for the main header */
    .stApp > header {
        background-color: #0e1117; 
        color: white; 
    }
    .main-header {
        font-size: 2.5em;
        font-weight: 700;
        color: #1f77b4; /* Streamlit's primary color */
        text-align: center;
        margin-bottom: 20px;
        padding: 10px;
        border-bottom: 3px solid #1f77b4;
    }
    /* Styling for the input widgets */
    .stTextInput label, .stNumberInput label {
        font-weight: 600;
        color: #f0f2f6;
    }
    /* Styling for the data summary table */
    .dataframe th {
        background-color: #1f77b4;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)


# --- Core Logic Functions ---

def get_data(ticker, start_date, end_date):
    """Fetches stock data using yfinance."""
    try:
        data = yf.download(ticker, start=start_date, end=end_date)
        return data
    except Exception as e:
        st.error(f"Error fetching data for {ticker}: {e}")
        return pd.DataFrame()

def calculate_bollinger_bands(df, window=20, num_std_dev=2):
    """Calculates Middle Band (SMA), Upper Band, and Lower Band."""
    if 'Close' not in df.columns or len(df) < window:
        return df

    # Calculate 20-day Simple Moving Average (SMA) - Middle Band
    df['Middle_Band'] = df['Close'].rolling(window=window).mean()

    # Calculate 20-day Standard Deviation
    df['STD'] = df['Close'].rolling(window=window).std()

    # Calculate Upper and Lower Bands
    df['Upper_Band'] = df['Middle_Band'] + (df['STD'] * num_std_dev)
    df['Lower_Band'] = df['Middle_Band'] - (df['STD'] * num_std_dev)

    # Calculate Bandwidth (optional, but useful for volatility assessment)
    df['Bandwidth'] = ((df['Upper_Band'] - df['Lower_Band']) / df['Middle_Band']) * 100

    # Calculate Bollinger %B (optional, shows where the price is relative to the bands)
    df['Pct_B'] = (df['Close'] - df['Lower_Band']) / (df['Upper_Band'] - df['Lower_Band'])

    return df.dropna()

def plot_bollinger_bands(df, ticker):
    """Generates an interactive Plotly chart with Bollinger Bands."""
    if df.empty or 'Upper_Band' not in df.columns:
        st.warning("Insufficient data to plot bands.")
        return

    # Create figure with 2 subplots (1 for price/bands, 1 for volume)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.05,
                        row_heights=[0.7, 0.3])

    # 1. Price and Bollinger Bands (Row 1)
    # Candlestick Trace
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Price'
    ), row=1, col=1)

    # Upper Band Trace
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['Upper_Band'],
        line=dict(color='rgba(255, 165, 0, 0.8)', width=1.5), # Orange
        name='Upper Band'
    ), row=1, col=1)

    # Middle Band (SMA) Trace
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['Middle_Band'],
        line=dict(color='rgba(135, 206, 235, 1)', width=1.5, dash='dash'), # Light Blue
        name='SMA (20)'
    ), row=1, col=1)

    # Lower Band Trace
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['Lower_Band'],
        line=dict(color='rgba(255, 165, 0, 0.8)', width=1.5), # Orange
        name='Lower Band'
    ), row=1, col=1)

    # 2. Volume (Row 2)
    fig.add_trace(go.Bar(
        x=df.index,
        y=df['Volume'],
        marker_color='rgba(31, 119, 180, 0.6)',
        name='Volume'
    ), row=2, col=1)

    # Update layout
    fig.update_layout(
        title=f'{ticker} Price and Bollinger Bands',
        xaxis_rangeslider_visible=False,
        height=700,
        template='plotly_dark',
        # Remove empty space between price and volume subplots
        xaxis=dict(showgrid=True, gridcolor='#2e3037'),
        yaxis=dict(showgrid=True, gridcolor='#2e3037'),
        yaxis2=dict(showgrid=True, gridcolor='#2e3037')
    )
    
    # Hide axis label on top subplot (Row 1) for a cleaner look
    fig.update_xaxes(title_text="", row=1, col=1) 
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Price / Bands", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)


    st.plotly_chart(fig, use_container_width=True)

# --- Streamlit UI ---

def main():
    st.markdown('<div class="main-header">Real-Time Bollinger Band Scanner</div>', unsafe_allow_html=True)

    # Sidebar for inputs
    with st.sidebar:
        st.header("Stock Parameters")
        
        # Input for Ticker Symbol
        ticker_symbol = st.text_input(
            "Enter Stock Ticker (e.g., AAPL, TSLA)",
            value='GOOG',
            max_chars=10
        ).upper()

        # Input for Time Window
        window = st.number_input(
            "Bollinger Band Window (Days)",
            min_value=5,
            max_value=100,
            value=20,
            step=1
        )

        # Input for Standard Deviation
        num_std = st.number_input(
            "Standard Deviation Multiplier",
            min_value=1.0,
            max_value=3.0,
            value=2.0,
            step=0.1,
            format="%.1f"
        )

        # Date Range Selection (Last 6 Months Default)
        today = pd.to_datetime('today').normalize()
        start_default = today - pd.DateOffset(months=6)

        date_range = st.date_input(
            "Select Date Range",
            value=(start_default.date(), today.date()),
            min_value=pd.to_datetime('2000-01-01').date(),
            max_value=today.date()
        )
        
        # Ensure date_range has two elements
        if len(date_range) == 2:
            start_date, end_date = date_range[0].strftime('%Y-%m-%d'), date_range[1].strftime('%Y-%m-%d')
        else:
            # Fallback if only one date is selected during interaction
            st.warning("Please select a valid start and end date.")
            return

    # Main area execution
    if ticker_symbol:
        st.subheader(f"Analysis for: **{ticker_symbol}**")
        
        # 1. Fetch Data
        data = get_data(ticker_symbol, start_date, end_date)
        
        if not data.empty:
            # 2. Calculate Bands
            df_bb = calculate_bollinger_bands(data, window, num_std)
            
            if not df_bb.empty:
                # 3. Plot Chart
                st.markdown("### Interactive Candlestick Chart with Bollinger Bands")
                plot_bollinger_bands(df_bb, ticker_symbol)

                # 4. Display Summary Table
                st.markdown("### Current Band Status")
                
                latest_data = df_bb.iloc[-1]
                
                # Check for signals
                is_overbought = latest_data['Close'] > latest_data['Upper_Band']
                is_oversold = latest_data['Close'] < latest_data['Lower_Band']
                
                status_text = "Neutral"
                color = "white"
                
                if is_overbought:
                    status_text = "Overbought (Price above Upper Band)"
                    color = "red"
                elif is_oversold:
                    status_text = "Oversold (Price below Lower Band)"
                    color = "green"

                # Display key metrics in columns
                col1, col2, col3, col4 = st.columns(4)
                
                col1.metric("Latest Close Price", f"${latest_data['Close']:.2f}")
                col2.metric("Upper Band", f"${latest_data['Upper_Band']:.2f}")
                col3.metric("Lower Band", f"${latest_data['Lower_Band']:.2f}")
                col4.metric(
                    "Signal Status", 
                    status_text, 
                    delta=f"Bandwidth: {latest_data['Bandwidth']:.2f}%"
                )
                
                # Display the last few rows of data for inspection
                st.markdown("### Raw Data (Last 5 Days)")
                st.dataframe(df_bb.tail(), use_container_width=True)

            else:
                st.warning(f"Not enough data (need at least {window} days) in the selected range to calculate the Bollinger Bands.")
        
    elif not ticker_symbol:
        st.info("Please enter a stock ticker symbol to begin the analysis.")

if __name__ == '__main__':
    main()
