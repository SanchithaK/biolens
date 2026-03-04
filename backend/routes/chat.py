from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import anthropic, os
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

class InterpretRequest(BaseModel):
	question: str
	deg_results: Optional[List[dict]] = None #from analysis/differential
	gene_list: Optional[List[str]] = None

class ChatResponse(BaseModel):
	answer: str
	tokens_used: int

@router.post("/interpret", response_model=ChatResponse)
def interpret_results(req: InterpretRequest):
    """
    Use Claude to provide biological interpretation of differential expression results.
    """
    context = ""
    if req.deg_results:
        top = req.deg_results[:25]
        top_str = "\n".join([
            f"  {r['gene_symbol']}: log2FC={r['log2fc']:.2f}, padj={r['padj']:.2e}, direction={r['direction']}"
            for r in top
        ])
        context = f"\n\nTop differentially expressed genes:\n{top_str}"
    elif req.gene_list:
        context = f"\n\nGene list: {', '.join(req.gene_list[:50])}"

    prompt = f"""You are an expert computational biologist specializing in cancer genomics.

The researcher asks: {req.question}{context}

Please provide:
1. A biological interpretation of these findings (2-3 sentences)
2. The key molecular pathways likely involved
3. Potential clinical or therapeutic relevance
4. One concrete follow-up analysis you would recommend

Be precise, concise, and scientifically rigorous. Assume the reader has a graduate-level biology background."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}]
    )

    return ChatResponse(
        answer=response.content[0].text,
        tokens_used=response.usage.input_tokens + response.usage.output_tokens
    )


@router.post("/ask")
def ask_anything(req: InterpretRequest):
    """
    Free-form question answering about gene expression biology.
    No structured data required — just ask a question.
    """
    prompt = f"""You are a helpful computational biology assistant with deep expertise in:
- Bulk and single-cell RNA-seq analysis
- Cancer genomics and the tumor microenvironment  
- Differential expression and pathway analysis
- Machine learning for biological data

Answer this question clearly and accurately: {req.question}

If you reference specific genes, pathways, or methods, be precise."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )
    return {"answer": response.content[0].text}
