#!/usr/bin/env python3
"""
Script to analyze convergence of all results in data/results/seq folders.
Finds the number of communications when APE (position errors) and ATE (rotation errors) 
reach within 1% of their final values.
"""

import os
import glob
import pandas as pd
import numpy as np
from pathlib import Path

def analyze_convergence(file_path):
    """
    Analyze a single residual_and_ate.txt file to find convergence points.
    
    Args:
        file_path: Path to the residual_and_ate.txt file
        
    Returns:
        dict: Contains convergence information
    """
    try:
        # Read the data
        data = pd.read_csv(file_path, sep=' ', header=None, 
                          names=['communications', 'residual', 'position_errors', 'rotation_errors'])
        
        if len(data) == 0:
            return None
            
        # Get final values (last row)
        final_position_error = data['position_errors'].iloc[-1]
        final_rotation_error = data['rotation_errors'].iloc[-1]
        final_communications = data['communications'].iloc[-1]
        
        # Calculate 1% thresholds
        position_threshold = final_position_error * 1.01  # Within 1% means <= 101% of final
        rotation_threshold = final_rotation_error * 1.01
        
        # Find first time each metric reaches within 1% of final value
        position_convergence_idx = data[data['position_errors'] <= position_threshold].index
        rotation_convergence_idx = data[data['rotation_errors'] <= rotation_threshold].index
        
        position_convergence_comm = None
        rotation_convergence_comm = None
        
        if len(position_convergence_idx) > 0:
            position_convergence_comm = data.loc[position_convergence_idx[0], 'communications']
        else:
            # If never converged within 1%, use final communications
            position_convergence_comm = final_communications
            
        if len(rotation_convergence_idx) > 0:
            rotation_convergence_comm = data.loc[rotation_convergence_idx[0], 'communications']
        else:
            # If never converged within 1%, use final communications
            rotation_convergence_comm = final_communications
        
        return {
            'file_path': file_path,
            'total_communications': final_communications,
            'final_position_error': final_position_error,
            'final_rotation_error': final_rotation_error,
            'position_convergence_comm': position_convergence_comm,
            'rotation_convergence_comm': rotation_convergence_comm,
            'position_convergence_ratio': position_convergence_comm / final_communications if position_convergence_comm is not None else 1.0,
            'rotation_convergence_ratio': rotation_convergence_comm / final_communications if rotation_convergence_comm is not None else 1.0,
            'total_iterations': len(data)
        }
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None

