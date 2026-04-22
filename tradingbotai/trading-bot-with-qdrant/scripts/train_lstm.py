import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
import os

class LSTMPredictor(nn.Module):
    def __init__(self, input_size=5, hidden_size=32, num_layers=2, dropout=0.3):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)
        self.fc = nn.Linear(hidden_size, 2)
    
    def forward(self, x):
        out, _ = self.lstm(x)
        out = out[:, -1, :]
        return self.fc(out)

def train_model(X, y, epochs=50, batch_size=32, lr=0.001):
    # Reshape X to (samples, seq_len, features)
    seq_len = 5
    X_seq, y_seq = [], []
    for i in range(len(X) - seq_len):
        X_seq.append(X[i:i+seq_len])
        y_seq.append(y[i+seq_len])
    X_seq = np.array(X_seq)
    y_seq = np.array(y_seq)
    
    # Handle NaNs if any (from indicators)
    X_seq = np.nan_to_num(X_seq)
    
    X_tensor = torch.FloatTensor(X_seq)
    y_tensor = torch.LongTensor(y_seq)
    dataset = TensorDataset(X_tensor, y_tensor)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    model = LSTMPredictor(input_size=X.shape[1], hidden_size=32)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        for bx, by in loader:
            optimizer.zero_grad()
            out = model(bx)
            loss = criterion(out, by)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        if (epoch+1) % 10 == 0:
            print(f"Epoch {epoch+1}/{epochs}, Loss: {total_loss/len(loader):.4f}")
    return model

if __name__ == "__main__":
    # Ensure directories exist
    os.makedirs("models", exist_ok=True)
    
    X = np.load("data/X.npy")
    y = np.load("data/y.npy")
    print(f"Loaded {len(X)} samples")
    model = train_model(X, y)
    
    # Export to ONNX
    dummy_input = torch.randn(1, 5, X.shape[1])  # (batch, seq_len, features)
    torch.onnx.export(model, dummy_input, "models/strategy_model.onnx",
                      input_names=['input'], output_names=['output'],
                      opset_version=12)
    print("✅ ONNX model saved to models/strategy_model.onnx")
