#!/usr/bin/env python3
"""
Clean Term Similarity Clustering Script
1. Create semantic embeddings for terms
2. Create clusterings where all terms are assigned a cluster  
3. Create names for clusters using Ollama
4. Run analysis for both 'Art' and 'Einsatzbereich' columns
"""

import os
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

import pandas as pd
import numpy as np
import requests
from sklearn.cluster import AgglomerativeClustering, DBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.neighbors import NearestNeighbors
from sentence_transformers import SentenceTransformer
import matplotlib.pyplot as plt
from collections import Counter

def analyze_column(column_name, df, model):
    """Analyze terms from a specific column"""
    print(f"\n{'='*60}")
    print(f"=== ANALYZING COLUMN: {column_name.upper()} ===")
    print(f"{'='*60}")
    
    # Load and extract terms
    print("=== Loading and Extracting Terms ===")
    all_terms = []
    for index, row in df.iterrows(): 
        if pd.notna(row[column_name]):
            terms = [term.strip() for term in row[column_name].split(",") if term.strip()]
            all_terms.extend(terms)

    unique_terms = list(set(all_terms))
    term_counts = Counter(all_terms)

    print(f"Total terms: {len(all_terms)}")
    print(f"Unique terms: {len(unique_terms)}")
    print(f"Top 5 most common: {term_counts.most_common(5)}")

    # 1. CREATE SEMANTIC EMBEDDINGS
    print("\n=== Creating Semantic Embeddings ===")
    embeddings = model.encode(unique_terms)
    print(f"Embeddings shape: {embeddings.shape}")
    
    return all_terms, unique_terms, term_counts, embeddings

# Load data and initialize model
print("=== Initializing ===")
df = pd.read_csv("/Users/ramius/Desktop/CodeVault/Caritas Datenprojekt/datenprojekte_git/MarkdownConverter/data/csv/combined_all_projects.csv", sep=";")
model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')

# Analyze both columns
columns_to_analyze = ["Art", "Einsatzbereich"]
analysis_results = {}

for column_name in columns_to_analyze:
    all_terms, unique_terms, term_counts, embeddings = analyze_column(column_name, df, model)
    analysis_results[column_name] = {
        'all_terms': all_terms,
        'unique_terms': unique_terms, 
        'term_counts': term_counts,
        'embeddings': embeddings
    }

