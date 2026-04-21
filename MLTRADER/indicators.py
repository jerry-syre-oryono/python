# indicators.py 
import pandas as pd 
import numpy as np 
 
def calculate_ma(df, period=200): 
    return df['close'].rolling(window=period).mean() 
 
def calculate_williams_r(df, period=14): 
    high = df['high'].rolling(window=period).max() 
    low = df['low'].rolling(window=period).min() 
    return -100 * (high - df['close']) / (high - low) 
 
def detect_choch(df, idx, lookback=5): 
    """Detect Change of Character (CHOCH) → Break of Structure (BOS) at a specific index""" 
    if idx < lookback: return 0
    highs = df['high'].rolling(lookback).max() 
    lows = df['low'].rolling(lookback).min() 
    choch = (df['high'].iloc[idx] > highs.shift(1).iloc[idx]) | (df['low'].iloc[idx] < lows.shift(1).iloc[idx]) 
    return int(choch) 
 
def is_near_order_block(df, idx, lookback=20): 
    """Simplified OB detection: recent swing high/low zone""" 
    recent_high = df['high'].iloc[idx-lookback:idx].max() 
    recent_low = df['low'].iloc[idx-lookback:idx].min() 
    return df['close'].iloc[idx] < recent_high * 1.002 
 
def is_london_ny_session(timestamp): 
    hour = timestamp.hour 
    london = (hour >= 8 and hour < 12)  # Simplified 
    ny = (hour >= 13 and hour < 17) 
    return london or ny 
 
def detect_engulfing(df, idx): 
    prev = df.iloc[idx-1] 
    curr = df.iloc[idx] 
    bullish = (curr['close'] > prev['high']) and (curr['open'] < prev['close']) 
    bearish = (curr['close'] < prev['low']) and (curr['open'] > prev['close']) 
    return 1 if bullish else (-1 if bearish else 0) 
 
def is_retrace_to_ma(df, idx, period=20): 
    ma = df['close'].rolling(period).mean().iloc[idx] 
    price = df['close'].iloc[idx] 
    return abs(price - ma) / ma < 0.005  # Within 0.5% of MA
