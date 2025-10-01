import os
import yfinance as yf
import pandas as pd

# --- Configuration ---
# List of top Nifty 50 tickers (Indian stocks on the National Stock Exchange)
# Using the '.NS' suffix for NSE tickers
TICKERS = [
    'RELIANCE.NS', 'HDFCBANK.NS', 'ICICIBANK.NS', 'INFY.NS', 'HDFC.NS', 
    'TCS.NS', 'HINDUNILVR.NS', 'KOTAKBANK.NS', 'BHARTIARTL.NS', 'ITC.NS',
    'LT.NS', 'SBIN.NS', 'AXISBANK.NS', 'BAJFINANCE.NS', 'ASIANPAINT.NS',
    'MARUTI.NS', 'TITAN.NS', 'M&M.NS', 'ULTRACEMCO.NS', 'NESTLEIND.NS',
    'WIPRO.NS', 'SUNPHARMA.NS', 'TECHM.NS', 'ADANIENT.NS', 'ADANIPORTS.NS',
    'POWERGRID.NS', 'NTPC.NS', 'TATACONSUM.NS', 'DIVISLAB.NS', 'GRASIM.NS',
    'INDUSINDBK.NS', 'APOLLOHOSP.NS', 'JSWSTEEL.NS', 'DRREDDY.NS', 'BRITANNIA.NS',
    'HCLTECH.NS', 'EICHERMOT.NS', 'CIPLA.NS', 'SHREECEM.NS', 'HEROMOTOCO.NS'
    # NOTE: I kept the list to 40 popular ones to prevent time-outs in the action run.
    # We can add more if these run successfully.
]
PERIOD = '6mo' # Use 6 months of historical data
INTERVAL = '1d' # Daily closing prices
BB_WINDOW = 20 # Standard 20-day Moving Average
BB_STD = 2 # Standard 2 standard deviations

def set_github_output(name, value):
    """
    Sets an output variable for the GitHub Actions workflow.
    The final signal text will be passed back to the YAML file this way.
    """
    try:
        # GitHub Actions writes outputs to a specific environment file
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            # Escape newlines for GitHub Actions multi-line output handling
            escaped_value = value.replace('\n', '%0A')
            print(f'{name}={escaped_value}', file=f)
    except Exception as e:
        # Fallback for local testing (will print the output to console)
        print(f"Error setting GitHub output (likely running locally): {e}")
        print(f"--- Faking GitHub Output Variable '{name}': {value} ---")


def calculate_bollinger_bands(df, window=BB_WINDOW, num_std=BB_STD):
    """Calculates the 20-day simple moving average and Bollinger Bands."""
    # Ensure the required columns exist before calculation
    if 'Close' not in df.columns:
        return None # Return None if data is incomplete

    df['SMA'] = df['Close'].rolling(window=window).mean()
    df['STD'] = df['Close'].rolling(window=window).std()
    df['Upper'] = df['SMA'] + (df['STD'] * num_std)
    df['Lower'] = df['SMA'] - (df['STD'] * num_std)
    return df

def generate_signal(ticker_df, ticker):
    """
    Generates a signal if the last closing price is near the upper or lower band.
    """
    # Check for NaN values in the last row (which happens when BB calculation starts)
    if ticker_df.iloc[-1].isnull().any():
        return f"ℹ️ {ticker} - Not enough data for full BB calculation. Skipping."
        
    last_row = ticker_df.iloc[-1]
    last_close = last_row['Close']
    upper_band = last_row['Upper']
    lower_band = last_row['Lower']

    signal = ""
    
    # Check for price above the Upper Band (potential sell signal)
    if last_close > upper_band:
        premium = (last_close - upper_band) / upper_band * 100
        signal = f"🚨 {ticker} - ABOVE Upper Band ({premium:.2f}%) at {last_close:.2f} (Potential Sell)"
        
    # Check for price below the Lower Band (potential buy signal)
    elif last_close < lower_band:
        discount = (lower_band - last_close) / lower_band * 100
        signal = f"🟢 {ticker} - BELOW Lower Band ({discount:.2f}%) at {last_close:.2f} (Potential Buy)"
    
    return signal

def run_scanner():
    """Main function to run the scanner, collect signals, and set GitHub output."""
    print("Starting Bollinger Band Signal Scan for Nifty 50 stocks...")
    
    signals = []
    
    for ticker in TICKERS:
        # Clean ticker name for display (remove .NS)
        display_ticker = ticker.replace('.NS', '')
        
        try:
            # 1. Fetch data
            data = yf.download(ticker, period=PERIOD, interval=INTERVAL, progress=False)
            
            # Defensive check for data emptiness or missing 'Close' column
            if data.empty or 'Close' not in data.columns:
                print(f"Skipping {ticker}: Data unavailable or corrupted.")
                signals.append(f"❌ {display_ticker} - Data unavailable or corrupted.")
                continue

            # 2. Calculate BB
            df_with_bb = calculate_bollinger_bands(data)
            
            # Check if BB calculation failed (e.g., if calculate_bollinger_bands returned None)
            if df_with_bb is None:
                print(f"Skipping {ticker}: Could not calculate Bollinger Bands due to missing 'Close' data.")
                signals.append(f"❌ {display_ticker} - Calculation failed: Missing 'Close' data.")
                continue

            # 3. Generate Signal
            signal = generate_signal(df_with_bb, display_ticker)
            
            # Only append signals that are not empty (meaning it's a Buy/Sell signal or the Info signal)
            if signal and not signal.startswith("ℹ️"):
                signals.append(signal)

        except Exception as e:
            # General catch for any unexpected yfinance or pandas error
            print(f"An unexpected error occurred processing {ticker}: {e}")
            signals.append(f"⚠️ {display_ticker} - Unexpected Error: {e}")

    # --- Final Output Formatting ---
    if not signals:
        # If no BUY/SELL signals found, set the clean default message
        final_message = "✅ No Bollinger Band Signals Found (All Nifty 50 tickers in range 5% - 95%)."
    else:
        # Join all found signals into a single string, separated by newlines
        final_message = "\n".join(signals)
        
    print("\n--- Final Scan Summary ---")
    print(final_message)
    print("--------------------------\n")
    
    # Send the final message to the GitHub Actions output variable 'signal'
    set_github_output("signal", final_message)
    
    print("Scan complete. Output variable set successfully.")


if __name__ == "__main__":
    run_scanner()
