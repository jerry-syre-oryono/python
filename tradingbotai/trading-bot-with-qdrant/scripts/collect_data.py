import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import os

def fetch_ohlcv(symbol="EURUSD", timeframe=mt5.TIMEFRAME_H1, 
                start_date=None, end_date=None, output_csv="data/EURUSD_H1.csv"):
    if not mt5.initialize():
        raise Exception("MT5 init failed")
    
    if start_date is None:
        start_date = datetime.now() - timedelta(days=365*2)  # 2 years
    if end_date is None:
        end_date = datetime.now()
    
    rates = mt5.copy_rates_range(symbol, timeframe, start_date, end_date)
    mt5.shutdown()
    
    if rates is None or len(rates) == 0:
        print(f"No rates found for {symbol}")
        return None

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    
    df.to_csv(output_csv)
    print(f"Saved {len(df)} bars to {output_csv}")
    return df

if __name__ == "__main__":
    # Fetch 1H data (2 years)
    fetch_ohlcv("EURUSD", mt5.TIMEFRAME_H1, output_csv="data/EURUSD_H1.csv")
    
    # Fetch 5M data (30 days for slot analysis)
    m5_start = datetime.now() - timedelta(days=30)
    fetch_ohlcv("EURUSD", mt5.TIMEFRAME_M5, start_date=m5_start, output_csv="data/EURUSD_M5.csv")
