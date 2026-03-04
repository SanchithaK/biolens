-- Biolens Database Schema

CREATE TABLE IF NOT EXISTS samples (
	sample_id VARCHAR(50) PRIMARY KEY,
	cancer_type VARCHAR(100) DEFAULT 'BRCA',
	stage VARCHAR(30),
	subtype VARCHAR(50),
	survival_days INTEGER,
	vital_status VARCHAR(20),
	created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS genes (
	gene_id SERIAL PRIMARY KEY,
	gene_symbol VARCHAR(50) UNIQUE NOT NULL,
	chromosome VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS expression (
	id BIGSERIAL PRIMARY KEY,
	sample_id VARCHAR(50) REFERENCES samples(sample_id) ON DELETE CASCADE,
	gene_id INTEGER REFERENCES genes(gene_id) on DELETE CASCADE,
	log2_tpm FLOAT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_expr_sample ON expression(sample_id);
CREATE INDEX IF NOT EXISTS idx_expr_gene ON expression(gene_id);
CREATE INDEX IF NOT EXISTS idx_expr_both ON expression(sample_id, gene_id);

CREATE TABLE IF NOT EXISTS differential_results(
	id SERIAL PRIMARY KEY,
	analysis_name VARCHAR(100) NOT NULL,
	gene_id INTEGER REFERENCES genes(gene_id),
	log2fc FLOAT,
	pvalue FLOAT,
	padj FLOAT,
	direction VARCHAR(10),
	run_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_de_analysis ON differential_results(analysis_name);

