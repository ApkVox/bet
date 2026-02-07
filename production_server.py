from waitress import serve
from main import app
import os
import sys

# Ensure current directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"==========================================")
    print(f"🚀 Courtside AI Production Server Started")
    print(f"👉 Access at: http://localhost:{port}")
    print(f"==========================================")
    
    # Serve using waitress
    serve(app, host="0.0.0.0", port=port, threads=6)
