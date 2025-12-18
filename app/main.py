from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.tts_router import router as tts_router
from app.api.image_router import router as image_router
from app.api.profile_extractor_router import router as profile_router
from app.api.html_report_router import router as html_report_router
from app.api.memory_router import router as memory_router
from app.api.chat_router import router as chat_router
from app.api.tools_router import router as tools_router

app = FastAPI(title="Blue Psychology API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tts_router)
app.include_router(image_router)
app.include_router(profile_router)
app.include_router(html_report_router)
app.include_router(memory_router)
app.include_router(chat_router)
app.include_router(tools_router)

@app.get("/")
async def root():
    return {"message": "Blue Psychology API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=15800, reload=True)
