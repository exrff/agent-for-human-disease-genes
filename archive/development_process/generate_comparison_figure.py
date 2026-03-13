import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# Set global aesthetics
sns.set_style("ticks")
sns.set_context("talk") # Larger fonts
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']

# 1. Load Data
try:
    df_z = pd.read_csv('figure_2b_zscore_data.csv', index_col=0)
    df_groups = pd.read_csv('figure_2b_sample_groups.csv', index_col=0)
except Exception as e:
    print(f"Error loading files: {e}")
    # Fallback to simulated data if files fail to load (for demonstration/robustness)
    # But we should rely on the uploaded files as per user request.
    # We will assume they load correctly for now.
    pass

# 2. Check and Fix Order
# Desired order: Intact -> Acute -> Day 3 -> Day 7
# Extract group info
# Assume df_groups has columns 'Group' and 'Color'
# We need to sort df_z columns based on this order

# Define order map
order_map = {"Intact": 0, "Acute": 1, "Day 3": 2, "Day 7": 3}

# Add a rank column to df_groups for sorting
df_groups['Rank'] = df_groups['Group'].map(order_map)
df_groups_sorted = df_groups.sort_values('Rank')

# Reorder Z-score dataframe columns
sorted_columns = df_groups_sorted.index.tolist()
# Ensure all columns exist
sorted_columns = [c for c in sorted_columns if c in df_z.columns]
df_z_sorted = df_z[sorted_columns]

# 3. Prepare Colors
# Create a dictionary for column colors
# Assuming 'Color' column exists in df_groups. 
# Based on user description: Intact=Gray, Acute=Red, Day3=Blue, Day7=Green
# Let's verify or enforce this color scheme
group_colors = {
    "Intact": "#808080",   # DarkGray
    "Acute": "#DC143C",    # Crimson
    "Day 3": "#1E90FF",    # DodgerBlue
    "Day 7": "#228B22"     # ForestGreen
}

# Create color list for columns
col_colors = df_groups_sorted['Group'].map(group_colors)

# 4. Plotting Figure 2B (Heatmap)
plt.figure(figsize=(12, 8))

# Draw Clustermap
# row_cluster=False to keep System A-E order (or True if we want to see system clustering)
# col_cluster=False is CRITICAL for time series
g = sns.clustermap(df_z_sorted,
                   col_cluster=False, 
                   row_cluster=False, 
                   col_colors=col_colors,
                   cmap="RdBu_r", 
                   center=0,
                   vmin=-1.5, vmax=1.5, # Force contrast
                   linewidths=0.5, linecolor='white',
                   figsize=(14, 8),
                   cbar_kws={'label': 'Z-Score'})

# 5. Customize Labels
# Remove default X-axis labels (too crowded)
g.ax_heatmap.set_xticklabels([])
g.ax_heatmap.set_xlabel("")
g.ax_heatmap.set_ylabel("")

# Add Group Labels manually
# Calculate positions for labels
# We need to know how many samples in each group to center the label
group_counts = df_groups_sorted['Group'].value_counts(sort=False).reindex(["Intact", "Acute", "Day 3", "Day 7"])
# Reindex ensures we count in the correct order: Intact, Acute, Day3, Day7
# However, value_counts might not preserve the order we want to iterate.
# Let's iterate through the sorted dataframe to be sure.
current_pos = 0
for group_name in ["Intact", "Acute", "Day 3", "Day 7"]:
    count = len(df_groups_sorted[df_groups_sorted['Group'] == group_name])
    if count > 0:
        center = current_pos + count / 2
        g.ax_heatmap.text(center, df_z_sorted.shape[0] + 0.5, 
                          f"{group_name}\n(n={count})", 
                          ha='center', va='top', fontsize=14, fontweight='bold', rotation=0)
        # Draw vertical lines separator
        if current_pos > 0:
             g.ax_heatmap.axvline(x=current_pos, color='white', linewidth=3)
        current_pos += count

# Adjust layout
plt.suptitle("Figure 2B: Temporal Activation Heatmap (High Contrast)", y=1.02, fontsize=18, fontweight='bold')

# Save
plt.savefig("Figure_2B_Heatmap_Final.png", dpi=300, bbox_inches='tight')
plt.close()

# Also generate a simple legend for the top bar colors manually if needed, 
# but the text labels at bottom serve this purpose well.
print("Figure 2B generated successfully.")