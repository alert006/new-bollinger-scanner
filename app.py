import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import time

# --- Configuration ---
# List of tickers to scan
TICKERS = ['MSFT', 'GOOGL', 'AAPL', 'AMZN', 'TSLA', 'SPY']
PERIOD = '1y' # Fetch 1 year of data
INTERVAL = '1d' # Daily data
WINDOW = 20 # Standard Bollinger Band window
NUM_STD = 2 # Standard deviations for bands

def calculate_bollinger_bands(df, window=WINDOW, num_std=NUM_STD):
    """
    Calculates the Middle, Upper, and Lower Bollinger Bands, and the %B indicator.
    
    Args:
        df (pd.DataFrame): DataFrame containing 'Close' price data.
        window (int): Rolling window period.
        num_std (int): Number of standard deviations.
        
    Returns:
        pd.DataFrame: Original DataFrame with 'Middle_Band', 'Upper_Band', 
                      'Lower_Band', and 'Pct_B' columns added.
    """
    
    # Ensure 'Close' column exists
    if 'Close' not in df.columns:
        return df

    # 1. Calculate the Rolling Mean (Middle Band)
    df['Middle_Band'] = df['Close'].rolling(window=window).mean()

    # 2. Calculate the Rolling Standard Deviation
    df['Std_Dev'] = df['Close'].rolling(window=window).std()

    # 3. Calculate Upper and Lower Bands
    # CRITICAL FIX: Ensure correct assignment using calculated series
    df['Upper_Band'] = df['Middle_Band'] + (df['Std_Dev'] * num_std)
    df['Lower_Band'] = df['Middle_Band'] - (df['Std_Dev'] * num_std)

    # 4. Calculate %B (Percent Bandwidth)
    # The formula is: (Close - Lower Band) / (Upper Band - Lower Band)
    # The division may produce division by zero if Upper == Lower, so we use np.where for safety
    band_range = df['Upper_Band'] - df['Lower_Band']
    
    # Fix the assignment error by ensuring the calculation produces a single Series
    df['Pct_B'] = np.where(
        band_range == 0,
        0.5, # Assign a neutral value if the band range is zero
        (df['Close'] - df['Lower_Band']) / band_range
    )
    
    df.drop(columns=['Std_Dev'], inplace=True)
    return df

def get_bollinger_signals(df_bands):
    """
    Scans the latest data point for a Bollinger Band signal.
    
    Signal criteria:
    - Long (Buy): Close price crosses below the Lower Band. (Pct_B < 0)
    - Short (Sell): Close price crosses above the Upper Band. (Pct_B > 1)
    
    Args:
        df_bands (pd.DataFrame): DataFrame containing the calculated bands.
        
    Returns:
        str: A string describing the signal (e.g., 'AAPL: Long Signal (Pct_B: -0.05)').
             Returns an empty string if no signal is found.
    """
    signals = []
    
    # Drop rows with NaN (due to rolling window calculation)
    df = df_bands.dropna()

    if df.empty:
        return ""
        
    # Get the latest data point
    latest = df.iloc[-1]
    ticker = df.index.name
    
    pct_b = latest['Pct_B']
    close = latest['Close']
    lower = latest['Lower_Band']
    upper = latest['Upper_Band']

    signal_found = False
    signal_type = "None"
    
    # --- Long Signal (Reversion to the Mean, Oversold) ---
    if pct_b < 0:
        signal_type = "Long/Buy"
        signal_found = True
        
    # --- Short Signal (Reversion to the Mean, Overbought) ---
    elif pct_b > 1:
        signal_type = "Short/Sell"
        signal_found = True

    if signal_found:
        signal_details = (
            f"**{ticker}: {signal_type} Signal**\n"
            f"  > Pct_B: {pct_b:.2f}\n"
            f"  > Close: {close:.2f} (Lower: {lower:.2f}, Upper: {upper:.2f})"
        )
        signals.append(signal_details)
        
    return "\n---\n".join(signals)


def run_scanner():
    """
    Main function to run the scanner across all configured tickers.
    """
    all_signals = []
    
    print(f"Starting Bollinger Band scan for {len(TICKERS)} tickers...")
    
    for ticker in TICKERS:
        try:
            # 1. Fetch data
            data = yf.download(ticker, period=PERIOD, interval=INTERVAL, progress=False)
            
            if data.empty:
                print(f"Skipping {ticker}: No data fetched.")
                continue
            
            data.index.name = ticker # Set ticker as index name for easy retrieval later
            
            # 2. Calculate Bands and Pct_B
            df_bands = calculate_bollinger_bands(data)
            
            # 3. Check for Signals
            signal = get_bollinger_signals(df_bands)
            
            if signal:
                all_signals.append(signal)
            
        except Exception as e:
            # Handle potential API errors or connectivity issues
            error_msg = f"Error processing {ticker}: {e}"
            print(error_msg)
            # You might want to log this error somewhere, but for now, just print it

        # Be polite to the API
        time.sleep(0.5) 
            
    
    if all_signals:
        # Join all found signals into a single string for Telegram
        final_output = "\n\n".join(all_signals)
        print("\n--- Final Signals Found ---")
        print(final_output)
        return final_output
    else:
        print("--- No Signals Found ---")
        # Return an empty string if no signals are found (this prevents the Telegram notification)
        return ""

if __name__ == "__main__":
    # The output of this script is captured by the GitHub Action workflow
    # and saved into the 'signal' variable.
    print(run_scanner())
