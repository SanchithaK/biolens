"""Cancer subtype classifier from gene expression profiles"""
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report
import joblib, os

os.makedirs("models", exist_ok =True)
MODEL_PATH = "models/subtype_classifier.pkl"

def train():
	print("Loading data...")
	expr = pd.read_csv("data/processed/expression_matrix.csv", index_col=0)
	clinical = pd.read_csv("data/processed/sample_metadata.csv", index_col=0)
	
	# Use PAM50 subtypes as labels
	shared = expr.index.intersection(clinical.index)
	X = expr.loc[shared]
	y = clinical.loc[shared, 'PAM50Call_RNAseq'].dropna()
	X = X.loc[y.index]

	print(f"Samples: {X.shape[0]} | Genes: {X.shape[1]}")
	print(f"Subtypes: \n{y.value_counts()}")

	# Encode labels
	le = LabelEncoder()
	y_enc = le.fit_transform(y)

	# Preprocess
	scaler = StandardScaler()
	X_scaled = scaler.fit_transform(X)

	pca = PCA(n_components = 50, random_state=42)
	X_pca = pca.fit_transform(X_scaled)
	print(f"PCA variance explained: {pca.explained_variance_ratio_.sum():.1%}")

	X_train, X_test, y_train, y_test = train_test_split(X_pca, y_enc, test_size = 0.2, stratify=y_enc, random_state=42)
	
	print("Training GradientBoosting classifier...")
	clf = GradientBoostingClassifier(n_estimators=200, max_depth=4, learning_rate=0.05, random_state=42)
	clf.fit(X_train, y_train)

	# Evaluate
	y_pred = clf.predict(X_test)
	print("\n--- Test Set Results ---")
	print(classification_report(y_test, y_pred, target_names = le.classes_))

	cv_scores = cross_val_score(clf, X_pca, y_enc, cv=5, scoring='accuracy')
	print(f"5-fold CV accuract: {cv_scores.mean():.3f} +/- {cv_scores.std():.3f}")

	# Save everything needed for inference
	joblib.dump({
		"model": clf,
		"scaler": scaler, 
		"pca": pca, 
		"label_encoder": le,
		"feature_names": X.columns.tolist(),
		"cv_accuracy": cv_scores.mean()}, MODEL_PATH)
	print(f"\n Model saved to {MODEL_PATH}")
	return cv_scores.mean()

def predict(expression_dict:dict) -> dict:
	"""Predict cancer subtype from a dict of gene to expression values."""
	bundle = joblib.load(MODEL_PATH)
	clf = bundle['model']
	scaler = bundle['scaler']
	pca = bundle['pca']
	le = bundle['label_encoder']
	features = bundle['feature_names']

	vec = pd.Series(expression_dict).reindex(features,fill_value=0).values.reshape(1, -1)
	vec_scaled = scaler.transform(vec)
	vec_pca = pca.transform(vec_scaled)

	pred = clf.predict(vec_pca)[0]
	proba = clf.predict_proba(vec_pca)[0]
	
	return{
		"predicted_subtype": le.classes_[pred],
		"confidence": round(float(max(proba)), 3),
		"all_probabilities": { cls: round(float(p), 3) for cls, p in zip(le.classes_, proba) }
	}

if __name__ == "__main__":
	accuracy = train()
	print(f"\nFinal CV accuracy: {accuracy:.1%}")
