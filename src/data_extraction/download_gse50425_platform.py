#!/usr/bin/env python3
"""
下载GSE50425的平台注释文件
"""

import requests
import gzip
import os
from urllib.parse import urljoin

def download_gse50425_platform():
    """下载GSE50425的平台注释"""
    
    print("Downloading GSE50425 platform annotation...")
    
    # GSE50425使用的平台需要从GEO数据库查询
    # 根据探针格式ILMN_xxx，这应该是Illumina平台
    
    # 常见的Illumina平台ID
    possible_platforms = [
        'GPL10558',  # Illumina HumanHT-12 V4.0 expression beadchip
        'GPL6947',   # Illumina HumanHT-12 V3.0 expression beadchip  
        'GPL6883',   # Illumina HumanRef-8 v3.0 expression beadchip
        'GPL6102',   # Illumina human-6 v2.0 expression beadchip
    ]
    
    output_dir = "data/validation_datasets/GSE50425"
    
    for platform_id in possible_platforms:
        print(f"\nTrying platform {platform_id}...")
        
        # 构建下载URL
        base_url = "https://ftp.ncbi.nlm.nih.gov/geo/platforms/"
        platform_dir = platform_id[:5] + "nnn"  # GPL10558 -> GPL10nnn
        file_url = f"{base_url}{platform_dir}/{platform_id}/annot/{platform_id}.annot.gz"
        
        try:
            print(f"  Downloading from: {file_url}")
            response = requests.get(file_url, timeout=30)
            
            if response.status_code == 200:
                # 保存文件
                output_file = os.path.join(output_dir, f"{platform_id}.annot.gz")
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                
                print(f"  ✅ Downloaded: {output_file}")
                
                # 解压并检查内容
                try:
                    with gzip.open(output_file, 'rt', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                    
                    print(f"  File contains {len(lines)} lines")
                    
                    # 查找ILMN_1343291探针
                    found_probe = False
                    for line in lines[:1000]:  # 检查前1000行
                        if 'ILMN_1343291' in line:
                            print(f"  ✅ Found target probe ILMN_1343291")
                            print(f"  Line: {line.strip()}")
                            found_probe = True
                            break
                    
                    if found_probe:
                        print(f"  ✅ This is the correct platform file!")
                        return platform_id, output_file
                    else:
                        print(f"  ❌ Target probe not found in this platform")
                        os.remove(output_file)
                        
                except Exception as e:
                    print(f"  ❌ Error reading file: {e}")
                    if os.path.exists(output_file):
                        os.remove(output_file)
            else:
                print(f"  ❌ Download failed: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Error downloading: {e}")
    
    # 如果所有平台都失败，尝试直接从GSE50425页面获取平台信息
    print(f"\nTrying to get platform info from GSE50425 page...")
    
    try:
        gse_url = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE50425&targ=self&form=text&view=brief"
        response = requests.get(gse_url, timeout=30)
        
        if response.status_code == 200:
            content = response.text
            
            # 查找平台信息
            lines = content.split('\n')
            for line in lines:
                if 'Platform_geo_accession' in line or 'Platform:' in line:
                    print(f"  Platform info: {line.strip()}")
                    
                    # 提取平台ID
                    if 'GPL' in line:
                        import re
                        platform_match = re.search(r'GPL\d+', line)
                        if platform_match:
                            platform_id = platform_match.group()
                            print(f"  Found platform ID: {platform_id}")
                            
                            # 尝试下载这个平台
                            return download_specific_platform(platform_id, output_dir)
        
    except Exception as e:
        print(f"  Error getting GSE info: {e}")
    
    print(f"\n❌ Could not download platform annotation for GSE50425")
    return None, None

def download_specific_platform(platform_id, output_dir):
    """下载特定平台的注释文件"""
    
    print(f"\nDownloading specific platform {platform_id}...")
    
    # 构建下载URL
    base_url = "https://ftp.ncbi.nlm.nih.gov/geo/platforms/"
    platform_dir = platform_id[:5] + "nnn"  # GPL10558 -> GPL10nnn
    
    # 尝试不同的文件格式
    possible_files = [
        f"{platform_id}.annot.gz",
        f"{platform_id}.txt",
        f"{platform_id}_annot.txt.gz"
    ]
    
    for filename in possible_files:
        file_url = f"{base_url}{platform_dir}/{platform_id}/annot/{filename}"
        
        try:
            print(f"  Trying: {file_url}")
            response = requests.get(file_url, timeout=30)
            
            if response.status_code == 200:
                output_file = os.path.join(output_dir, filename)
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                
                print(f"  ✅ Downloaded: {output_file}")
                return platform_id, output_file
                
        except Exception as e:
            print(f"  Error: {e}")
    
    return None, None

if __name__ == "__main__":
    platform_id, platform_file = download_gse50425_platform()
    
    if platform_file:
        print(f"\n✅ Successfully downloaded platform annotation!")
        print(f"Platform: {platform_id}")
        print(f"File: {platform_file}")
    else:
        print(f"\n❌ Failed to download platform annotation")
        print(f"GSE50425 analysis will use probe IDs instead of gene symbols")