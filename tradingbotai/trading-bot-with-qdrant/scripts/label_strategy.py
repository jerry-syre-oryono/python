import pandas as pd
import numpy as np
from indicators import *

def label_strategy_signal(h1_row, m5_slice, idx, h1_df, m5_df):
    """
    Apply your 1H bias + 5M slots to label a single bar.
    Returns (label, bias, confidence)
    """
    # ---- 1H Bias (5 conditions) ----
    cond_1h = {
        'ma': h1_row['close'] > h1_row['ma_200'],
        'structure': detect_choch(h1_df, idx) == 1,
        'ob': is_near_order_block(h1_df, idx),
        'wr': abs(h1_row['williams_r']) < 50,
        'session': is_london_ny_session(h1_row.name)
    }
    completion_1h = sum(cond_1h.values()) / 5.0
    
    if completion_1h >= 0.6:
        bias = 'buy' if cond_1h['ma'] else 'sell'
    else:
        bias = 'none'
    
    if bias == 'none':
        return 0, bias, 0.0
    
    # ---- 5M Slots (up to 3, each 6 conditions) ----
    # Find nearest 5M bar within this 1H bar's time range
    m5_bars = m5_df[m5_df.index <= h1_row.name]
    if len(m5_bars) == 0:
        return 0, bias, 0.0
    last_m5 = m5_bars.iloc[-1]
    m5_idx = m5_df.index.get_loc(last_m5.name)
    
    best_slot = 0.0
    for slot in range(3):  # 3 parallel slots
        # For simplicity, we use the same 5M bar for all slots (you can shift by -1,-2)
        cond_slot = {
            'side_match': (bias == 'buy' and last_m5['close'] > last_m5['ma_200']) or
                          (bias == 'sell' and last_m5['close'] < last_m5['ma_200']),
            'ma': last_m5['close'] > last_m5['ma_200'],
            'micro_structure': detect_choch(m5_df, m5_idx) == 1,
            'retrace': is_retrace_to_ma(m5_df, m5_idx),
            'wr': abs(last_m5['williams_r']) > 80,
            'engulf': detect_engulfing(m5_df, m5_idx) != 0
        }
        completion = sum(cond_slot.values()) / 6.0
        if completion > best_slot:
            best_slot = completion
    
    overall_conf = (completion_1h * 0.5) + (best_slot * 0.5)
    if overall_conf < 0.75:
        return 0, bias, overall_conf
    
    # ---- Determine profitability (label) ----
    entry = h1_row['close']
    future_bars = h1_df.iloc[idx+1:idx+8]  # next ~7 hours
    if len(future_bars) == 0:
        return 0, bias, overall_conf
        
    if bias == 'buy':
        max_price = future_bars['high'].max()
        profit = (max_price - entry) * 10000
    else:
        min_price = future_bars['low'].min()
        profit = (entry - min_price) * 10000
    label = 1 if profit > 15 else 0
    return label, bias, overall_conf

def build_training_dataset(h1_df, m5_df, min_bars=200):
    X = []   # features
    y = []   # labels
    for idx in range(min_bars, len(h1_df)-8):
        row = h1_df.iloc[idx]
        label, bias, conf = label_strategy_signal(row, m5_df, idx, h1_df, m5_df)
        if bias != 'none':
            # Build feature vector (you can expand)
            features = [
                row['ma_200'], row['williams_r'], conf,
                h1_df['close'].iloc[idx-1] / row['close'] - 1,  # 1-bar return
                h1_df['high'].iloc[idx] - h1_df['low'].iloc[idx]  # range
            ]
            X.append(features)
            y.append(label)
    return np.array(X), np.array(y)

if __name__ == "__main__":
    h1 = pd.read_csv("data/EURUSD_H1.csv", index_col=0, parse_dates=True)
    m5 = pd.read_csv("data/EURUSD_M5.csv", index_col=0, parse_dates=True)
    
    # Add indicators
    h1['ma_200'] = calculate_ma(h1, 200)
    h1['williams_r'] = calculate_williams_r(h1)
    m5['ma_200'] = calculate_ma(m5, 200)
    m5['williams_r'] = calculate_williams_r(m5)
    
    X, y = build_training_dataset(h1, m5)
    print(f"Dataset shape: {X.shape}, positive labels: {sum(y)}")
    np.save("data/X.npy", X)
    np.save("data/y.npy", y)
