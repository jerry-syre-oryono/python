# train.py 
import torch 
import torch.nn as nn 
from torch.utils.data import DataLoader, TensorDataset 
from model import LSTMPredictor
import numpy as np

def train_model(X, y, epochs=50, batch_size=32, lr=0.001): 
    """Train LSTM model""" 
    # Check for NaN or Inf
    if np.any(np.isnan(X)) or np.any(np.isinf(X)):
        print("⚠️ Warning: NaN or Inf found in features. Cleaning...")
        X = np.nan_to_num(X)
    
    # Convert to tensors 
    # X shape should be (num_samples, seq_len, input_size)
    X_tensor = torch.FloatTensor(X) 
    y_tensor = torch.LongTensor(y) 
    
    dataset = TensorDataset(X_tensor, y_tensor) 
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True) 
    
    input_size = X.shape[2]
    model = LSTMPredictor(input_size=input_size, hidden_size=64) 
    criterion = nn.CrossEntropyLoss() 
    optimizer = torch.optim.Adam(model.parameters(), lr=lr) 
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5) 
    
    for epoch in range(epochs): 
        model.train() 
        total_loss = 0 
        for batch_X, batch_y in loader: 
            optimizer.zero_grad() 
            outputs = model(batch_X) 
            loss = criterion(outputs, batch_y) 
            loss.backward() 
            optimizer.step() 
            total_loss += loss.item() 
        
        avg_loss = total_loss/len(loader)
        scheduler.step(avg_loss)
        
        if (epoch + 1) % 10 == 0: 
            print(f"Epoch {epoch+1}/{epochs}, Loss: {avg_loss:.4f}") 
    
    return model 

if __name__ == "__main__":
    # Test with dummy data if run directly
    print("Running training with dummy data...")
    X_dummy = np.random.randn(100, 20, 10) # 100 samples, 20 seq_len, 10 features
    y_dummy = np.random.randint(0, 2, 100)
    model = train_model(X_dummy, y_dummy, epochs=20)
    print("✅ Training complete.")
