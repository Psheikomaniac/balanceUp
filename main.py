import os
import sys

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from app.routers import penalties, users
from app.database.models import init_db

app = FastAPI(
    title="Penalties Management API",
    description="API for managing penalties and users.",
    version="1.0.0"
)

# Initialize the database
init_db()

app.include_router(penalties.router)
app.include_router(users.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8011, reload=True)