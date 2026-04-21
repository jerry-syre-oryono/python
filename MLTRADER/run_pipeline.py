# run_pipeline.py
import numpy as np
import os
from train import train_model
from export_to_onnx import export_to_onnx

def main():
    # 1. Load Dataset
    if not os.path.exists("X_train.npy") or not os.path.exists("y_train.npy"):
        print("Running prepare_dataset.py...")
        import subprocess
        import sys
        subprocess.run([sys.executable, "prepare_dataset.py"], check=True)
    
    X = np.load("X_train.npy")
    y = np.load("y_train.npy")
    
    print(f"Dataset loaded: X={X.shape}, y={y.shape}")
    
    # 2. Train Model
    print("Starting training...")
    model = train_model(X, y, epochs=30)
    print("✅ Training complete.")
    
    # 3. Export to ONNX
    print("Exporting to ONNX...")
    # input_shape is (seq_len, features)
    input_shape = (X.shape[1], X.shape[2])
    export_to_onnx(model, input_shape, filepath="strategy_model.onnx")
    print("✅ Pipeline complete. Model saved as strategy_model.onnx")

if __name__ == "__main__":
    main()
