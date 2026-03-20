from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.database import get_db
from typing import Optional

router = APIRouter()

@router.get("/samples")
def list_samples(
    stage: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db)
):
    """List samples with optional stage filter."""
    if stage:
        query = "SELECT * FROM samples WHERE stage = :stage LIMIT :limit"
        params = {"stage": stage, "limit": limit}
    else:
        query = "SELECT * FROM samples LIMIT :limit"
        params = {"limit": limit}

    rows = db.execute(text(query), params).fetchall()
    return [dict(r._mapping) for r in rows]

@ router.get("/{gene_symbol}")
def get_expression(gene_symbol: str, stage: Optional[str]=None, db: Session = Depends(get_db)):
	"""Get expression values for a specific gene across all samples"""
	query = """
		SELECT s.sample_id, s.stage, s.subtype, e.log2_tpm
		FROM expression e
		JOIN genes g ON e.gene_id = g.gene_id
		JOIN samples s ON e.sample_id = s.sample_id
		WHERE UPPER(g.gene_symbol) = UPPER(:gene)
	"""
	params = {"gene": gene_symbol}
	if stage:
		query += "AND s.stage= :stage"
		params["stage"]=stage
	
	rows = db.execute(text(query), params).fetchall()
	if not rows:
		raise HTTPException(status_code = 404, detail=f"Gene {gene_symbol} not found")
	return {"gene": gene_symbol, "n_samples": len(rows), "data": [dict(r._mapping) for r in rows]}

@router.get("/summary/top_variable")
def top_variable_genes(n: int=Query(50, le=500), db: Session=Depends(get_db)):
	"""Returns the top N most variable genes across all samples"""
	query = """
		SELECT g.gene_symbol, VARIANCE(e.log2_tpm) AS variance
		FROM expression e
		JOIN genes g ON e.gene_id = g.gene_id
		GROUP BY g.gene_symbol
		ORDER BY variance DESC
		LIMIT :n
	"""
	rows = db.execute(text(query), {"n":n}).fetchall()
	return [dict(r._mapping) for r in rows]

@router.get("/search/semantic")
def semantic_gene_search(query: str, n:int=10):
	""" Search for genes by biological meaning using vector similarity."""
	from ml.embeddings import semantic_search
	return semantic_search(query, n)
