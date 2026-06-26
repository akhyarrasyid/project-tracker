from fastapi import FastAPI
from database import engine, Base
from routers.tasks import router as tasks_router

# Initialize database schemas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Project Tracker API")

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Include routers
app.include_router(tasks_router)