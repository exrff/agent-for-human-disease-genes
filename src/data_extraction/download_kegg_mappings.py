#!/usr/bin/env python3
"""
Download and process KEGG pathway mappings for real ssGSEA analysis
"""

import urllib.request
import json
import os
import time
from collections import defaultdict

def download_kegg_pathways():
    """Download KEGG pathway information"""
    
    print("Downloading KEGG pathway mappings...")
    
    # Create directory
    os.makedirs('data/kegg_mappings', exist_ok=True)
    
    # KEGG REST API endpoints
    base_url = "https://rest.kegg.jp"
    
    try:
        # Get list of human pathways
        print("  Getting human pathway list...")
        pathway_list_url = f"{base_url}/list/pathway/hsa"
        
        with urllib.request.urlopen(pathway_list_url) as response:
            pathway_data = response.read().decode('utf-8')
        
        pathways = []
        for line in pathway_data.strip().split('\n'):
            if line:
                parts = line.split('\t')
                if len(parts) >= 2:
                    pathway_id = parts[0].replace('path:', '')
                    pathway_name = parts[1]
                    pathways.append((pathway_id, pathway_name))
        
        print(f"    Found {len(pathways)} human pathways")
        
        # Download gene mappings for each pathway
        pathway_to_genes = {}
        
        for i, (pathway_id, pathway_name) in enumerate(pathways):
            if i % 10 == 0:
                print(f"    Processing pathway {i+1}/{len(pathways)}: {pathway_id}")
            
            try:
                # Get genes for this pathway
                genes_url = f"{base_url}/get/{pathway_id}"
                
                with urllib.request.urlopen(genes_url) as response:
                    pathway_info = response.read().decode('utf-8')
                
                # Parse gene information
                genes = []
                in_gene_section = False
                
                for line in pathway_info.split('\n'):
                    if line.startswith('GENE'):
                        in_gene_section = True
                        # Parse first gene line
                        gene_part = line[12:].strip()  # Skip 'GENE        '
                        if gene_part:
                            gene_info = gene_part.split(';')[0].strip()
                            if ' ' in gene_info:
                                gene_symbol = gene_info.split(' ')[1]
                                genes.append(gene_symbol)
                    elif in_gene_section and line.startswith('            '):
                        # Continuation of gene list
                        gene_part = line[12:].strip()
                        if gene_part:
                            gene_info = gene_part.split(';')[0].strip()
                            if ' ' in gene_info:
                                gene_symbol = gene_info.split(' ')[1]
                                genes.append(gene_symbol)
                    elif in_gene_section and not line.startswith('            '):
                        # End of gene section
                        break
                
                if genes:
                    pathway_to_genes[f"KEGG:{pathway_id}"] = {
                        'name': pathway_name,
                        'genes': genes
                    }
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                print(f"      Warning: Could not get genes for {pathway_id}: {e}")
                continue
        
        print(f"  ✅ Downloaded mappings for {len(pathway_to_genes)} pathways")
        
        # Save the mapping
        mapping_file = 'data/kegg_mappings/kegg_to_genes.json'
        with open(mapping_file, 'w') as f:
            json.dump(pathway_to_genes, f, indent=2)
        
        print(f"  ✅ Saved KEGG-gene mapping to {mapping_file}")
        
        return pathway_to_genes
        
    except Exception as e:
        print(f"❌ Error downloading KEGG pathways: {e}")
        return None

def main():
    """Main function"""
    print("="*60)
    print("DOWNLOADING KEGG PATHWAY MAPPINGS FOR REAL ssGSEA")
    print("="*60)
    
    # Download KEGG mappings
    kegg_mapping = download_kegg_pathways()
    
    if kegg_mapping:
        print(f"\n✅ SUCCESS: KEGG mappings ready for real ssGSEA")
        print(f"   - {len(kegg_mapping)} KEGG pathways mapped to genes")
        print(f"   - Mapping saved to data/kegg_mappings/kegg_to_genes.json")
    else:
        print(f"\n❌ FAILED: Could not download KEGG mappings")

if __name__ == "__main__":
    main()