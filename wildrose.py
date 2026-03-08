import threading
import uvicorn
import webview
from web_server import app

def start_server():
    # Run the FastAPI server via uvicorn in a separate thread
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

if __name__ == "__main__":
    # Start server thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Create the native desktop window using pywebview
    window = webview.create_window(
        "Wildrose - Eve", 
        "http://127.0.0.1:8000",
        width=1000, 
        height=600,
        min_size=(600, 400),
        background_color="#FFFFFF"
    )
    
    # Start the GUI event loop
    webview.start()
