# export_to_onnx.py 
import torch 
import onnx 
 
def export_to_onnx(model, input_shape, filepath="strategy_model.onnx"): 
    """Export PyTorch model to ONNX format""" 
    model.eval() 
    # input_shape: (seq_len, input_size)
    dummy_input = torch.randn(1, *input_shape) 
    
    torch.onnx.export( 
        model, 
        dummy_input, 
        filepath, 
        input_names=['input'], 
        output_names=['output'], 
        dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}, 
        opset_version=12 
    ) 
    
    # Verify 
    onnx_model = onnx.load(filepath) 
    onnx.checker.check_model(onnx_model) 
    print(f"✅ Model exported to {filepath}") 

if __name__ == "__main__":
    from model import LSTMPredictor
    # Test export with a fresh model
    model = LSTMPredictor(input_size=10)
    export_to_onnx(model, input_shape=(20, 10), filepath="test_model.onnx")
