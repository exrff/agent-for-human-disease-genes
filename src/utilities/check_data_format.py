#!/usr/bin/env python3
"""
Check the format of validation dataset files
"""

import gzip
import os

def check_file_format(filepath):
    """Check the format of a compressed data file"""
    print(f"\nChecking: {filepath}")
    
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return
    
    try:
        with gzip.open(filepath, 'rt', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"Total lines: {len(lines)}")
        print("First 10 lines:")
        for i, line in enumerate(lines[:10]):
            print(f"{i+1:2d}: {line.strip()}")
        
        # Look for data table start
        for i, line in enumerate(lines):
            if 'series_matrix_table_begin' in line:
                print(f"\nData table starts at line {i+1}")
                print("Data header:")
                if i+1 < len(lines):
                    print(f"{i+2:2d}: {lines[i+1].strip()}")
                if i+2 < len(lines):
                    print(f"{i+3:2d}: {lines[i+2].strip()}")
                break
        
    except Exception as e:
        print(f"Error reading file: {e}")
        
        # Try with different encodings
        for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
            try:
                print(f"Trying encoding: {encoding}")
                with gzip.open(filepath, 'rt', encoding=encoding) as f:
                    lines = f.readlines()
                print(f"Success with {encoding}! Total lines: {len(lines)}")
                print("First 5 lines:")
                for i, line in enumerate(lines[:5]):
                    print(f"{i+1:2d}: {line.strip()}")
                break
            except Exception as e2:
                print(f"Failed with {encoding}: {e2}")

# Check all three datasets
datasets = ['GSE28914', 'GSE65682', 'GSE21899']

for dataset in datasets:
    filepath = f"data/validation_datasets/{dataset}/{dataset}_series_matrix.txt.gz"
    check_file_format(filepath)