def find_optimal_clusters(embeddings, unique_terms, max_k=20):
    """Find optimal number of clusters using silhouette score"""
    if len(unique_terms) < 4:
        return 2
    
    max_k = min(max_k, len(unique_terms)//2)
    silhouette_scores = []
    K_range = range(2, max_k + 1)
    
    for k in K_range:
        hierarchical = AgglomerativeClustering(n_clusters=k, linkage='ward')
        labels = hierarchical.fit_predict(embeddings)
        silhouette_scores.append(silhouette_score(embeddings, labels))
    
    optimal_k = K_range[np.argmax(silhouette_scores)]
    print(f"Optimal number of clusters: {optimal_k}")
    return optimal_k

def reassign_noise_to_clusters(embeddings, labels):
    """Reassign noise points (-1) to nearest cluster centroid"""
    if -1 not in labels:
        return labels
    
    labels = labels.copy()
    valid_labels = set(labels) - {-1}
    
    if not valid_labels:
        labels[:] = 0  # All noise -> single cluster
        return labels
    
    # Calculate cluster centroids
    centroids = {}
    for cluster_id in valid_labels:
        cluster_mask = labels == cluster_id
        centroids[cluster_id] = np.mean(embeddings[cluster_mask], axis=0)
    
    # Assign noise points to nearest centroid
    noise_indices = np.where(labels == -1)[0]
    for idx in noise_indices:
        distances = [np.linalg.norm(embeddings[idx] - centroid) 
                    for centroid in centroids.values()]
        best_cluster = list(centroids.keys())[np.argmin(distances)]
        labels[idx] = best_cluster
    
    return labels

def perform_clustering_analysis(column_name, unique_terms, embeddings, term_counts):
    """Perform complete clustering analysis for a column"""
    print(f"\n=== CLUSTERING ANALYSIS FOR {column_name.upper()} ===")
    
    # Find optimal number of clusters
    optimal_k = find_optimal_clusters(embeddings, unique_terms)

    # Perform different clustering algorithms
    clustering_results = {}

    # Hierarchical Clustering
    print("Performing Hierarchical clustering...")
    hierarchical = AgglomerativeClustering(n_clusters=optimal_k, linkage='ward')
    clustering_results['Hierarchical'] = hierarchical.fit_predict(embeddings)

    # K-Means Clustering  
    print("Performing K-Means clustering...")
    kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
    clustering_results['K-Means'] = kmeans.fit_predict(embeddings)

    # DBSCAN Clustering (with noise reassignment)
    print("Performing DBSCAN clustering...")
    neighbors = NearestNeighbors(n_neighbors=3)
    neighbors_fit = neighbors.fit(embeddings)
    distances, _ = neighbors_fit.kneighbors(embeddings)
    optimal_eps = np.median(np.sort(distances[:, 2]))

    dbscan = DBSCAN(eps=optimal_eps, min_samples=2)
    dbscan_labels = dbscan.fit_predict(embeddings)
    dbscan_labels = reassign_noise_to_clusters(embeddings, dbscan_labels)
    clustering_results['DBSCAN'] = dbscan_labels

    # Select best clustering method based on silhouette score
    print("\n=== Selecting Best Clustering Method ===")
    best_method = None
    best_score = -1
    best_labels = None

    for method, labels in clustering_results.items():
        if len(set(labels)) > 1:
            score = silhouette_score(embeddings, labels)
            print(f"{method}: {len(set(labels))} clusters, silhouette={score:.3f}")
            if score > best_score:
                best_score = score
                best_method = method
                best_labels = labels

    print(f"\nBest method: {best_method} (silhouette={best_score:.3f})")

    # Create clusters dictionary
    clusters = {}
    for term, label in zip(unique_terms, best_labels):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(term)

    print(f"Final clustering: {len(clusters)} clusters, all {len(unique_terms)} terms assigned")

    # Generate cluster names using Ollama
    print("\n=== Generating Cluster Names with Ollama ===")
    cluster_names = generate_cluster_names_ollama(clusters)
    
    # Create and save visualization
    create_visualization(column_name, embeddings, clusters, cluster_names, best_labels, best_method, unique_terms)
    
    # Export results
    export_results(column_name, unique_terms, best_labels, cluster_names, term_counts)
    
    return clusters, cluster_names, best_labels, best_method

def generate_cluster_names_ollama(clusters_dict, model_name='llama3.2:latest'):
    """Generate cluster names using Ollama"""
    cluster_names = {}
    
    # Test Ollama connection first
    try:
        test_response = requests.get('http://localhost:11434/api/tags', timeout=5)
        if test_response.status_code != 200:
            print("❌ Warning: Ollama server not responding. Using fallback names.")
            ollama_available = False
        else:
            print("✅ Ollama server connected successfully")
            ollama_available = True
    except Exception as e:
        print(f"❌ Warning: Cannot connect to Ollama ({e}). Using fallback names.")
        ollama_available = False
    
    for cluster_id, cluster_terms in clusters_dict.items():
        terms_text = ', '.join(cluster_terms)
        
        if not ollama_available:
            # Simple fallback: use most common word or first term
            cluster_name = cluster_terms[0] if cluster_terms else f"Group_{cluster_id}"
        else:
            prompt = f"""Diese deutschen Begriffe wurden zusammengruppiert: {terms_text}

Erstelle einen kurzen Kategorienamen (1-3 Wörter), der erfasst, was diese Begriffe gemeinsam haben.
Antworte nur mit dem Kategorienamen auf Deutsch, nichts anderes."""
            
            try:
                print(f"🤖 Asking Ollama about cluster {cluster_id}: {terms_text[:50]}...")
                
                response = requests.post(
                    'http://localhost:11434/api/generate',
                    json={
                        'model': model_name,
                        'prompt': prompt,
                        'stream': False,
                        'options': {
                            'temperature': 0.1,  # Lower temperature for more consistent results
                            'top_p': 0.8,
                            'num_predict': 10    # Fewer tokens for shorter responses
                        }
                    },
                    timeout=45  # Longer timeout
                )
                
                print(f"📡 Response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    raw_response = result.get('response', '').strip()
                    print(f"📝 Raw Ollama response: '{raw_response}'")
                    
                    # Clean up the response
                    cluster_name = raw_response.split('\n')[0].strip()
                    cluster_name = cluster_name.strip('"\'.–:')
                    
                    # Validate the response
                    if (not cluster_name or 
                        len(cluster_name.split()) > 4 or 
                        cluster_name.lower().startswith('category') or
                        len(cluster_name) > 30):
                        print("⚠️  Invalid response, using fallback")
                        cluster_name = cluster_terms[0] if cluster_terms else f"Group_{cluster_id}"
                    else:
                        print(f"✅ Good response: '{cluster_name}'")
                else:
                    print(f"❌ HTTP error {response.status_code}: {response.text}")
                    cluster_name = cluster_terms[0] if cluster_terms else f"Group_{cluster_id}"
                    
            except Exception as e:
                print(f"❌ Ollama error for cluster {cluster_id}: {e}")
                cluster_name = cluster_terms[0] if cluster_terms else f"Group_{cluster_id}"
        
        cluster_names[cluster_id] = {
            'name': cluster_name,
            'terms': cluster_terms,
            'size': len(cluster_terms)
        }
        
        print(f"🏷️  Cluster {cluster_id}: '{cluster_name}' <- {', '.join(cluster_terms[:3])}{'...' if len(cluster_terms) > 3 else ''}")
    
    return cluster_names

def create_visualization(column_name, embeddings, clusters, cluster_names, best_labels, best_method, unique_terms):
    """Create and save PCA visualization"""
    print(f"\n=== Creating Visualization for {column_name} ===")
    pca = PCA(n_components=2, random_state=42)
    embeddings_2d = pca.fit_transform(embeddings)

    plt.figure(figsize=(15, 10))
    # Use better color palette for distinction
    colors = plt.cm.tab20(np.linspace(0, 1, len(clusters)))

    for i, (cluster_id, cluster_terms) in enumerate(clusters.items()):
        mask = best_labels == cluster_id
        cluster_name = cluster_names[cluster_id]['name']
        
        plt.scatter(embeddings_2d[mask, 0], embeddings_2d[mask, 1], 
                   c=[colors[i]], label=f'{cluster_name} ({len(cluster_terms)})', 
                   alpha=0.8, s=80, edgecolors='black', linewidth=0.5)
        
        # Add term names as text annotations with cluster-specific colors
        for j, (x, y) in enumerate(embeddings_2d[mask]):
            term_idx = np.where(mask)[0][j]
            term_name = unique_terms[term_idx]
            plt.annotate(term_name, (x, y), xytext=(3, 3), textcoords='offset points',
                        fontsize=8, alpha=0.9, color=colors[i], fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7, edgecolor='none'))

    plt.xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%} variance)')
    plt.ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%} variance)')
    plt.title(f'{best_method} Clustering - {column_name}')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'term_clustering_{column_name.lower()}.png', dpi=300, bbox_inches='tight')
    plt.close()

