import yfinance as yf
import pandas as pd
import numpy as np
import time
import sys

# --- Configuration ---
# List of NIFTY 50 tickers with the .NS suffix for Yahoo Finance (Indian Exchange)
TICKERS = [
    "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "HDFC.NS",
    "TCS.NS", "KOTAKBANK.NS", "HINDUNILVR.NS", "ITC.NS", "BHARTIARTL.NS",
    "SBIN.NS", "LT.NS", "BAJFINANCE.NS", "AXISBANK.NS", "ASIANPAINT.NS",
    "MARUTI.NS", "WIPRO.NS", "HCLTECH.NS", "ULTRACEMCO.NS", "SUNPHARMA.NS",
    "TITAN.NS", "NESTLEIND.NS", "TECHM.NS", "NTPC.NS", "M&M.NS",
    "ADANIPORTS.NS", "POWERGRID.NS", "GRASIM.NS", "INDUSINDBK.NS", "DRREDDY.NS",
    "JSWSTEEL.NS", "APOLLOHOSP.NS", "SBILIFE.NS", "EICHERMOT.NS", "BRITANNIA.NS",
    "BPCL.NS", "TATACONSUM.NS", "HDFCLIFE.NS", "COALINDIA.NS", "SHREECEM.NS",
    "HINDALCO.NS", "HEROMOTOCO.NS", "DIVISLAB.NS", "UPL.NS", "CIPLA.NS",
    "ONGC.NS", "TATAMOTORS.NS", "ADANIENT.NS", "BAJAJFINSV.NS", "DMART.NS" 
]
WINDOW = 20  # Lookback window for Bollinger Bands
NUM_STD = 2  # Number of standard deviations for bands

# --- Core Functions ---

def fetch_data(ticker):
    """Fetches historical data for a given ticker."""
    try:
        # Fetch up to 1 year of daily data
        data = yf.download(ticker, period="1y", interval="1d", progress=False)
        return data
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None

def calculate_bollinger_bands(data, window, num_std):
    """
    Calculates Bollinger Bands (Middle, Upper, Lower) and %B.
    This function expects a DataFrame with a 'Close' column.
    """
    if data is None or data.empty:
        return None

    # 1. Calculate Middle Band (20-day Simple Moving Average of the Close price)
    data['Middle_Band'] = data['Close'].rolling(window=window).mean()

    # 2. Calculate Standard Deviation (20-day)
    data['StdDev'] = data['Close'].rolling(window=window).std()

    # 3. Calculate Upper and Lower Bands
    data['Upper_Band'] = data['Middle_Band'] + (data['StdDev'] * num_std)
    data['Lower_Band'] = data['Middle_Band'] - (data['StdDev'] * num_std)

    # 4. Calculate %B (Percent Bandwidth)
    # This calculation is now correctly structured for element-wise operation (Series/Series).
    denominator = data['Upper_Band'] - data['Lower_Band']
    
    # Handle division by zero/NaNs that may occur at the start of the series (first 19 days)
    data['Pct_B'] = np.where(denominator != 0, (data['Close'] - data['Lower_Band']) / denominator, 0.5)
    
    return data

def scan_for_signals(data, ticker):
    """Checks the latest %B value for buy/sell signals."""
    if data is None or data.empty:
        return None

    # Get the last valid %B value (the current day's signal)
    # Use .iloc[-1] to get the most recent value
    latest_pct_b = data['Pct_B'].iloc[-1]
    
    # Check for Oversold (Buy/Long Signal) or Overbought (Sell/Short Signal)
    if latest_pct_b < 0.05:
        # Stock is below the lower band, highly oversold (Buy Signal)
        return f"{ticker}: Long/Buy Signal (%B = {latest_pct_b:.2f})"
    elif latest_pct_b > 0.95:
        # Stock is above the upper band, highly overbought (Short/Sell Signal)
        return f"{ticker}: Short/Sell Signal (%B = {latest_pct_b:.2f})"
    else:
        return None

def main():
    """Main function to run the scanner across all tickers."""
    signal_list = []
    
    print("--- Starting Daily Bollinger Band Scan (Nifty 50) ---")

    for ticker in TICKERS:
        # 1. Fetch Data
        data = fetch_data(ticker)
        if data is None:
            continue
            
        # 2. Calculate Bands and %B
        data_with_bands = calculate_bollinger_bands(data, WINDOW, NUM_STD)
        if data_with_bands is None:
            continue
            
        # 3. Scan for Signal
        signal = scan_for_signals(data_with_bands, ticker)
        
        if signal:
            signal_list.append(signal)

    # Output for GitHub Actions
    if signal_list:
        output = "Signals Found:\n" + "\n".join(signal_list)
        print(f"::set-output name=signal::{output}")
    else:
        # Critical for Telegram step: output must be set, even if empty
        print("No Signals Found")
        print(f"::set-output name=signal::No Signals Found")
        
    print("--- Scan Complete ---")

# Entry point of the script
if __name__ == "__main__":
    main()
