import torch 
import torch.nn as nn 
 
class LSTMPredictor(nn.Module): 
    """LSTM model for market pattern classification""" 
    def __init__(self, input_size=10, hidden_size=64, num_layers=2, dropout=0.3): 
        super().__init__() 
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, 
                            batch_first=True, dropout=dropout) 
        self.batch_norm = nn.BatchNorm1d(hidden_size) 
        self.fc1 = nn.Linear(hidden_size, 32) 
        self.fc2 = nn.Linear(32, 2)  # Binary output (win/no win) 
        self.dropout = nn.Dropout(dropout) 
        self.relu = nn.ReLU() 
    
    def forward(self, x): 
        # x shape: (batch_size, seq_len, input_size)
        lstm_out, _ = self.lstm(x) 
        # Get the output from the last time step
        last_out = lstm_out[:, -1, :] 
        x = self.batch_norm(last_out) 
        x = self.relu(self.fc1(x)) 
        x = self.dropout(x) 
        return self.fc2(x) 
