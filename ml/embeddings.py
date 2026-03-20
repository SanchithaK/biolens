import chromadb
import os

chroma = chromadb.PersistentClient(path="./chroma_db")
collection = chroma.get_or_create_collection(name="genes", metadata={"hnsw:space": "cosine"})

_model = None

def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def _is_indexed():
    return collection.count() > 0

def index_genes_from_db():
    import mygene
    from sqlalchemy import create_engine, text
    from dotenv import load_dotenv
    load_dotenv()

    engine = create_engine(os.getenv("DATABASE_URL"))
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT gene_id, gene_symbol FROM genes")).fetchall()

    print(f"Fetching biological descriptions for {len(rows)} genes...")
    mg = mygene.MyGeneInfo()
    symbols = [r.gene_symbol for r in rows]
    
    # Fetch gene summaries in batches
    results = mg.querymany(symbols, scopes='symbol', 
                           fields='summary,name,go.BP', 
                           species='human', returnall=True)
    
    gene_info = {}
    for hit in results['out']:
        if 'query' in hit and 'summary' in hit:
            gene_info[hit['query']] = hit['summary']
        elif 'query' in hit and 'name' in hit:
            gene_info[hit['query']] = hit['name']

    print("Indexing into ChromaDB...")
    model = _get_model()
    
    # Delete existing collection and recreate
    chroma.delete_collection("genes")
    global collection
    collection = chroma.get_or_create_collection(name="genes", 
                    metadata={"hnsw:space": "cosine"})

    batch_size = 200
    gene_rows = list(rows)
    for i in range(0, len(gene_rows), batch_size):
        batch = gene_rows[i:i+batch_size]
        ids, documents, metadatas = [], [], []
        for r in batch:
            desc = gene_info.get(r.gene_symbol, 
                   f"Gene {r.gene_symbol}: expressed in breast cancer")
            ids.append(f"gene_{r.gene_id}")
            documents.append(f"{r.gene_symbol}: {desc}")
            metadatas.append({"gene_symbol": r.gene_symbol})
        
        embeddings = model.encode(documents).tolist()
        collection.add(ids=ids, embeddings=embeddings,
                       documents=documents, metadatas=metadatas)
        if i % 1000 == 0:
            print(f"  {i+len(batch)}/{len(gene_rows)} indexed...")
    
    print(f"Indexed {len(rows)} genes.")

def semantic_search(query: str, n_results: int = 10) -> list:
    """Search genes by biological meaning. Auto-indexes on first call."""
    if not _is_indexed():
        print("ChromaDB empty — indexing genes from database...")
        index_genes_from_db()

    model = _get_model()
    query_embedding = model.encode([query]).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=n_results)

    return [
        {"gene_symbol": m["gene_symbol"], "description": d, "similarity": round(1 - dist, 3)}
        for m, d, dist in zip(
            results["metadatas"][0],
            results["documents"][0],
            results["distances"][0]
        )
    ]	