def main():
    # Find all result folders
    results_dir = "data/results/seq"
    
    if not os.path.exists(results_dir):
        print(f"Results directory {results_dir} not found!")
        return
    
    # Get all subdirectories
    result_folders = [d for d in os.listdir(results_dir) 
                     if os.path.isdir(os.path.join(results_dir, d))]
    
    print(f"Found {len(result_folders)} result folders")
    
    all_results = []
    processed_count = 0
    skipped_count = 0
    
    for folder in sorted(result_folders):
        folder_path = os.path.join(results_dir, folder)
        residual_file = os.path.join(folder_path, "residual_and_ate.txt")
        
        if not os.path.exists(residual_file):
            print(f"Skipping {folder}: no residual_and_ate.txt file")
            skipped_count += 1
            continue
            
        print(f"Processing {folder}...")
        result = analyze_convergence(residual_file)
        
        if result is not None:
            result['experiment_name'] = folder
            all_results.append(result)
            processed_count += 1
        else:
            skipped_count += 1
    
    print(f"\nProcessed {processed_count} files, skipped {skipped_count} files")
    
    if not all_results:
        print("No valid results found!")
        return
    
    # Convert to DataFrame for easier analysis
    df = pd.DataFrame(all_results)
    
    # Extract algorithm and grid size from experiment names
    df['algorithm'] = df['experiment_name'].str.extract(r'_([^_]+)_\d{4}-\d{2}-\d{2}')
    df['grid_size'] = df['experiment_name'].str.extract(r'grid_(\d+_\d+)_')
    
    # Create output file
    output_file = "convergence_analysis_results.txt"
    
    with open(output_file, 'w') as f:
        f.write("Convergence Analysis Results\n")
        f.write("=" * 50 + "\n\n")
        f.write("Columns explanation:\n")
        f.write("- experiment_name: Name of the experiment folder\n")
        f.write("- algorithm: Algorithm used (extracted from folder name)\n")
        f.write("- grid_size: Grid dimensions (extracted from folder name)\n")
        f.write("- total_communications: Total communications in the experiment\n")
        f.write("- final_position_error: Final APE (Absolute Position Error)\n")
        f.write("- final_rotation_error: Final ATE (Absolute Translation Error)\n")
        f.write("- position_convergence_comm: Communications when APE reached within 1% of final\n")
        f.write("- rotation_convergence_comm: Communications when ATE reached within 1% of final\n")
        f.write("- position_convergence_ratio: Ratio of convergence comm to total comm (APE)\n")
        f.write("- rotation_convergence_ratio: Ratio of convergence comm to total comm (ATE)\n")
        f.write("- total_iterations: Total number of data points in the file\n\n")
        
        # Write detailed results
        f.write("DETAILED RESULTS:\n")
        f.write("-" * 100 + "\n")
        
        for _, row in df.iterrows():
            f.write(f"Experiment: {row['experiment_name']}\n")
            f.write(f"  Algorithm: {row['algorithm']}\n")
            f.write(f"  Grid Size: {row['grid_size']}\n")
            f.write(f"  Total Communications: {row['total_communications']:.0f}\n")
            f.write(f"  Final Position Error: {row['final_position_error']:.6f}\n")
            f.write(f"  Final Rotation Error: {row['final_rotation_error']:.6f}\n")
            pos_conv = f"{row['position_convergence_comm']:.0f}" if pd.notna(row['position_convergence_comm']) else 'N/A'
            f.write(f"  Position Convergence (1%): {pos_conv} communications")
            if pd.notna(row['position_convergence_ratio']):
                f.write(f" ({row['position_convergence_ratio']:.2%} of total)")
            f.write("\n")
            rot_conv = f"{row['rotation_convergence_comm']:.0f}" if pd.notna(row['rotation_convergence_comm']) else 'N/A'
            f.write(f"  Rotation Convergence (1%): {rot_conv} communications")
            if pd.notna(row['rotation_convergence_ratio']):
                f.write(f" ({row['rotation_convergence_ratio']:.2%} of total)")
            f.write("\n")
            f.write(f"  Total Iterations: {row['total_iterations']}\n")
            f.write("\n")
        
        # Summary statistics by algorithm
        f.write("\nSUMMARY BY ALGORITHM:\n")
        f.write("-" * 50 + "\n")
        
        for algorithm in df['algorithm'].unique():
            if pd.isna(algorithm):
                continue
            alg_data = df[df['algorithm'] == algorithm]
            f.write(f"\nAlgorithm: {algorithm}\n")
            f.write(f"  Number of experiments: {len(alg_data)}\n")
            f.write(f"  Average position convergence ratio: {alg_data['position_convergence_ratio'].mean():.2%}\n")
            f.write(f"  Average rotation convergence ratio: {alg_data['rotation_convergence_ratio'].mean():.2%}\n")
            f.write(f"  Average final position error: {alg_data['final_position_error'].mean():.6f}\n")
            f.write(f"  Average final rotation error: {alg_data['final_rotation_error'].mean():.6f}\n")
    
    # Also save as CSV for further analysis
    csv_file = "convergence_analysis_results.csv"
    df.to_csv(csv_file, index=False)
    
    print(f"\nResults saved to:")
    print(f"  - {output_file} (detailed text report)")
    print(f"  - {csv_file} (CSV for further analysis)")
    
    # Print quick summary
    print(f"\nQuick Summary:")
    print(f"Total experiments analyzed: {len(df)}")
    print(f"Algorithms found: {sorted(df['algorithm'].dropna().unique())}")
    print(f"Grid sizes found: {sorted(df['grid_size'].dropna().unique())}")

if __name__ == "__main__":
    main()
