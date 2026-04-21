# collect_mt5_data.py 
import MetaTrader5 as mt5 
import pandas as pd 
from datetime import datetime, timedelta 
 
def fetch_ohlcv(symbol="EURUSD", timeframe=mt5.TIMEFRAME_H1, start_date=None, end_date=None): 
    """Fetch OHLCV data from MT5""" 
    if not mt5.initialize(): 
        raise Exception("MT5 initialization failed") 
     
    if start_date is None: 
        start_date = datetime.now() - timedelta(days=365*3)  # 3 years 
    if end_date is None: 
        end_date = datetime.now() 
     
    rates = mt5.copy_rates_range(symbol, timeframe, start_date, end_date) 
    mt5.shutdown() 
     
    if rates is None or len(rates) == 0:
        print(f"No data for {symbol} on {timeframe}")
        return pd.DataFrame()

    df = pd.DataFrame(rates) 
    df['time'] = pd.to_datetime(df['time'], unit='s') 
    df.set_index('time', inplace=True) 
    return df 
 
def fetch_multi_timeframe(symbol="EURUSD", lookback_days=365): 
    """Fetch both 1H and 5M data aligned""" 
    end = datetime.now() 
    start = end - timedelta(days=lookback_days) 
     
    # Fetch 1H data 
    h1_data = fetch_ohlcv(symbol, mt5.TIMEFRAME_H1, start, end) 
     
    # Fetch 5M data (more granular for alignment) 
    m5_data = fetch_ohlcv(symbol, mt5.TIMEFRAME_M5, start, end) 
     
    return h1_data, m5_data 
 
if __name__ == "__main__": 
    h1_df, m5_df = fetch_multi_timeframe("EURUSD", lookback_days=30) 
    if not h1_df.empty:
        h1_df.to_csv("EURUSD_H1_3years.csv") 
    if not m5_df.empty:
        m5_df.to_csv("EURUSD_M5_3years.csv") 
    print(f"✅ Saved: {len(h1_df)} H1 bars, {len(m5_df)} M5 bars") 
