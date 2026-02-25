"""Entry point — starts the FastAPI backend on port 8001."""

import os
import uvicorn

os.chdir(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
