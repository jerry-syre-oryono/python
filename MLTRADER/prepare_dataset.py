# prepare_dataset.py 
import pandas as pd 
import numpy as np 
from indicators import * 
 
def extract_features(df_h1, df_m5, idx): 
    """Extract feature vector for a given H1 index""" 
    # H1 features 
    h1_close = df_h1['close'].iloc[idx] 
    h1_ma = df_h1['ma_200'].iloc[idx] 
    h1_wr = df_h1['williams_r'].iloc[idx] 
    h1_choch = detect_choch(df_h1, idx) 
    h1_ob = is_near_order_block(df_h1, idx) 
    h1_session = int(is_london_ny_session(df_h1.index[idx])) 
     
    # Align with M5 
    nearest_m5 = df_m5[df_m5.index <= df_h1.index[idx]].iloc[-1] 
    m5_idx = df_m5.index.get_loc(nearest_m5.name) 
     
    # M5 features 
    m5_close = df_m5['close'].iloc[m5_idx] 
    m5_ma = df_m5['ma_200'].iloc[m5_idx] 
    m5_wr = df_m5['williams_r'].iloc[m5_idx] 
    m5_choch = detect_choch(df_m5, m5_idx) 
    m5_retrace = int(is_retrace_to_ma(df_m5, m5_idx)) 
    m5_engulf = detect_engulfing(df_m5, m5_idx) 
     
    return [ 
        h1_close / h1_ma if h1_ma != 0 else 1.0, h1_wr, h1_choch, h1_ob, h1_session, 
        m5_close / m5_ma if m5_ma != 0 else 1.0, m5_wr, m5_choch, m5_retrace, m5_engulf 
    ] 
 
def label_strategy_signal(df_h1, df_m5, idx): 
    """Apply your checklist logic to label each bar""" 
    # ========== 1H Bias (5 conditions) ========== 
    conditions_1h = { 
        'ma': df_h1['close'].iloc[idx] > df_h1['ma_200'].iloc[idx], 
        'structure': detect_choch(df_h1, idx), 
        'ob': is_near_order_block(df_h1, idx), 
        'wr': abs(df_h1['williams_r'].iloc[idx]) < 50,  # Neutral 
        'session': is_london_ny_session(df_h1.index[idx]) 
    } 
    completion_1h = sum(conditions_1h.values()) / 5.0 
     
    # Determine bias 
    if completion_1h >= 0.6: 
        bias = 'buy' if conditions_1h['ma'] else 'sell' 
    else: 
        bias = 'none' 
     
    if bias == 'none': 
        return 0, bias, 0  # No trade 
     
    # ========== 5M Slots (up to 3, 6 conditions each) ========== 
    nearest_m5 = df_m5[df_m5.index <= df_h1.index[idx]].iloc[-1] 
    m5_idx = df_m5.index.get_loc(nearest_m5.name) 
     
    best_slot_completion = 0 
    for slot in range(3): 
        conditions_slot = { 
            'side_match': bias == ('buy' if df_m5['close'].iloc[m5_idx] > df_m5['ma_200'].iloc[m5_idx] else 'sell'), 
            'ma': df_m5['close'].iloc[m5_idx] > df_m5['ma_200'].iloc[m5_idx], 
            'micro_structure': detect_choch(df_m5, m5_idx), 
            'retrace': is_retrace_to_ma(df_m5, m5_idx), 
            'wr': df_m5['williams_r'].iloc[m5_idx] < -80 or df_m5['williams_r'].iloc[m5_idx] > 80, 
            'engulf': detect_engulfing(df_m5, m5_idx) != 0 
        } 
        completion = sum(conditions_slot.values()) / 6.0 
        best_slot_completion = max(best_slot_completion, completion) 
     
    # ========== Overall Confidence ========== 
    overall_confidence = (completion_1h * 0.5) + (best_slot_completion * 0.5) 
     
    if overall_confidence < 0.75: 
        return 0, bias, overall_confidence 
     
    # ========== Determine Profitability (Label) ========== 
    entry_price = df_h1['close'].iloc[idx] 
    look_ahead = min(8, len(df_h1) - idx - 1)
    if look_ahead <= 0: return 0, bias, overall_confidence
    
    future_bars = df_h1.iloc[idx+1:idx+1+look_ahead] 
     
    if bias == 'buy': 
        max_price = future_bars['high'].max() 
        profit_pips = (max_price - entry_price) * 10000 
    else: 
        min_price = future_bars['low'].min() 
        profit_pips = (entry_price - min_price) * 10000 
     
    return (1 if profit_pips > 15 else 0), bias, overall_confidence 
 
def build_training_dataset(df_h1, df_m5, seq_len=20, min_bars=200): 
    X, y, biases = [], [], [] 
    
    # Precompute all features for speed
    print("Precomputing features...")
    all_features = []
    for i in range(len(df_h1)):
        try:
            all_features.append(extract_features(df_h1, df_m5, i))
        except:
            all_features.append([0.0] * 10)
    
    all_features = np.array(all_features)
    
    print("Generating sequences...")
    for idx in range(max(min_bars, seq_len), len(df_h1)): 
        try: 
            label, bias, confidence = label_strategy_signal(df_h1, df_m5, idx) 
            if bias != 'none': 
                # Extract sequence of features
                seq = all_features[idx-seq_len+1 : idx+1]
                X.append(seq) 
                y.append(label) 
                biases.append(bias) 
        except Exception as e: 
            continue 
    return np.array(X), np.array(y), biases 
 
if __name__ == "__main__": 
    try:
        h1_df = pd.read_csv("EURUSD_H1_3years.csv", index_col=0, parse_dates=True) 
        m5_df = pd.read_csv("EURUSD_M5_3years.csv", index_col=0, parse_dates=True) 
        
        # Add indicators 
        h1_df['ma_200'] = calculate_ma(h1_df, 200) 
        h1_df['williams_r'] = calculate_williams_r(h1_df) 
        m5_df['ma_200'] = calculate_ma(m5_df, 200) 
        m5_df['williams_r'] = calculate_williams_r(m5_df) 
        
        X, y, biases = build_training_dataset(h1_df, m5_df, seq_len=20) 
        print(f"✅ Dataset: {X.shape[0]} samples, {X.shape[1]} seq_len, {X.shape[2]} features") 
        if len(y) > 0:
            print(f"✅ Label distribution: {np.bincount(y)}")
            np.save("X_train.npy", X)
            np.save("y_train.npy", y)
            print("✅ Saved X_train.npy and y_train.npy")
        else:
            print("⚠️ No samples generated.")
    except FileNotFoundError:
        print("❌ CSV files not found.")
