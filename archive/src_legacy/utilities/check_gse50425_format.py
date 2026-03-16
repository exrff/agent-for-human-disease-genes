#!/usr/bin/env python3
"""
检查GSE50425数据格式
"""

import gzip
import pandas as pd

def check_gse50425_format():
    """检查GSE50425数据格式"""
    
    data_path = "data/validation_datasets/GSE50425/GSE50425_series_matrix.txt.gz"
    
    print("Checking GSE50425 data format...")
    
    try:
        with gzip.open(data_path, 'rt', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        print(f"Total lines: {len(lines)}")
        
        # 查找关键信息
        platform_info = None
        sample_info = {}
        data_start = None
        
        for i, line in enumerate(lines[:100]):  # 只检查前100行
            if line.startswith('!Platform_title'):
                platform_info = line.strip()
                print(f"Platform: {platform_info}")
            elif line.startswith('!Sample_title'):
                titles = line.strip().split('\t')[1:]
                sample_info['titles'] = [t.strip('"') for t in titles]
                print(f"Sample titles (first 3): {sample_info['titles'][:3]}")
            elif line.startswith('!Sample_geo_accession'):
                accessions = line.strip().split('\t')[1:]
                sample_info['accessions'] = [a.strip('"') for a in accessions]
                print(f"Sample accessions (first 3): {sample_info['accessions'][:3]}")
            elif line.startswith('!series_matrix_table_begin'):
                data_start = i + 1
                print(f"Data starts at line: {data_start}")
                break
        
        if data_start:
            # 检查数据表头和前几行
            data_lines = []
            for line in lines[data_start:data_start+10]:
                if line.startswith('!series_matrix_table_end'):
                    break
                data_lines.append(line.strip().split('\t'))
            
            if data_lines:
                header = [col.strip('"') for col in data_lines[0]]
                print(f"Data header: {header}")
                
                if len(data_lines) > 1:
                    first_row = [cell.strip('"') for cell in data_lines[1]]
                    print(f"First data row: {first_row}")
                    
                    # 检查探针ID格式
                    probe_id = first_row[0] if first_row else ""
                    print(f"Sample probe ID: {probe_id}")
                    
                    # 检查是否是Affymetrix格式
                    if "_at" in probe_id or "_s_at" in probe_id:
                        print("  → Affymetrix probe format detected")
                    elif probe_id.startswith("ILMN_"):
                        print("  → Illumina probe format detected")
                    elif probe_id.isdigit():
                        print("  → Numeric probe ID format")
                    else:
                        print(f"  → Unknown probe format: {probe_id}")
        
        # 查找平台信息
        platform_id = None
        for line in lines[:50]:
            if line.startswith('!Platform_geo_accession'):
                platform_id = line.strip().split('\t')[1].strip('"')
                print(f"Platform ID: {platform_id}")
                break
        
        return platform_id, sample_info
        
    except Exception as e:
        print(f"Error: {e}")
        return None, None

if __name__ == "__main__":
    platform_id, sample_info = check_gse50425_format()