def export_results(column_name, unique_terms, best_labels, cluster_names, term_counts):
    """Export results to CSV files"""
    print(f"\n=== Exporting Results for {column_name} ===")
    
    # Detailed results
    results_data = []
    for term, label in zip(unique_terms, best_labels):
        cluster_info = cluster_names[label]
        results_data.append({
            'term': term,
            'cluster_id': label,
            'cluster_name': cluster_info['name'],
            'cluster_size': cluster_info['size'],
            'frequency': term_counts.get(term, 0)
        })

    results_df = pd.DataFrame(results_data)
    results_df.to_csv(f'term_clustering_{column_name.lower()}_results.csv', index=False)

    # Summary
    summary_data = []
    for cluster_id, info in cluster_names.items():
        total_freq = sum(term_counts.get(term, 0) for term in info['terms'])
        summary_data.append({
            'cluster_id': cluster_id,
            'cluster_name': info['name'],
            'cluster_size': info['size'],
            'total_frequency': total_freq,
            'terms': ', '.join(sorted(info['terms']))
        })

    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(f'term_clustering_{column_name.lower()}_summary.csv', index=False)
    
    print(f"✅ Results for {column_name} saved to:")
    print(f"   - term_clustering_{column_name.lower()}_results.csv (detailed)")  
    print(f"   - term_clustering_{column_name.lower()}_summary.csv (summary)")
    print(f"   - term_clustering_{column_name.lower()}.png (visualization)")

# Process each column
for column_name in columns_to_analyze:
    data = analysis_results[column_name]
    clusters, cluster_names, best_labels, best_method = perform_clustering_analysis(
        column_name, 
        data['unique_terms'], 
        data['embeddings'], 
        data['term_counts']
    )
    
    # Display results
    print(f"\n=== Final Cluster Names for {column_name.upper()} ===")
    for cluster_id in sorted(cluster_names.keys()):
        info = cluster_names[cluster_id]
        print(f"\n🏷️  Cluster {cluster_id}: '{info['name']}' ({info['size']} terms)")
        print(f"    📋 Terms: {', '.join(sorted(info['terms']))}")
    
    print(f"\n📊 {column_name} Summary: {len(clusters)} clusters, {len(data['unique_terms'])} terms, all assigned!")

print(f"\n{'='*80}")
print("🎉 ANALYSIS COMPLETE FOR BOTH COLUMNS!")
print(f"{'='*80}")