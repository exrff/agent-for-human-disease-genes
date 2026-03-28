"""
数据预处理模块

处理GO本体和KEGG通路数据的解析、清洗和过滤。
"""

from .go_parser import GOParser, GOTerm
from .kegg_parser import KEGGParser, KEGGPathway

__all__ = [
    'GOParser',
    'GOTerm',
    'KEGGParser',
    'KEGGPathway'
]