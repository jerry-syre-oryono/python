import pandas as pd
import numpy as np

def calculate_ma(df, period=200):
    return df['close'].rolling(window=period).mean()

def calculate_williams_r(df, period=14):
    high = df['high'].rolling(window=period).max()
    low = df['low'].rolling(window=period).min()
    return -100 * (high - df['close']) / (high - low)

def detect_choch(df, idx, lookback=5):
    """Simplified CHOCH → BOS detection"""
    if idx < lookback: return 0
    highs = df['high'].iloc[idx-lookback:idx].max()
    lows = df['low'].iloc[idx-lookback:idx].min()
    curr_high = df['high'].iloc[idx]
    curr_low = df['low'].iloc[idx]
    return 1 if (curr_high > highs or curr_low < lows) else 0

def is_near_order_block(df, idx, lookback=20):
    if idx < lookback: return False
    recent_high = df['high'].iloc[max(0,idx-lookback):idx].max()
    recent_low = df['low'].iloc[max(0,idx-lookback):idx].min()
    return df['close'].iloc[idx] < recent_high * 1.002  # within 0.2% of high

def is_london_ny_session(timestamp):
    hour = timestamp.hour
    return (8 <= hour < 12) or (13 <= hour < 17)  # simplified

def detect_engulfing(df, idx):
    if idx == 0: return 0
    prev = df.iloc[idx-1]
    curr = df.iloc[idx]
    if curr['close'] > prev['high'] and curr['open'] < prev['close']:
        return 1   # bullish engulfing
    elif curr['close'] < prev['low'] and curr['open'] > prev['close']:
        return -1  # bearish engulfing
    return 0

def is_retrace_to_ma(df, idx, period=20):
    if idx < period: return False
    ma = df['close'].rolling(period).mean().iloc[idx]
    price = df['close'].iloc[idx]
    return abs(price - ma) / ma < 0.005
