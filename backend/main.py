from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes import expression, analysis, chat

app = FastAPI ( title="BioLens API", description="AI-powered gene expression analysis platform", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(expression.router, prefix="/expression", tags=["Expression"])
app.include_router(analysis.router, prefix="/analysis", tags=["Analysis"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])

@app.get("/")
def root():
	return {"message": "Biolens API is running", "docs": "/docs"}

