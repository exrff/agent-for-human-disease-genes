import sys, logging
sys.path.insert(0, '.')
logging.basicConfig(level=logging.INFO)
from src.agent.geo_validator import validate_and_report

for gse in ['GSE2034', 'GSE105756', 'GSE103195']:
    r = validate_and_report(gse)
    print(f"{gse}: valid={r['valid']} | {r['reason']} | {r['gdstype'][:45]} | n_samples={r['n_samples']}")
    print()
