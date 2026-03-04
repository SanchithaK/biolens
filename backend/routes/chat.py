from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
import anthropic, os
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

class ChatQuery(BaseModel):
    question: str
    context_genes: Optional[List[str]] = None

@router.post("/ask")
def ask(query: ChatQuery):
    """Natural language question answering about gene expression biology."""
    prompt = f"""You are a helpful computational biology assistant with expertise in:
- Bulk RNA-seq and cancer genomics
- Differential expression and pathway analysis  
- The tumor microenvironment
- TCGA datasets

Answer this question clearly and accurately: {query.question}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )
    return {"answer": response.content[0].text}
