import pandas as pd
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
import os

# Qdrant Cloud Credentials
QDRANT_URL = "https://d0754f8d-a323-402c-8dba-4cc8079c15e5.eu-west-2-0.aws.cloud.qdrant.io"
QDRANT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6MThkZTVlZGYtYzA0MS00NDg5LTkxYmMtM2UwYTI0YjQ0YWMwIn0.9-lx_H6LELMk2NOLJzdXPWIBWPFZgRi3gqk8FwE0u8U"

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

def encode_window(window):
    # Flatten the 4 features (OHLC) over the window size
    flat = window.flatten()
    norm = np.linalg.norm(flat)
    return (flat / norm).tolist() if norm > 0 else flat.tolist()

def store_winning_patterns(h1_df, window_size=30):
    # Create collection if not exists
    try:
        collections = [c.name for c in client.get_collections().collections]
    except Exception:
        collections = []

    if "winning_patterns" not in collections:
        client.create_collection(
            collection_name="winning_patterns",
            vectors_config=VectorParams(size=4*window_size, distance=Distance.COSINE)
        )
        print("Created collection 'winning_patterns'")
    
    points = []
    count = 0
    for idx in range(window_size, len(h1_df)-10):
        # Extract OHLC window
        window = h1_df[['open','high','low','close']].iloc[idx-window_size:idx].values
        vec = encode_window(window)
        
        # Forward return (10 bars ahead)
        future_return = (h1_df['close'].iloc[idx+10] / h1_df['close'].iloc[idx] - 1) * 100
        
        if future_return > 0.15:   # profitable bullish
            points.append(PointStruct(
                id=idx,
                vector=vec,
                payload={
                    'timestamp': str(h1_df.index[idx]),
                    'return_pct': float(future_return),
                    'bias': 'bullish'
                }
            ))
            count += 1
        elif future_return < -0.15: # profitable bearish
             points.append(PointStruct(
                id=idx,
                vector=vec,
                payload={
                    'timestamp': str(h1_df.index[idx]),
                    'return_pct': float(future_return),
                    'bias': 'bearish'
                }
            ))
             count += 1

        if len(points) >= 100:
            client.upsert("winning_patterns", points)
            points = []
            
    if points:
        client.upsert("winning_patterns", points)
        
    print(f"Stored {count} patterns in Qdrant")

if __name__ == "__main__":
    if not os.path.exists("data/EURUSD_H1.csv"):
        print("Data file not found. Please run collect_data.py first.")
    else:
        h1 = pd.read_csv("data/EURUSD_H1.csv", index_col=0, parse_dates=True)
        store_winning_patterns(h1)
