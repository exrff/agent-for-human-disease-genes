"""
V7 Classification Script - Mentor Feedback Implementation
==========================================================
Key Changes:
1. System E (Reproductive): Strict - Only true reproductive processes
2. System A (Self-healing): Expanded - Include cell proliferation, development
3. Priority: E > B > D > A > C (A moved before C)
"""

import re
import pandas as pd
import networkx as nx

# Files
go_file_path = '数据/go-basic.txt'
kegg_file_path = '数据/br_br08901.txt'

# =============================================================================
# PART 1: KEGG V7 Classification
# =============================================================================

kegg_entries = []
current_class_A = ""
current_class_B = ""

def classify_kegg_v7(class_a, class_b, name):
    """
    V7 Logic:
    - System E: STRICT (only true reproduction)
    - System A: EXPANDED (repair + proliferation + development)
    """
    text = (str(class_a) + " " + str(class_b) + " " + str(name)).lower()
    systems = set()
    
    # --- System E: Reproductive (STRICT) ---
    if "reproductive system" in class_b.lower():
        systems.add("System E: Reproductive")
    # Only meiosis and gamete-related processes
    if re.search(r'\b(meiosis|meiotic|oocyte|spermatogenesis|gametogenesis)\b', name.lower()):
        systems.add("System E: Reproductive")
    
    # --- System A: Self-healing (EXPANDED) ---
    # Original repair/aging/apoptosis
    if "repair" in class_b.lower() or "aging" in class_b.lower():
        systems.add("System A: Self-healing")
    if "apoptosis" in name.lower():
        systems.add("System A: Self-healing")
    
    # NEW: Cell proliferation and development (moved from E)
    if re.search(r'\b(cell cycle|cell growth|proliferation|replication)\b', name.lower()):
        # Exclude if it's specifically meiotic
        if "meiotic" not in name.lower():
            systems.add("System A: Self-healing")
    
    # Development and morphogenesis
    if re.search(r'\b(development|morphogenesis|differentiation|regeneration)\b', name.lower()):
        # Exclude reproductive development
        if not re.search(r'\b(oocyte|sperm|gamete|gonad)\b', name.lower()):
            systems.add("System A: Self-healing")
    
    # Muscle and cardiac (structural maintenance)
    if re.search(r'\b(muscle|cardiac|cardiomyopathy|myocyte)\b', name.lower()):
        systems.add("System A: Self-healing")
    
    # --- System B: Immune ---
    if "immune system" in class_b.lower():
        systems.add("System B: Immune")
    if "drug resistance" in class_b.lower():
        systems.add("System B: Immune")
    if "infectious" in class_a.lower() or "infection" in name.lower():
        systems.add("System B: Immune")
    if re.search(r'\b(phagosome|lysosome)\b', name.lower()):
        systems.add("System B: Immune")
    
    # --- System D: Regulation (Neuro/Endo) ---
    if "nervous system" in class_b.lower():
        systems.add("System D: Regulation (Neuro)")
    if "endocrine system" in class_b.lower():
        systems.add("System D: Regulation (Endo)")
    if "sensory system" in class_b.lower():
        systems.add("System D: Regulation (Sensory)")
    if re.search(r'\b(synaptic|neuroactive)\b', name.lower()):
        systems.add("System D: Regulation (Neuro)")
    
    # --- System C: Metabolism ---
    if "metabolism" in class_a.lower():
        systems.add("System C: Energy/Metabolism")
    if "transport" in name.lower() and re.search(r'\b(abc|phospho|ion)\b', name.lower()):
        systems.add("System C: Energy/Metabolism")
    
    # --- Priority: E > B > D > A > C ---
    primary = "Unclassified"
    if "System E: Reproductive" in systems:
        primary = "System E: Reproductive"
    elif "System B: Immune" in systems:
        primary = "System B: Immune"
    elif "System D: Regulation (Neuro)" in systems:
        primary = "System D: Regulation (Neuro)"
    elif "System D: Regulation (Endo)" in systems:
        primary = "System D: Regulation (Endo)"
    elif "System A: Self-healing" in systems:
        primary = "System A: Self-healing"
    elif "System C: Energy/Metabolism" in systems:
        primary = "System C: Energy/Metabolism"
    elif "System D: Regulation (Sensory)" in systems:
        primary = "System D: Regulation (Sensory)"
    elif len(systems) == 0:
        # 兜底逻辑：如果没有匹配任何系统，归为通用生物过程
        primary = "General Biological Process"
    
    return primary, list(systems)


