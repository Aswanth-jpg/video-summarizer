#!/usr/bin/env python3
"""Start the YouTube summarizer backend."""

import os
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8001"))

    print("Starting backend with start_server.py")
    print(f"Backend URL: http://localhost:{port}")
    print(f"API docs: http://localhost:{port}/docs")

    uvicorn.run(
        "simple_main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info",
    )
