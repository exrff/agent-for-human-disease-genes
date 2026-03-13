# GSE2034 Breast Cancer Patient Heterogeneity Analysis Report

## Summary
- **Dataset**: GSE2034 Breast Cancer
- **Total patients**: 286
- **Optimal clusters identified**: 2
- **Analysis date**: 2026-01-05 20:06:53

## System Activation Variability

### System A
- **Mean activation**: 0.2798
- **Standard deviation**: 0.0061
- **Coefficient of variation**: 0.0220
- **Range**: [0.2636, 0.2969]
- **Dynamic range**: 0.0334

### System B
- **Mean activation**: 0.2846
- **Standard deviation**: 0.0045
- **Coefficient of variation**: 0.0159
- **Range**: [0.2722, 0.2968]
- **Dynamic range**: 0.0246

### System C
- **Mean activation**: 0.3454
- **Standard deviation**: 0.0047
- **Coefficient of variation**: 0.0136
- **Range**: [0.3330, 0.3592]
- **Dynamic range**: 0.0262

### System D
- **Mean activation**: 0.3065
- **Standard deviation**: 0.0043
- **Coefficient of variation**: 0.0142
- **Range**: [0.2949, 0.3180]
- **Dynamic range**: 0.0232

### System E
- **Mean activation**: 0.2822
- **Standard deviation**: 0.0049
- **Coefficient of variation**: 0.0174
- **Range**: [0.2687, 0.2955]
- **Dynamic range**: 0.0268

## System Correlation Matrix

        A       B       C       D       E
A  1.0000  0.9842  0.9063  0.9890  0.9831
B  0.9842  1.0000  0.8375  0.9993  0.9998
C  0.9063  0.8375  1.0000  0.8476  0.8344
D  0.9890  0.9993  0.8476  1.0000  0.9991
E  0.9831  0.9998  0.8344  0.9991  1.0000

## Key Findings

1. **High Patient Heterogeneity**: Coefficient of variation ranges from 0.014 to 0.022

2. **Optimal Clustering**: 2 distinct patient subgroups identified based on system activation patterns

3. **System Correlations**: 
   - Strongest positive correlation: 1.000
   - Strongest negative correlation: 0.834

## Clinical Implications

The high heterogeneity in system activation patterns suggests:
- Potential molecular subtypes within the breast cancer cohort
- Different therapeutic targets for different patient subgroups
- Need for personalized treatment approaches

## Files Generated
- `GSE2034_sample_info_enhanced.csv` - Enhanced sample information with clinical features
- `GSE2034_cluster_analysis.csv` - Clustering results and system scores
- `GSE2034_heterogeneity_analysis.png` - Comprehensive visualization
- `GSE2034_subcategory_heatmap.png` - Subcategory activation heatmap