# Parse KEGG file
print("Parsing KEGG pathways...")
with open(kegg_file_path, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line.startswith('A'):
            current_class_A = line[1:].strip()
        elif line.startswith('B'):
            current_class_B = line[1:].strip()
        elif line.startswith('C'):
            parts = line.split(maxsplit=2)
            if len(parts) >= 3:
                entry_id = parts[1]
                name = parts[2]
                
                prim, all_sys = classify_kegg_v7(current_class_A, current_class_B, name)
                
                kegg_entries.append({
                    'ID': f"KEGG:{entry_id}",
                    'Name': name,
                    'Definition': f"{current_class_A} > {current_class_B}",
                    'Source': 'KEGG',
                    'Primary_System': prim,
                    'All_Systems': "; ".join(all_sys)
                })

print(f"KEGG entries processed: {len(kegg_entries)}")

# =============================================================================
# PART 2: GO V7 Classification
# =============================================================================

print("\nBuilding GO graph...")

# 1. Build Graph (Parent -> Child)
go_graph = nx.DiGraph()
term_data = {}
current_id = ""
current_props = {}

with open(go_file_path, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line == '[Term]':
            if current_id:
                term_data[current_id] = current_props
            current_id = ""
            current_props = {'is_a': []}
        elif line.startswith('id: '):
            current_id = line[4:]
        elif line.startswith('name: '):
            current_props['name'] = line[6:]
        elif line.startswith('namespace: '):
            current_props['namespace'] = line[11:]
        elif line.startswith('def: '):
            current_props['def'] = line[5:]
        elif line.startswith('is_a: '):
            parent_id = line[6:].split(' !')[0].strip()
            current_props['is_a'].append(parent_id)

if current_id:
    term_data[current_id] = current_props

# Build graph
for node, props in term_data.items():
    go_graph.add_node(node, **props)
    for parent in props.get('is_a', []):
        go_graph.add_edge(parent, node)

print(f"GO terms loaded: {len(term_data)}")

def get_ancestors(node_id):
    """Get all ancestor nodes in GO DAG"""
    if node_id not in go_graph:
        return set()
    try:
        return nx.ancestors(go_graph, node_id)
    except:
        return set()


def classify_go_v7(node_id, props):
    """
    V7 Logic for GO terms:
    - System E: STRICT (only true reproduction)
    - System A: EXPANDED (repair + proliferation + development)
    """
    name_str = str(props.get('name', '')).lower()
    
    # --- CLEANING: Remove Obsolete ---
    if "obsolete" in name_str:
        return "Excluded (Obsolete)", []
    
    if props.get('namespace') != 'biological_process':
        return "Excluded (Non-BP)", []
    
    ancestors = get_ancestors(node_id)
    ancestor_names = set()
    for anc in ancestors:
        if anc in term_data:
            ancestor_names.add(term_data[anc].get('name', '').lower())
    
    self_text = (name_str + " " + str(props.get('def', ''))).lower()
    systems_found = set()
    
    # --- E (Reproductive) - STRICT ---
    # Only true reproductive processes
    if any('reproductive process' in name for name in ancestor_names):
        systems_found.add("System E: Reproductive")
    if re.search(r'\b(meiosis|meiotic|gamet|sperm|oocyte|fertiliz|pregnan|embryo development|germ cell|mating|insemination|ovulation|placenta|parturition)\b', self_text):
        # Exclude general development terms
        if not re.search(r'\b(cell cycle|mitosis|mitotic|proliferation)\b', self_text):
            systems_found.add("System E: Reproductive")
    
    # --- A (Self-healing) - EXPANDED ---
    # Original wound healing
    if any('response to wounding' in name for name in ancestor_names) or \
       any('wound healing' in name for name in ancestor_names):
        systems_found.add("System A: Self-healing")
    
    # Expanded: morphogenesis, development, proliferation
    if re.search(r'\b(angiogene|coagulat|regeneration|hemostasis|clot|extracellular matrix|collagen|ossification|vasculature|stem cell)\b', self_text):
        systems_found.add("System A: Self-healing")
    
    # NEW: Morphogenesis and development (moved from E)
    if re.search(r'\b(morphogenesis|organogenesis|tissue development|organ development|anatomical structure development)\b', self_text):
        # Exclude reproductive-specific development
        if not re.search(r'\b(gonad|oocyte|sperm|gamete|reproductive)\b', self_text):
            systems_found.add("System A: Self-healing")
    
    # NEW: Cell proliferation and cycle (moved from E)
    if re.search(r'\b(cell cycle|mitosis|mitotic|cell division|cell proliferation|cell growth)\b', self_text):
        # Exclude meiosis
        if "meiosis" not in self_text and "meiotic" not in self_text:
            systems_found.add("System A: Self-healing")
    
    # Muscle and cardiac development
    if re.search(r'\b(muscle|cardiac|cardiocyte|myoblast|myocyte|heart development)\b', self_text):
        systems_found.add("System A: Self-healing")
    
    # Bone and cartilage
    if re.search(r'\b(osteoblast|chondrocyte|bone|cartilage|skeletal)\b', self_text):
        systems_found.add("System A: Self-healing")
    
    # Growth factors
    if re.search(r'\b(growth factor|tgf|fgf|egf|vegf|pdgf)\b', self_text):
        systems_found.add("System A: Self-healing")
    
    # --- B (Immune) - EXPANDED ---
    if any('immune system process' in name for name in ancestor_names):
        systems_found.add("System B: Immune")
    if re.search(r'\b(defense|leukocyte|cytokine|inflammat|b cell|t cell|lymph|phagocyt|chemotaxis|antigen|interferon|chemokine)\b', self_text):
        systems_found.add("System B: Immune")
    if re.search(r'\b(bacteri|vir[au]l|fungal|parasit|host|symbiont|killing of cells|pathogen)\b', self_text):
        systems_found.add("System B: Immune")
    
    # --- D (Neuro/Endo) ---
    if any('nervous system process' in name for name in ancestor_names):
        systems_found.add("System D: Regulation (Neuro)")
    if re.search(r'\b(neuro|synap|axon|brain|behavior|sensory|perception|action potential|ion channel)\b', self_text):
        systems_found.add("System D: Regulation (Neuro)")
    if re.search(r'\b(dopamine|serotonin|catecholamine|acetylcholine|neuropeptide|glial|memory|learning|locomotion)\b', self_text):
        systems_found.add("System D: Regulation (Neuro)")
    
    if re.search(r'\b(hormone|endocrine|circadian|adrenal|pituitary|thyroid|insulin|glucagon|corticosteroid|estrogen|androgen)\b', self_text):
        systems_found.add("System D: Regulation (Endo)")
    
    # --- C (Metabolism) - EXPANDED ---
    if any('metabolic process' in name for name in ancestor_names):
        systems_found.add("System C: Energy/Metabolism")
    if re.search(r'\b(metabol|biosynthe|catabol|respiration|fermentation|glycoly|gluconeo)\b', self_text):
        systems_found.add("System C: Energy/Metabolism")
    if re.search(r'\b(fatty acid|lipid|carbohydrate|amino acid|nucleotide|vitamin|cofactor)\b', self_text):
        systems_found.add("System C: Energy/Metabolism")
    
    # Specific Transport (Ion, Nutrient)
    if re.search(r'\b(lipid transport|glucose transport|amino acid transport|ion transport|transmembrane transport|cation transport|anion transport)\b', self_text):
        # If not specifically neuro, it's generic C
        if "System D: Regulation (Neuro)" not in systems_found:
            systems_found.add("System C: Energy/Metabolism")
    
    # --- Determine PRIMARY (Priority: E > B > D > A > C) ---
    primary = "Unclassified"
    
    if "System E: Reproductive" in systems_found:
        primary = "System E: Reproductive"
    elif "System B: Immune" in systems_found:
        primary = "System B: Immune"
    elif "System D: Regulation (Neuro)" in systems_found:
        primary = "System D: Regulation (Neuro)"
    elif "System D: Regulation (Endo)" in systems_found:
        primary = "System D: Regulation (Endo)"
    elif "System A: Self-healing" in systems_found:
        primary = "System A: Self-healing"
    elif "System C: Energy/Metabolism" in systems_found:
        primary = "System C: Energy/Metabolism"
    elif len(systems_found) == 0 and ("regulation" in self_text or "signaling" in self_text):
        primary = "General Regulation (Unmapped)"
    elif len(systems_found) == 0:
        primary = "General Biological Process"
    
    return primary, list(systems_found)


# Apply classification
print("\nClassifying GO terms...")
go_results = []
for node, props in term_data.items():
    prim, all_sys = classify_go_v7(node, props)
    if prim != "Excluded (Non-BP)" and prim != "Excluded (Obsolete)":
        go_results.append({
            'ID': node,
            'Name': props.get('name'),
            'Definition': props.get('def'),
            'Source': 'GO',
            'Primary_System': prim,
            'All_Systems': "; ".join(all_sys)
        })

print(f"GO terms classified: {len(go_results)}")

# =============================================================================
# PART 3: Combine and Save
# =============================================================================

df_kegg_v7 = pd.DataFrame(kegg_entries)
df_go_v7 = pd.DataFrame(go_results)
df_final_v7 = pd.concat([df_kegg_v7, df_go_v7], ignore_index=True)

# Statistics
print("\n" + "="*60)
print("V7 Classification Results - Primary System Counts:")
print("="*60)
system_counts = df_final_v7['Primary_System'].value_counts()
print(system_counts)

# Calculate percentages
total = len(df_final_v7)
print("\n" + "="*60)
print("Percentage Distribution:")
print("="*60)
for system, count in system_counts.items():
    percentage = (count / total) * 100
    print(f"{system}: {count} ({percentage:.2f}%)")

# Save
output_file = '数据/classified_systems_v7_mentor_revised.csv'
df_final_v7.to_csv(output_file, index=False)
print(f"\n✅ V7 classification saved to: {output_file}")

# Compare with V6
print("\n" + "="*60)
print("Comparison with V6:")
print("="*60)
try:
    df_v6 = pd.read_csv('数据/classified_systems_data_driven_v6.csv')
    v6_counts = df_v6['Primary_System'].value_counts()
    
    print("\nKey Changes:")
    for system in ['System A: Self-healing', 'System E: Reproductive', 'System C: Energy/Metabolism']:
        v6_count = v6_counts.get(system, 0)
        v7_count = system_counts.get(system, 0)
        change = v7_count - v6_count
        change_pct = (change / v6_count * 100) if v6_count > 0 else 0
        print(f"{system}:")
        print(f"  V6: {v6_count} → V7: {v7_count} (Change: {change:+d}, {change_pct:+.1f}%)")
except:
    print("V6 file not found for comparison")

print("\n" + "="*60)
print("✅ V7 Classification Complete!")
print("="*60)
