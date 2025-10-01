import yfinance as yf
import pandas as pd
import numpy as np
import time
import sys
from yfinance.shared import TickerNoDataError # Import the specific error

# --- Configuration ---
# List of NIFTY 50 tickers with the .NS suffix for Yahoo Finance (Indian Exchange)
# NOTE: HDFC.NS has been removed as it is delisted/merged with HDFCBANK.NS and no longer returns data.
TICKERS = [
    "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
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
        # Fetch up to 1 year of daily data.
        data = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=True, timeout=10)
        
        # Check if data frame contains a 'Close' column and has enough rows
        if data.empty or 'Close' not in data.columns or len(data) < WINDOW:
            print(f"Warning: Not enough data or missing 'Close' column for {ticker}. Skipping.")
            return None
        
        return data
    except TickerNoDataError:
        # Catch the specific yfinance error when a ticker returns no data (like delisted ones)
        print(f"Error: Ticker {ticker} returned no data. It may be delisted or invalid.")
        return None
    except Exception as e:
        # Catch other network or request errors
        print(f"Error fetching data for {ticker}: {e}")
        return None

def calculate_pct_b(close_prices, window, num_std):
    """
    Calculates the latest %B value from a single Pandas Series of closing prices.
    This function is completely isolated to prevent DataFrame broadcasting errors.
    """
    if close_prices is None or len(close_prices) < window:
        return np.nan

    # 1. Calculate Middle Band (SMA)
    middle_band = close_prices.rolling(window=window).mean()

    # 2. Calculate Standard Deviation
    std_dev = close_prices.rolling(window=window).std()

    # 3. Calculate Upper and Lower Bands
    upper_band = middle_band + (std_dev * num_std)
    lower_band = middle_band - (std_dev * num_std)

    # 4. Calculate %B (Percent Bandwidth) for the whole series
    denominator = upper_band - lower_band
    numerator = close_prices - lower_band
    
    # Calculate %B, handling division by zero/NaNs (occurs at start of series)
    pct_b_series = np.where(denominator != 0, numerator / denominator, 0.5)
    
    # Return ONLY the latest calculated value as a float
    return pct_b_series[-1]

def scan_for_signals(pct_b, ticker):
    """Checks the latest %B value for buy/sell signals."""
    # Check for NaN (Not a Number) which happens if data was insufficient or calculation failed
    if np.isnan(pct_b):
        return None
        
    # Check for Oversold (Buy/Long Signal: < 5%)
    if pct_b < 0.05:
        return f"{ticker}: Long/Buy Signal (%B = {pct_b:.2f}) - Oversold (Below Lower Band)"
    # Check for Overbought (Sell/Short Signal: > 95%)
    elif pct_b > 0.95:
        return f"{ticker}: Short/Sell Signal (%B = {pct_b:.2f}) - Overbought (Above Upper Band)"
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
            
        # 2. Extract Close Prices and Calculate %B
        try:
            # Pass only the Close price Series to the calculation function
            close_prices = data['Close']
            latest_pct_b = calculate_pct_b(close_prices, WINDOW, NUM_STD)
                
            # 3. Scan for Signal
            signal = scan_for_signals(latest_pct_b, ticker)
            
            if signal:
                signal_list.append(signal)
        except Exception as e:
            # Catch any unexpected errors during the calculation phase
            print(f"Error processing final calculation for {ticker}: {e}. Skipping.")
            continue

    # --- GitHub Actions Output ---
    if signal_list:
        output = "🚨 Daily Trading Signals Found! 🚨\n\n" + "\n".join(signal_list)
        print(output) # Print the signals for visibility
        # Set the output variable for the next step (Telegram)
        print(f"::set-output name=signal::{output}")
    else:
        # Ensure the output is set even when no signals are found
        no_signal_msg = "No Bollinger Band Signals Found (All tickers in range 5% - 95%)."
        print(no_signal_msg)
        print(f"::set-output name=signal::{no_signal_msg}")
        
    print("--- Scan Complete ---")

# Entry point of the script
if __name__ == "__main__":
    main()
