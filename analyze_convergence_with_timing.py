#!/usr/bin/env python3
"""
Enhanced script to analyze convergence with iteration numbers and runtime information.
Reads both residual_and_ate.txt and iter_time_comm.txt files to get complete picture.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from pathlib import Path

def extract_robot_count(grid_size_str):
    """Extract robot count from grid size string like '15_15' -> 15"""
    if pd.isna(grid_size_str):
        return None
    parts = grid_size_str.split('_')
    if len(parts) >= 2:
        return int(parts[0])
    return None

def find_convergence_iteration_and_time(iter_time_file, convergence_comm, use_final=False):
    """
    Find the iteration number and runtime when convergence communication is reached.
    
    Args:
        iter_time_file: Path to iter_time_comm.txt file
        convergence_comm: Communication count at convergence
        use_final: If True, return final values instead of convergence values
        
    Returns:
        tuple: (iteration, runtime) or (None, None) if not found
    """
    if not os.path.exists(iter_time_file):
        return None, None
        
    try:
        # Read the iter_time_comm.txt file
        iter_data = pd.read_csv(iter_time_file, sep='\s+', comment='#', header=None,
                               names=['iteration', 'total_time', 'total_communications'])
        
        if len(iter_data) == 0:
            return None, None
            
        # If use_final is True or convergence_comm is invalid, return final values
        if use_final or pd.isna(convergence_comm) or convergence_comm == 0:
            final_row = iter_data.iloc[-1]
            return final_row['iteration'], final_row['total_time']
        
        # Find the row where total_communications is closest to (but >= ) convergence_comm
        valid_rows = iter_data[iter_data['total_communications'] >= convergence_comm]
        
        if len(valid_rows) == 0:
            # If no row meets the convergence communication, return final values
            final_row = iter_data.iloc[-1]
            return final_row['iteration'], final_row['total_time']
            
        # Get the first row that meets or exceeds the convergence communication count
        closest_row = valid_rows.iloc[0]
        return closest_row['iteration'], closest_row['total_time']
        
    except Exception as e:
        print(f"Error reading {iter_time_file}: {e}")
        return None, None

def analyze_convergence_with_timing(results_dir="data/results/seq"):
    """
    Enhanced convergence analysis that includes iteration and timing information.
    """
    if not os.path.exists(results_dir):
        print(f"Results directory {results_dir} not found!")
        return None
        
    # Read the existing convergence analysis
    if not os.path.exists('convergence_analysis_results.csv'):
        print("convergence_analysis_results.csv not found! Run analyze_all_convergence.py first.")
        return None
        
    df = pd.read_csv('convergence_analysis_results.csv')
    
    # Add new columns for iteration and timing information
    df['position_convergence_iteration'] = None
    df['position_convergence_time'] = None
    df['rotation_convergence_iteration'] = None
    df['rotation_convergence_time'] = None
    
    print("Analyzing timing and iteration data...")
    
    for idx, row in df.iterrows():
        # Extract folder path from the experiment name
        folder_name = row['experiment_name']
        folder_path = os.path.join(results_dir, folder_name)
        iter_time_file = os.path.join(folder_path, "iter_time_comm.txt")
        
        print(f"Processing {folder_name}...")
        
        # Get position convergence timing
        if pd.notna(row['position_convergence_comm']) and row['position_convergence_comm'] > 0:
            # Method converged, use convergence point
            pos_iter, pos_time = find_convergence_iteration_and_time(
                iter_time_file, row['position_convergence_comm'], use_final=False)
        else:
            # Method failed to converge, use final values
            pos_iter, pos_time = find_convergence_iteration_and_time(
                iter_time_file, None, use_final=True)
            
        df.at[idx, 'position_convergence_iteration'] = pos_iter
        df.at[idx, 'position_convergence_time'] = pos_time
            
        # Get rotation convergence timing
        if pd.notna(row['rotation_convergence_comm']) and row['rotation_convergence_comm'] > 0:
            # Method converged, use convergence point
            rot_iter, rot_time = find_convergence_iteration_and_time(
                iter_time_file, row['rotation_convergence_comm'], use_final=False)
        else:
            # Method failed to converge, use final values
            rot_iter, rot_time = find_convergence_iteration_and_time(
                iter_time_file, None, use_final=True)
            
        df.at[idx, 'rotation_convergence_iteration'] = rot_iter
        df.at[idx, 'rotation_convergence_time'] = rot_time
    
    # Extract robot count
    df['robot_count'] = df['grid_size'].apply(extract_robot_count)
    df = df.dropna(subset=['robot_count']).sort_values('robot_count')
    
    # Save enhanced results
    df.to_csv('enhanced_convergence_analysis.csv', index=False)
    print(f"Enhanced analysis saved to: enhanced_convergence_analysis.csv")
    
    return df

def plot_convergence_analysis(df):
    """Create comprehensive plots of convergence analysis including timing."""
    
    # Set up the plotting style
    plt.style.use('default')
    colors = {'asapp': 'red', 'dgs': 'blue', 'geodesic-mesa': 'green'}
    
    # Create a large figure with multiple subplots
    fig, axes = plt.subplots(3, 3, figsize=(18, 15))
    fig.suptitle('Enhanced Convergence Analysis vs. Number of Robots', fontsize=16, fontweight='bold')
    
    # Plot 1: Total Communications vs Robot Count
    ax = axes[0, 0]
    for algorithm in df['algorithm'].unique():
        alg_data = df[df['algorithm'] == algorithm]
        ax.plot(alg_data['robot_count'], alg_data['total_communications'], 
                'o-', label=algorithm, color=colors.get(algorithm, 'black'), linewidth=2, markersize=6)
    ax.set_xlabel('Number of Robots')
    ax.set_ylabel('Total Communications')
    ax.set_title('Total Communications')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_yscale('log')
    
    # Plot 2: Position Convergence Communications vs Robot Count
    ax = axes[0, 1]
    for algorithm in df['algorithm'].unique():
        alg_data = df[df['algorithm'] == algorithm]
        valid_data = alg_data.dropna(subset=['position_convergence_comm'])
        if len(valid_data) > 0:
            ax.plot(valid_data['robot_count'], valid_data['position_convergence_comm'], 
                    'o-', label=algorithm, color=colors.get(algorithm, 'black'), linewidth=2, markersize=6)
    ax.set_xlabel('Number of Robots')
    ax.set_ylabel('Communications to Convergence')
    ax.set_title('Position Convergence Communications')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_yscale('log')
    
    # Plot 3: Position Convergence Iterations vs Robot Count
    ax = axes[0, 2]
    for algorithm in df['algorithm'].unique():
        alg_data = df[df['algorithm'] == algorithm]
        valid_data = alg_data.dropna(subset=['position_convergence_iteration'])
        if len(valid_data) > 0:
            ax.plot(valid_data['robot_count'], valid_data['position_convergence_iteration'], 
                    'o-', label=algorithm, color=colors.get(algorithm, 'black'), linewidth=2, markersize=6)
    ax.set_xlabel('Number of Robots')
    ax.set_ylabel('Iterations to Convergence')
    ax.set_title('Position Convergence Iterations')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot 4: Position Convergence Time vs Robot Count
    ax = axes[1, 0]
    for algorithm in df['algorithm'].unique():
        alg_data = df[df['algorithm'] == algorithm]
        valid_data = alg_data.dropna(subset=['position_convergence_time'])
        if len(valid_data) > 0:
            ax.plot(valid_data['robot_count'], valid_data['position_convergence_time'], 
                    'o-', label=algorithm, color=colors.get(algorithm, 'black'), linewidth=2, markersize=6)
    ax.set_xlabel('Number of Robots')
    ax.set_ylabel('Time to Convergence (s)')
    ax.set_title('Position Convergence Time')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_yscale('log')
    
    # Plot 5: Convergence Efficiency (% of total) vs Robot Count
    ax = axes[1, 1]
    for algorithm in df['algorithm'].unique():
        alg_data = df[df['algorithm'] == algorithm]
        valid_data = alg_data.dropna(subset=['position_convergence_ratio'])
        if len(valid_data) > 0:
            ax.plot(valid_data['robot_count'], valid_data['position_convergence_ratio'] * 100, 
                    'o-', label=algorithm, color=colors.get(algorithm, 'black'), linewidth=2, markersize=6)
    ax.set_xlabel('Number of Robots')
    ax.set_ylabel('Convergence Efficiency (%)')
    ax.set_title('Position Convergence Efficiency')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 105)
    
    # Plot 6: Final Position Error vs Robot Count
    ax = axes[1, 2]
    for algorithm in df['algorithm'].unique():
        alg_data = df[df['algorithm'] == algorithm]
        valid_data = alg_data[alg_data['final_position_error'] < 1000]  # Filter outliers
        if len(valid_data) > 0:
            ax.plot(valid_data['robot_count'], valid_data['final_position_error'], 
                    'o-', label=algorithm, color=colors.get(algorithm, 'black'), linewidth=2, markersize=6)
    ax.set_xlabel('Number of Robots')
    ax.set_ylabel('Final Position Error')
    ax.set_title('Final Position Error')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_yscale('log')
    
    # Plot 7: Communication efficiency (comm/iteration) at convergence
    ax = axes[2, 0]
    for algorithm in df['algorithm'].unique():
        alg_data = df[df['algorithm'] == algorithm]
        valid_data = alg_data.dropna(subset=['position_convergence_comm', 'position_convergence_iteration'])
        if len(valid_data) > 0:
            comm_per_iter = valid_data['position_convergence_comm'] / valid_data['position_convergence_iteration']
            ax.plot(valid_data['robot_count'], comm_per_iter, 
                    'o-', label=algorithm, color=colors.get(algorithm, 'black'), linewidth=2, markersize=6)
    ax.set_xlabel('Number of Robots')
    ax.set_ylabel('Communications per Iteration')
    ax.set_title('Communication Efficiency at Convergence')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_yscale('log')
    
    # Plot 8: Time efficiency (time/iteration) at convergence
    ax = axes[2, 1]
    for algorithm in df['algorithm'].unique():
        alg_data = df[df['algorithm'] == algorithm]
        valid_data = alg_data.dropna(subset=['position_convergence_time', 'position_convergence_iteration'])
        if len(valid_data) > 0:
            time_per_iter = valid_data['position_convergence_time'] / valid_data['position_convergence_iteration']
            ax.plot(valid_data['robot_count'], time_per_iter, 
                    'o-', label=algorithm, color=colors.get(algorithm, 'black'), linewidth=2, markersize=6)
    ax.set_xlabel('Number of Robots')
    ax.set_ylabel('Time per Iteration (s)')
    ax.set_title('Time Efficiency at Convergence')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot 9: Iterations vs Communications scaling at convergence
    ax = axes[2, 2]
    for algorithm in df['algorithm'].unique():
        alg_data = df[df['algorithm'] == algorithm]
        valid_data = alg_data.dropna(subset=['position_convergence_comm', 'position_convergence_iteration'])
        if len(valid_data) > 0:
            ax.scatter(valid_data['position_convergence_iteration'], valid_data['position_convergence_comm'], 
                      label=algorithm, color=colors.get(algorithm, 'black'), s=50, alpha=0.7)
    ax.set_xlabel('Iterations to Convergence')
    ax.set_ylabel('Communications to Convergence')
    ax.set_title('Iterations vs Communications')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xscale('log')
    ax.set_yscale('log')
    
    plt.tight_layout()
    plt.savefig('enhanced_convergence_analysis.png', dpi=300, bbox_inches='tight')
    print("Saved: enhanced_convergence_analysis.png")
    plt.close()

def print_summary_statistics(df):
    """Print comprehensive summary statistics."""
    print("\nEnhanced Summary Statistics by Algorithm:")
    print("=" * 80)
    
    for algorithm in sorted(df['algorithm'].unique()):
        alg_data = df[df['algorithm'] == algorithm]
        print(f"\n{algorithm.upper()}:")
        print(f"  Robot counts tested: {sorted(alg_data['robot_count'].unique())}")
        
        # Communication statistics
        print(f"  Total communications range: {alg_data['total_communications'].min():.0f} - {alg_data['total_communications'].max():.0f}")
        
        # Convergence communication statistics
        valid_comm = alg_data.dropna(subset=['position_convergence_comm'])
        if len(valid_comm) > 0:
            print(f"  Convergence communications range: {valid_comm['position_convergence_comm'].min():.0f} - {valid_comm['position_convergence_comm'].max():.0f}")
        
        # Convergence iteration statistics
        valid_iter = alg_data.dropna(subset=['position_convergence_iteration'])
        if len(valid_iter) > 0:
            print(f"  Convergence iterations range: {valid_iter['position_convergence_iteration'].min():.0f} - {valid_iter['position_convergence_iteration'].max():.0f}")
            
        # Convergence time statistics
        valid_time = alg_data.dropna(subset=['position_convergence_time'])
        if len(valid_time) > 0:
            print(f"  Convergence time range: {valid_time['position_convergence_time'].min():.1f}s - {valid_time['position_convergence_time'].max():.1f}s")
            
        # Efficiency statistics
        valid_eff = alg_data.dropna(subset=['position_convergence_ratio'])
        if len(valid_eff) > 0:
            print(f"  Average convergence efficiency: {valid_eff['position_convergence_ratio'].mean():.1%}")

def main():
    # Analyze convergence with timing information
    df = analyze_convergence_with_timing()
    
    if df is None:
        return
        
    print(f"\nEnhanced analysis completed for {len(df)} experiments")
    print(f"Algorithms: {sorted(df['algorithm'].unique())}")
    print(f"Robot counts: {sorted(df['robot_count'].unique())}")
    
    # Create plots
    plot_convergence_analysis(df)
    
    # Print summary statistics
    print_summary_statistics(df)
    
    # Create a detailed summary table
    summary_cols = ['experiment_name', 'algorithm', 'robot_count', 'total_communications',
                   'position_convergence_comm', 'position_convergence_iteration', 
                   'position_convergence_time', 'position_convergence_ratio']
    
    summary_df = df[summary_cols].copy()
    summary_df = summary_df.round({'position_convergence_time': 2, 'position_convergence_ratio': 4})
    
    print(f"\nDetailed Summary Table:")
    print("=" * 120)
    print(summary_df.to_string(index=False))
    
    # Save summary
    summary_df.to_csv('convergence_summary_with_timing.csv', index=False)
    print(f"\nFiles saved:")
    print(f"  - enhanced_convergence_analysis.csv (complete data)")
    print(f"  - convergence_summary_with_timing.csv (summary table)")
    print(f"  - enhanced_convergence_analysis.png (visualization)")

if __name__ == "__main__":
    main()
