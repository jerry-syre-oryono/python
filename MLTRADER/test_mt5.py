import MetaTrader5 as mt5 
 
if mt5.initialize(): 
    print("✅ MT5 initialized successfully") 
    print(f"Terminal info: {mt5.terminal_info()}") 
    mt5.shutdown() 
else: 
    print("❌ MT5 initialization failed")
