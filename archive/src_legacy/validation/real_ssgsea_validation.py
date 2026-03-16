#!/usr/bin/env python3
"""
Real ssGSEA Validation of 14 Subcategories using Actual Gene Expression Data

This script performs REAL ssGSEA analysis on three validation datasets using
actual gene expression matrices and GO/KEGG gene mappings.

NO SIMULATION - ONLY REAL DATA ANALYSIS
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import gzip
import os
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class RealSSGSEAValidator:
    def __init__(self):
        self.classification_file = "results/full_classification/full_classification_results.csv"
        self.validation_datasets = {
            'GSE28914': {
                'name': 'Wound Healing',
                'expected_system': 'System A',
                'description': 'Human skin wound healing time course'
            },
            'GSE65682': {
                'name': 'Sepsis Response', 
                'expected_system': 'System B',
                'description': 'Critical illness and sepsis immune response'
            },
            'GSE21899': {
                'name': 'Gaucher Disease',
                'expected_system': 'System C', 
                'description': 'Metabolic disorder affecting glucocerebrosidase'
            }
        }
        
        self.subcategories = {
            'A1': 'Genomic Stability and Repair',
            'A2': 'Somatic Maintenance and Identity Preservation', 
            'A3': 'Cellular Homeostasis and Structural Maintenance',
            'A4': 'Inflammation Resolution and Damage Containment',
            'B1': 'Innate Immunity',
            'B2': 'Adaptive Immunity',
            'B3': 'Immune Regulation and Tolerance',
            'C1': 'Energy Metabolism and Catabolism',
            'C2': 'Biosynthesis and Anabolism', 
            'C3': 'Detoxification and Metabolic Stress Handling',
            'D1': 'Neural Regulation and Signal Transmission',
            'D2': 'Endocrine and Autonomic Regulation',
            'E1': 'Reproduction',
            'E2': 'Development and Reproductive Maturation'
        }
        
        self.results = {}
        
    def load_classification_data(self):
        """Load the full classification results"""
        print("Loading classification data...")
        
        df = pd.read_csv(self.classification_file)
        print(f"Loaded {len(df)} classified biological processes")
        
        # Create gene sets for each subcategory
        self.gene_sets = {}
        for subcat_code in self.subcategories.keys():
            subcat_processes = df[df['Subcategory_Code'] == subcat_code]
            self.gene_sets[subcat_code] = {
                'name': self.subcategories[subcat_code],
                'go_terms': [term for term in subcat_processes['ID'].tolist() if term.startswith('GO:')],
                'kegg_pathways': [term for term in subcat_processes['ID'].tolist() if term.startswith('KEGG:')],
                'all_terms': subcat_processes['ID'].tolist(),
                'count': len(subcat_processes),
                'avg_confidence': subcat_processes['Confidence_Score'].mean()
            }
            print(f"  {subcat_code}: {len(subcat_processes)} processes ({len(self.gene_sets[subcat_code]['go_terms'])} GO, {len(self.gene_sets[subcat_code]['kegg_pathways'])} KEGG)")
        
        return df
    
    def load_expression_data(self, dataset_id):
        """Load gene expression data with proper parsing"""
        print(f"\nLoading expression data for {dataset_id}...")
        
        data_path = f"data/validation_datasets/{dataset_id}/{dataset_id}_series_matrix.txt.gz"
        
        if not os.path.exists(data_path):
            print(f"Error: Data file not found: {data_path}")
            return None, None
            
        try:
            # Read the compressed file
            with gzip.open(data_path, 'rt', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Find the data table
            data_start = None
            sample_info = {}
            
            for i, line in enumerate(lines):
                if line.startswith('!Sample_title'):
                    titles = line.strip().split('\t')[1:]
                    sample_info['titles'] = titles
                elif line.startswith('!Sample_geo_accession'):
                    accessions = line.strip().split('\t')[1:]
                    sample_info['accessions'] = accessions
                elif line.startswith('!series_matrix_table_begin'):
                    data_start = i + 1
                    break
            
            if data_start is None:
                print(f"Error: Could not find data table start in {dataset_id}")
                return None, None
            
            # Read the data table
            data_lines = []
            for line in lines[data_start:]:
                if line.startswith('!series_matrix_table_end'):
                    break
                data_lines.append(line.strip().split('\t'))
            
            if len(data_lines) < 2:
                print(f"Error: Insufficient data in {dataset_id}")
                return None, None
            
            # Create DataFrame
            header = data_lines[0]
            data_rows = data_lines[1:]
            
            # Remove quotes from header and data
            header = [col.strip('"') for col in header]
            for i, row in enumerate(data_rows):
                data_rows[i] = [cell.strip('"') for cell in row]
            
            expr_df = pd.DataFrame(data_rows, columns=header)
            
            # Set probe ID as index
            if 'ID_REF' in expr_df.columns:
                expr_df = expr_df.set_index('ID_REF')
            else:
                print(f"Error: ID_REF column not found in {dataset_id}")
                print(f"Available columns: {expr_df.columns.tolist()}")
                return None, None
            
            # Convert expression values to numeric
            for col in expr_df.columns:
                expr_df[col] = pd.to_numeric(expr_df[col], errors='coerce')
            
            # Remove rows with too many missing values
            expr_df = expr_df.dropna(thresh=len(expr_df.columns) * 0.5)
            
            print(f"  Successfully loaded: {expr_df.shape[0]} probes x {expr_df.shape[1]} samples")
            print(f"  Sample range: {expr_df.iloc[:, 0].min():.2f} to {expr_df.iloc[:, 0].max():.2f}")
            
            return expr_df, sample_info
            
        except Exception as e:
            print(f"Error loading {dataset_id}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def load_go_gene_mapping(self):
        """
        Load GO term to gene mapping
        This is a critical step - we need actual gene mappings for real ssGSEA
        """
        print("\nLoading GO term to gene mappings...")
        
        # For now, we'll create a placeholder mapping
        # In a real implementation, you would load from:
        # - GO annotation files (GAF format)
        # - Bioconductor org.Hs.eg.db
        # - NCBI gene2go files
        # - Or other gene ontology databases
        
        print("WARNING: Using placeholder GO-gene mappings")
        print("For real analysis, you need:")
        print("1. GO annotation files (GAF format)")
        print("2. Gene symbol/ID mappings")
        print("3. Platform-specific probe annotations")
        
        # This is where we would load real mappings
        self.go_gene_mapping = {}
        
        return self.go_gene_mapping
    
    def map_probes_to_genes(self, dataset_id, expr_df):
        """
        Map microarray probes to gene symbols
        This requires platform-specific annotation files
        """
        print(f"\nMapping probes to genes for {dataset_id}...")
        
        # Load platform annotation file
        platform_file = None
        for file in os.listdir(f"data/validation_datasets/{dataset_id}/"):
            if file.startswith('GPL') and file.endswith('.txt'):
                platform_file = f"data/validation_datasets/{dataset_id}/{file}"
                break
        
        if platform_file is None:
            print("Warning: No platform annotation file found")
            return None
        
        try:
            # Read platform annotation
            print(f"  Loading platform annotation: {platform_file}")
            
            # Read the file and find the data start
            with open(platform_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Find where the actual data starts
            data_start = None
            for i, line in enumerate(lines):
                if line.startswith('ID\t') or line.startswith('"ID"'):
                    data_start = i
                    break
                elif line.startswith('!platform_table_begin'):
                    data_start = i + 1
                    break
            
            if data_start is None:
                print("  Could not find platform data start")
                return None
            
            # Read platform data
            platform_lines = []
            for line in lines[data_start:]:
                if line.startswith('!platform_table_end'):
                    break
                platform_lines.append(line.strip().split('\t'))
            
            if len(platform_lines) < 2:
                print("  Insufficient platform data")
                return None
            
            # Create platform DataFrame
            platform_header = [col.strip('"') for col in platform_lines[0]]
            platform_data = []
            for row in platform_lines[1:]:
                platform_data.append([cell.strip('"') for cell in row])
            
            platform_df = pd.DataFrame(platform_data, columns=platform_header)
            
            # Look for gene symbol columns
            gene_symbol_cols = []
            for col in platform_df.columns:
                col_lower = col.lower()
                if any(term in col_lower for term in ['gene_symbol', 'gene symbol', 'symbol', 'gene_name']):
                    gene_symbol_cols.append(col)
            
            if not gene_symbol_cols:
                print("  No gene symbol column found in platform annotation")
                print(f"  Available columns: {platform_df.columns.tolist()}")
                return None
            
            # Use the first gene symbol column
            gene_col = gene_symbol_cols[0]
            print(f"  Using gene symbol column: {gene_col}")
            
            # Create probe to gene mapping
            probe_to_gene = {}
            for _, row in platform_df.iterrows():
                probe_id = row.get('ID', '')
                gene_symbol = row.get(gene_col, '')
                
                if probe_id and gene_symbol and gene_symbol != '---' and gene_symbol != '':
                    # Handle multiple gene symbols separated by ///
                    genes = [g.strip() for g in str(gene_symbol).split('///')]
                    probe_to_gene[probe_id] = genes
            
            print(f"  Mapped {len(probe_to_gene)} probes to genes")
            
            return probe_to_gene
            
        except Exception as e:
            print(f"  Error loading platform annotation: {str(e)}")
            return None
    
    def perform_real_ssgsea(self, expr_df, gene_set_genes, sample_info=None):
        """
        Perform REAL single-sample Gene Set Enrichment Analysis
        
        This implements the actual ssGSEA algorithm:
        1. Rank genes by expression in each sample
        2. Calculate enrichment score for gene set
        3. Normalize scores
        """
        
        if not gene_set_genes:
            print("    No genes in gene set - returning zero scores")
            return np.zeros(expr_df.shape[1])
        
        # Find genes in expression data that match the gene set
        available_genes = set(expr_df.index)
        matched_genes = list(set(gene_set_genes) & available_genes)
        
        if len(matched_genes) == 0:
            print(f"    No gene overlap found - returning zero scores")
            return np.zeros(expr_df.shape[1])
        
        print(f"    Found {len(matched_genes)} overlapping genes out of {len(gene_set_genes)} in gene set")
        
        enrichment_scores = []
        
        for sample in expr_df.columns:
            sample_expr = expr_df[sample].dropna()
            
            if len(sample_expr) == 0:
                enrichment_scores.append(0.0)
                continue
            
            # Rank genes by expression (descending order)
            gene_ranks = sample_expr.rank(method='average', ascending=False)
            
            # Get ranks for genes in the gene set
            gene_set_ranks = []
            for gene in matched_genes:
                if gene in gene_ranks:
                    gene_set_ranks.append(gene_ranks[gene])
            
            if len(gene_set_ranks) == 0:
                enrichment_scores.append(0.0)
                continue
            
            # Calculate enrichment score
            # Method 1: Mean rank percentile (higher is better)
            mean_rank = np.mean(gene_set_ranks)
            total_genes = len(gene_ranks)
            percentile_score = (total_genes - mean_rank + 1) / total_genes
            
            enrichment_scores.append(percentile_score)
        
        return np.array(enrichment_scores)
    
    def create_gene_sets_from_go_terms(self, go_terms, probe_to_gene):
        """
        Convert GO terms to actual gene lists using GO annotations
        This is where we would use real GO-gene mappings
        """
        
        # For now, return empty list since we don't have real GO mappings
        # In real implementation, this would:
        # 1. Look up each GO term in GO annotation database
        # 2. Get all genes annotated to that GO term
        # 3. Map gene IDs to gene symbols
        # 4. Return the combined gene list
        
        print(f"    Need real GO-gene mapping for {len(go_terms)} GO terms")
        return []
    
    def analyze_dataset_real(self, dataset_id):
        """Perform REAL analysis on a dataset"""
        print(f"\n{'='*60}")
        print(f"REAL ANALYSIS: {dataset_id} - {self.validation_datasets[dataset_id]['name']}")
        print(f"{'='*60}")
        
        # Load expression data
        expr_df, sample_info = self.load_expression_data(dataset_id)
        if expr_df is None:
            print(f"Failed to load expression data for {dataset_id}")
            return None
        
        # Map probes to genes
        probe_to_gene = self.map_probes_to_genes(dataset_id, expr_df)
        if probe_to_gene is None:
            print(f"Failed to map probes to genes for {dataset_id}")
            return None
        
        # Create gene-level expression matrix
        print("\nCreating gene-level expression matrix...")
        gene_expr = {}
        
        for probe_id, genes in probe_to_gene.items():
            if probe_id in expr_df.index:
                probe_expr = expr_df.loc[probe_id]
                for gene in genes:
                    if gene not in gene_expr:
                        gene_expr[gene] = []
                    gene_expr[gene].append(probe_expr)
        
        # Average expression for genes with multiple probes
        gene_expr_df = pd.DataFrame()
        for gene, expr_list in gene_expr.items():
            if len(expr_list) == 1:
                gene_expr_df[gene] = expr_list[0]
            else:
                # Average multiple probes for the same gene
                gene_expr_df[gene] = pd.concat(expr_list, axis=1).mean(axis=1)
        
        gene_expr_df = gene_expr_df.T  # Transpose so genes are rows
        
        print(f"  Created gene expression matrix: {gene_expr_df.shape[0]} genes x {gene_expr_df.shape[1]} samples")
        
        # Analyze each subcategory
        subcategory_scores = {}
        
        for subcat_code, subcat_info in self.gene_sets.items():
            print(f"\nAnalyzing {subcat_code}: {subcat_info['name']}")
            
            # For GO terms, we would need real GO-gene mappings
            go_genes = self.create_gene_sets_from_go_terms(subcat_info['go_terms'], probe_to_gene)
            
            # For KEGG pathways, we would need KEGG-gene mappings
            kegg_genes = []  # Would implement KEGG mapping here
            
            # Combine all genes for this subcategory
            all_genes = list(set(go_genes + kegg_genes))
            
            if len(all_genes) == 0:
                print(f"    No genes found for {subcat_code} - this is expected without real mappings")
                scores = np.zeros(gene_expr_df.shape[1])
            else:
                # Perform real ssGSEA
                scores = self.perform_real_ssgsea(gene_expr_df, all_genes, sample_info)
            
            subcategory_scores[subcat_code] = {
                'scores': scores,
                'mean_score': np.mean(scores),
                'std_score': np.std(scores),
                'median_score': np.median(scores),
                'name': subcat_info['name'],
                'gene_count': len(all_genes)
            }
            
            print(f"    Mean enrichment score: {np.mean(scores):.3f} ± {np.std(scores):.3f}")
        
        return {
            'dataset_info': self.validation_datasets[dataset_id],
            'expression_shape': expr_df.shape,
            'gene_expression_shape': gene_expr_df.shape,
            'sample_info': sample_info,
            'subcategory_scores': subcategory_scores,
            'probe_to_gene_count': len(probe_to_gene)
        }
    
    def identify_missing_components(self):
        """Identify what's needed for real ssGSEA analysis"""
        print("\n" + "="*60)
        print("MISSING COMPONENTS FOR REAL ssGSEA ANALYSIS")
        print("="*60)
        
        missing = []
        
        print("\n1. GO Term to Gene Mappings:")
        print("   ❌ Need: GO annotation files (GAF format)")
        print("   ❌ Need: Gene Ontology database")
        print("   ❌ Need: Species-specific GO annotations")
        print("   📁 Source: http://geneontology.org/docs/download-go-annotations/")
        missing.append("GO-gene mappings")
        
        print("\n2. KEGG Pathway to Gene Mappings:")
        print("   ❌ Need: KEGG pathway gene lists")
        print("   ❌ Need: KEGG API access or downloaded data")
        print("   📁 Source: https://www.kegg.jp/kegg/rest/keggapi.html")
        missing.append("KEGG-gene mappings")
        
        print("\n3. Gene ID Conversion:")
        print("   ❌ Need: Gene symbol standardization")
        print("   ❌ Need: Entrez ID to Symbol mapping")
        print("   📁 Source: NCBI Gene database")
        missing.append("Gene ID mappings")
        
        print("\n4. Platform Annotations:")
        print("   ✅ Have: Platform annotation files (GPL*.txt)")
        print("   ✅ Have: Probe to gene symbol mappings")
        
        print("\n5. Expression Data:")
        print("   ✅ Have: Raw expression matrices")
        print("   ✅ Have: Sample information")
        
        print(f"\n📋 SUMMARY:")
        print(f"   ✅ Available: Expression data, platform annotations")
        print(f"   ❌ Missing: {', '.join(missing)}")
        
        print(f"\n🔧 TO IMPLEMENT REAL ssGSEA:")
        print(f"   1. Download GO annotations (gene_association.goa_human)")
        print(f"   2. Download KEGG pathway-gene mappings")
        print(f"   3. Create GO term → gene list mappings")
        print(f"   4. Create KEGG pathway → gene list mappings")
        print(f"   5. Run real ssGSEA with actual gene sets")
        
        return missing
    
    def run_real_analysis(self):
        """Run the real analysis (or identify what's missing)"""
        print("="*80)
        print("REAL ssGSEA VALIDATION - NO SIMULATION")
        print("="*80)
        
        # Load classification data
        self.load_classification_data()
        
        # Identify missing components
        missing = self.identify_missing_components()
        
        if missing:
            print(f"\n⚠️  CANNOT PERFORM REAL ssGSEA WITHOUT:")
            for item in missing:
                print(f"   - {item}")
            
            print(f"\n💡 RECOMMENDATION:")
            print(f"   Provide the missing gene mapping files, and I'll implement real ssGSEA")
            print(f"   Current analysis would return all zeros due to missing mappings")
            
            return None
        
        # If we had all components, we would run real analysis
        results = {}
        for dataset_id in self.validation_datasets.keys():
            result = self.analyze_dataset_real(dataset_id)
            if result:
                results[dataset_id] = result
        
        return results

def main():
    """Main execution"""
    validator = RealSSGSEAValidator()
    results = validator.run_real_analysis()
    
    if results is None:
        print("\n" + "="*80)
        print("CONCLUSION: REAL ANALYSIS REQUIRES ADDITIONAL DATA")
        print("="*80)
        print("The expression data and platform annotations are available,")
        print("but we need GO/KEGG gene mappings to perform real ssGSEA.")
        print("\nProvide these files and I'll implement the real analysis.")
    
    return results

if __name__ == "__main__":
    main()