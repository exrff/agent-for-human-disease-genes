#!/usr/bin/env python3
"""
Download and process GO annotations for real ssGSEA analysis
"""

import urllib.request
import gzip
import os
import pandas as pd
from collections import defaultdict

def download_go_annotations():
    """Download GO annotations from official sources"""
    
    print("Downloading GO annotations...")
    
    # Create directory
    os.makedirs('data/go_annotations', exist_ok=True)
    
    # URLs for GO annotation files
    urls = {
        'goa_human': 'http://geneontology.org/gene-associations/goa_human.gaf.gz',
        'gene2go': 'https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene2go.gz',
        'gene_info': 'https://ftp.ncbi.nlm.nih.gov/gene/DATA/GENE_INFO/Mammalia/Homo_sapiens.gene_info.gz'
    }
    
    for name, url in urls.items():
        output_file = f'data/go_annotations/{name}.gz'
        if not os.path.exists(output_file):
            print(f"  Downloading {name}...")
            try:
                urllib.request.urlretrieve(url, output_file)
                print(f"    ✅ Downloaded {name}")
            except Exception as e:
                print(f"    ❌ Failed to download {name}: {e}")
        else:
            print(f"  ✅ {name} already exists")
    
    return True

def process_go_annotations():
    """Process GO annotations to create GO term -> gene mappings"""
    
    print("\nProcessing GO annotations...")
    
    # Check if files exist
    goa_file = 'data/go_annotations/goa_human.gz'
    if not os.path.exists(goa_file):
        print(f"❌ GO annotation file not found: {goa_file}")
        return None
    
    go_to_genes = defaultdict(set)
    
    try:
        print("  Reading GOA human annotations...")
        with gzip.open(goa_file, 'rt') as f:
            for line_num, line in enumerate(f):
                if line.startswith('!'):  # Skip comments
                    continue
                
                parts = line.strip().split('\t')
                if len(parts) < 5:
                    continue
                
                # GAF format: DB, DB_Object_ID, DB_Object_Symbol, Qualifier, GO_ID, ...
                gene_symbol = parts[2]
                go_id = parts[4]
                
                if go_id.startswith('GO:') and gene_symbol:
                    go_to_genes[go_id].add(gene_symbol)
                
                if line_num % 100000 == 0:
                    print(f"    Processed {line_num} lines...")
        
        print(f"  ✅ Processed GO annotations: {len(go_to_genes)} GO terms")
        
        # Save the mapping
        mapping_file = 'data/go_annotations/go_to_genes.json'
        import json
        
        # Convert sets to lists for JSON serialization
        go_to_genes_json = {go_id: list(genes) for go_id, genes in go_to_genes.items()}
        
        with open(mapping_file, 'w') as f:
            json.dump(go_to_genes_json, f, indent=2)
        
        print(f"  ✅ Saved GO-gene mapping to {mapping_file}")
        
        return go_to_genes
        
    except Exception as e:
        print(f"❌ Error processing GO annotations: {e}")
        return None

def main():
    """Main function"""
    print("="*60)
    print("DOWNLOADING GO ANNOTATIONS FOR REAL ssGSEA")
    print("="*60)
    
    # Download files
    success = download_go_annotations()
    
    if success:
        # Process annotations
        go_mapping = process_go_annotations()
        
        if go_mapping:
            print(f"\n✅ SUCCESS: GO annotations ready for real ssGSEA")
            print(f"   - {len(go_mapping)} GO terms mapped to genes")
            print(f"   - Mapping saved to data/go_annotations/go_to_genes.json")
        else:
            print(f"\n❌ FAILED: Could not process GO annotations")
    else:
        print(f"\n❌ FAILED: Could not download GO annotations")

if __name__ == "__main__":
    main()