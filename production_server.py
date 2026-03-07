
import os
import sys

# Cargar .env antes de cualquier import que use variables de entorno
from dotenv import load_dotenv
load_dotenv()

# Ensure current directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"==========================================")
    print(f"La Fija - Production Server Started")
    print(f"Access at: http://localhost:{port}")
    print(f"==========================================")
    
    # Serve using uvicorn (ASGI)
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
