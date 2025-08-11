#!/usr/bin/env python3
"""
Simplified script to plot only position convergence metrics:
- Position Convergence Communications vs Robot Count
- Position Convergence Iterations vs Robot Count  
- Position Convergence Time vs Robot Count
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def plot_position_convergence_metrics():
    """Plot the three key position convergence metrics."""
    
    # Read the enhanced convergence analysis results
    try:
        df = pd.read_csv('enhanced_convergence_analysis.csv')
    except FileNotFoundError:
        print("enhanced_convergence_analysis.csv not found! Run analyze_convergence_with_timing.py first.")
        return
    
    # Filter out rows without robot_count
    df = df.dropna(subset=['robot_count']).sort_values('robot_count')
    
    print(f"Plotting data for {len(df)} experiments")
    print(f"Algorithms: {sorted(df['algorithm'].unique())}")
    print(f"Robot counts: {sorted(df['robot_count'].unique())}")
    
    # Set up the plotting style for IEEE paper format
    plt.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['Times New Roman'],
        'font.size': 8,
        'axes.titlesize': 8,
        'axes.labelsize': 8,
        'xtick.labelsize': 8,
        'ytick.labelsize': 8,
        'legend.fontsize': 7,
        'figure.titlesize': 9,
        'lines.linewidth': 1.5,
        'lines.markersize': 4,
        'grid.linewidth': 0.5,
        'axes.linewidth': 0.8
    })
    
    colors = {'asapp': 'red', 'dgs': 'blue', 'geodesic-mesa': 'green', 'CBS': 'purple'}
    markers = {'asapp': 'o', 'dgs': 's', 'geodesic-mesa': '^', 'CBS': 'D'}
    
    # IEEE single column width is approximately 3.5 inches
    # For 3 subplots, we need more width while keeping height reasonable
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 2.8))  # 3.5 inches per subplot
    fig.suptitle('Position Convergence Analysis vs. Number of Robots', fontsize=9, fontweight='bold')
    
    # Plot 1: Position Convergence Communications vs Robot Count
    ax1 = axes[0]
    for algorithm in sorted(df['algorithm'].unique()):
        alg_data = df[df['algorithm'] == algorithm]
        valid_data = alg_data.dropna(subset=['position_convergence_comm'])
        if len(valid_data) > 0:
            ax1.plot(valid_data['robot_count'], valid_data['position_convergence_comm'], 
                    marker=markers.get(algorithm, 'o'), linestyle='-', 
                    label=algorithm, color=colors.get(algorithm, 'black'), 
                    linewidth=1.5, markersize=4, markerfacecolor='white', 
                    markeredgewidth=1, markeredgecolor=colors.get(algorithm, 'black'))
    
    ax1.set_xlabel('Number of Robots', fontsize=8)
    ax1.set_ylabel('Communications to 1%\nPosition Convergence', fontsize=8)
    ax1.set_title('Position Convergence\nCommunications', fontsize=8, fontweight='bold')
    ax1.legend(fontsize=7, loc='upper left')
    ax1.grid(True, alpha=0.3, linewidth=0.5)
    # ax1.set_yscale('log')
    
    # Add robot count labels on x-axis
    robot_counts = sorted(df['robot_count'].unique())
    ax1.set_xticks(robot_counts)
    ax1.set_xticklabels([f'{int(x)}' for x in robot_counts])
    
    # Plot 2: Position Convergence Iterations vs Robot Count
    ax2 = axes[1]
    for algorithm in sorted(df['algorithm'].unique()):
        alg_data = df[df['algorithm'] == algorithm]
        valid_data = alg_data.dropna(subset=['position_convergence_iteration'])
        if len(valid_data) > 0:
            ax2.plot(valid_data['robot_count'], valid_data['position_convergence_iteration'], 
                    marker=markers.get(algorithm, 'o'), linestyle='-',
                    label=algorithm, color=colors.get(algorithm, 'black'), 
                    linewidth=1.5, markersize=4, markerfacecolor='white', 
                    markeredgewidth=1, markeredgecolor=colors.get(algorithm, 'black'))
    
    ax2.set_xlabel('Number of Robots', fontsize=8)
    ax2.set_ylabel('Iterations to 1%\nPosition Convergence', fontsize=8)
    ax2.set_title('Position Convergence\nIterations', fontsize=8, fontweight='bold')
    ax2.legend(fontsize=7, loc='upper left')
    ax2.grid(True, alpha=0.3, linewidth=0.5)
    # ax2.set_yscale('log')
    
    ax2.set_xticks(robot_counts)
    ax2.set_xticklabels([f'{int(x)}' for x in robot_counts])
    
    # Plot 3: Position Convergence Time vs Robot Count
    ax3 = axes[2]
    for algorithm in sorted(df['algorithm'].unique()):
        alg_data = df[df['algorithm'] == algorithm]
        valid_data = alg_data.dropna(subset=['position_convergence_time'])
        if len(valid_data) > 0:
            ax3.plot(valid_data['robot_count'], valid_data['position_convergence_time'], 
                    marker=markers.get(algorithm, 'o'), linestyle='-',
                    label=algorithm, color=colors.get(algorithm, 'black'), 
                    linewidth=1.5, markersize=4, markerfacecolor='white', 
                    markeredgewidth=1, markeredgecolor=colors.get(algorithm, 'black'))
    
    ax3.set_xlabel('Number of Robots', fontsize=8)
    ax3.set_ylabel('Time to 1% Position\nConvergence (s)', fontsize=8)
    ax3.set_title('Position Convergence\nTime', fontsize=8, fontweight='bold')
    ax3.legend(fontsize=7, loc='upper left')
    ax3.grid(True, alpha=0.3, linewidth=0.5)
    # ax3.set_yscale('log')
    
    ax3.set_xticks(robot_counts)
    ax3.set_xticklabels([f'{int(x)}' for x in robot_counts])
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.85)  # Make room for suptitle
    plt.savefig('position_convergence_analysis.png', dpi=300, bbox_inches='tight')
    print("Saved: position_convergence_analysis.png")
    plt.close()
    
    # Create a summary table for the three metrics
    summary_data = []
    for algorithm in sorted(df['algorithm'].unique()):
        alg_data = df[df['algorithm'] == algorithm]
        for robot_count in sorted(alg_data['robot_count'].unique()):
            robot_data = alg_data[alg_data['robot_count'] == robot_count]
            if len(robot_data) > 0:
                row_data = robot_data.iloc[0]
                summary_data.append({
                    'Algorithm': algorithm,
                    'Robot_Count': int(robot_count),
                    'Convergence_Communications': row_data.get('position_convergence_comm', 'N/A'),
                    'Convergence_Iterations': row_data.get('position_convergence_iteration', 'N/A'),
                    'Convergence_Time_s': row_data.get('position_convergence_time', 'N/A'),
                    'Final_Position_Error': row_data.get('final_position_error', 'N/A')
                })
    
    summary_df = pd.DataFrame(summary_data)
    
    # Print summary table
    print("\nPosition Convergence Summary Table:")
    print("=" * 100)
    print(summary_df.to_string(index=False, float_format='%.2f'))
    
    # Save summary table
    summary_df.to_csv('position_convergence_summary.csv', index=False)
    print(f"\nSummary table saved to: position_convergence_summary.csv")
    
    # Print algorithm comparison
    print("\nAlgorithm Performance Comparison:")
    print("=" * 60)
    
    for algorithm in sorted(df['algorithm'].unique()):
        alg_data = df[df['algorithm'] == algorithm]
        
        # Filter valid convergence data
        valid_comm = alg_data.dropna(subset=['position_convergence_comm'])
        valid_iter = alg_data.dropna(subset=['position_convergence_iteration'])
        valid_time = alg_data.dropna(subset=['position_convergence_time'])
        
        print(f"\n{algorithm.upper()}:")
        if len(valid_comm) > 0:
            print(f"  Communications: {valid_comm['position_convergence_comm'].min():.0f} - {valid_comm['position_convergence_comm'].max():.0f}")
        if len(valid_iter) > 0:
            print(f"  Iterations: {valid_iter['position_convergence_iteration'].min():.0f} - {valid_iter['position_convergence_iteration'].max():.0f}")
        if len(valid_time) > 0:
            print(f"  Time: {valid_time['position_convergence_time'].min():.1f}s - {valid_time['position_convergence_time'].max():.1f}s")
        
        # Calculate averages
        if len(valid_comm) > 0:
            print(f"  Average communications: {valid_comm['position_convergence_comm'].mean():.0f}")
        if len(valid_iter) > 0:
            print(f"  Average iterations: {valid_iter['position_convergence_iteration'].mean():.0f}")
        if len(valid_time) > 0:
            print(f"  Average time: {valid_time['position_convergence_time'].mean():.1f}s")

def plot_normalized_convergence_metrics():
    """Plot the three key position convergence metrics normalized by number of robots."""
    
    # Read the enhanced convergence analysis results
    try:
        df = pd.read_csv('enhanced_convergence_analysis.csv')
    except FileNotFoundError:
        print("enhanced_convergence_analysis.csv not found! Run analyze_convergence_with_timing.py first.")
        return
    
    # Filter out rows without robot_count
    df = df.dropna(subset=['robot_count']).sort_values('robot_count')
    
    print(f"\nPlotting normalized data for {len(df)} experiments")
    print(f"Algorithms: {sorted(df['algorithm'].unique())}")
    print(f"Robot counts: {sorted(df['robot_count'].unique())}")
    
    # Set up the plotting style for IEEE paper format
    plt.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['Times New Roman'],
        'font.size': 8,
        'axes.titlesize': 8,
        'axes.labelsize': 8,
        'xtick.labelsize': 8,
        'ytick.labelsize': 8,
        'legend.fontsize': 7,
        'figure.titlesize': 9,
        'lines.linewidth': 1.5,
        'lines.markersize': 4,
        'grid.linewidth': 0.5,
        'axes.linewidth': 0.8
    })
    
    colors = {'asapp': 'red', 'dgs': 'blue', 'geodesic-mesa': 'green', 'CBS': 'purple'}
    markers = {'asapp': 'o', 'dgs': 's', 'geodesic-mesa': '^', 'CBS': 'D'}
    
    # IEEE single column width formatting
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 2.8))
    fig.suptitle('Position Convergence Analysis Normalized by Number of Robots', fontsize=9, fontweight='bold')
    
    # Plot 1: Position Convergence Communications per Robot vs Robot Count
    ax1 = axes[0]
    for algorithm in sorted(df['algorithm'].unique()):
        alg_data = df[df['algorithm'] == algorithm]
        valid_data = alg_data.dropna(subset=['position_convergence_comm'])
        if len(valid_data) > 0:
            normalized_comm = valid_data['position_convergence_comm'] / valid_data['robot_count']
            ax1.plot(valid_data['robot_count'], normalized_comm, 
                    marker=markers.get(algorithm, 'o'), linestyle='-', 
                    label=algorithm, color=colors.get(algorithm, 'black'), 
                    linewidth=1.5, markersize=4, markerfacecolor='white', 
                    markeredgewidth=1, markeredgecolor=colors.get(algorithm, 'black'))
    
    ax1.set_xlabel('Number of Robots', fontsize=8)
    ax1.set_ylabel('Communications\nper Robot', fontsize=8)
    ax1.set_title('Position Convergence\nCommunications per Robot', fontsize=8, fontweight='bold')
    ax1.legend(fontsize=7, loc='upper left')
    ax1.grid(True, alpha=0.3, linewidth=0.5)
    
    # Add robot count labels on x-axis
    robot_counts = sorted(df['robot_count'].unique())
    ax1.set_xticks(robot_counts)
    ax1.set_xticklabels([f'{int(x)}' for x in robot_counts])
    
    # Plot 2: Position Convergence Iterations per Robot vs Robot Count
    ax2 = axes[1]
    for algorithm in sorted(df['algorithm'].unique()):
        alg_data = df[df['algorithm'] == algorithm]
        valid_data = alg_data.dropna(subset=['position_convergence_iteration'])
        if len(valid_data) > 0:
            normalized_iter = valid_data['position_convergence_iteration'] / valid_data['robot_count']
            ax2.plot(valid_data['robot_count'], normalized_iter, 
                    marker=markers.get(algorithm, 'o'), linestyle='-',
                    label=algorithm, color=colors.get(algorithm, 'black'), 
                    linewidth=1.5, markersize=4, markerfacecolor='white', 
                    markeredgewidth=1, markeredgecolor=colors.get(algorithm, 'black'))
    
    ax2.set_xlabel('Number of Robots', fontsize=8)
    ax2.set_ylabel('Iterations\nper Robot', fontsize=8)
    ax2.set_title('Position Convergence\nIterations per Robot', fontsize=8, fontweight='bold')
    ax2.legend(fontsize=7, loc='upper left')
    ax2.grid(True, alpha=0.3, linewidth=0.5)
    
    ax2.set_xticks(robot_counts)
    ax2.set_xticklabels([f'{int(x)}' for x in robot_counts])
    
    # Plot 3: Position Convergence Time per Robot vs Robot Count
    ax3 = axes[2]
    for algorithm in sorted(df['algorithm'].unique()):
        alg_data = df[df['algorithm'] == algorithm]
        valid_data = alg_data.dropna(subset=['position_convergence_time'])
        if len(valid_data) > 0:
            normalized_time = valid_data['position_convergence_time'] / valid_data['robot_count']
            ax3.plot(valid_data['robot_count'], normalized_time, 
                    marker=markers.get(algorithm, 'o'), linestyle='-',
                    label=algorithm, color=colors.get(algorithm, 'black'), 
                    linewidth=1.5, markersize=4, markerfacecolor='white', 
                    markeredgewidth=1, markeredgecolor=colors.get(algorithm, 'black'))
    
    ax3.set_xlabel('Number of Robots', fontsize=8)
    ax3.set_ylabel('Time per Robot (s)', fontsize=8)
    ax3.set_title('Position Convergence\nTime per Robot', fontsize=8, fontweight='bold')
    ax3.legend(fontsize=7, loc='upper left')
    ax3.grid(True, alpha=0.3, linewidth=0.5)
    
    ax3.set_xticks(robot_counts)
    ax3.set_xticklabels([f'{int(x)}' for x in robot_counts])
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.85)  # Make room for suptitle
    plt.savefig('position_convergence_normalized.png', dpi=300, bbox_inches='tight')
    print("Saved: position_convergence_normalized.png")
    plt.close()
    
    # Create a normalized summary table
    normalized_summary_data = []
    for algorithm in sorted(df['algorithm'].unique()):
        alg_data = df[df['algorithm'] == algorithm]
        for robot_count in sorted(alg_data['robot_count'].unique()):
            robot_data = alg_data[alg_data['robot_count'] == robot_count]
            if len(robot_data) > 0:
                row_data = robot_data.iloc[0]
                normalized_summary_data.append({
                    'Algorithm': algorithm,
                    'Robot_Count': int(robot_count),
                    'Comm_per_Robot': row_data.get('position_convergence_comm', 0) / robot_count if pd.notna(row_data.get('position_convergence_comm')) else 'N/A',
                    'Iter_per_Robot': row_data.get('position_convergence_iteration', 0) / robot_count if pd.notna(row_data.get('position_convergence_iteration')) else 'N/A',
                    'Time_per_Robot_s': row_data.get('position_convergence_time', 0) / robot_count if pd.notna(row_data.get('position_convergence_time')) else 'N/A',
                })
    
    normalized_summary_df = pd.DataFrame(normalized_summary_data)
    
    # Print normalized summary table
    print("\nNormalized Position Convergence Summary Table:")
    print("=" * 80)
    print(normalized_summary_df.to_string(index=False, float_format='%.2f'))
    
    # Save normalized summary table
    normalized_summary_df.to_csv('position_convergence_normalized_summary.csv', index=False)
    print(f"\nNormalized summary table saved to: position_convergence_normalized_summary.csv")
    
    # Print normalized algorithm comparison
    print("\nNormalized Algorithm Performance Comparison:")
    print("=" * 60)
    
    for algorithm in sorted(df['algorithm'].unique()):
        alg_data = df[df['algorithm'] == algorithm]
        
        # Calculate normalized metrics
        valid_comm = alg_data.dropna(subset=['position_convergence_comm'])
        valid_iter = alg_data.dropna(subset=['position_convergence_iteration'])
        valid_time = alg_data.dropna(subset=['position_convergence_time'])
        
        print(f"\n{algorithm.upper()} (per robot):")
        if len(valid_comm) > 0:
            comm_per_robot = valid_comm['position_convergence_comm'] / valid_comm['robot_count']
            print(f"  Communications: {comm_per_robot.min():.0f} - {comm_per_robot.max():.0f} (avg: {comm_per_robot.mean():.0f})")
        if len(valid_iter) > 0:
            iter_per_robot = valid_iter['position_convergence_iteration'] / valid_iter['robot_count']
            print(f"  Iterations: {iter_per_robot.min():.0f} - {iter_per_robot.max():.0f} (avg: {iter_per_robot.mean():.0f})")
        if len(valid_time) > 0:
            time_per_robot = valid_time['position_convergence_time'] / valid_time['robot_count']
            print(f"  Time: {time_per_robot.min():.1f}s - {time_per_robot.max():.1f}s (avg: {time_per_robot.mean():.1f}s)")

def main():
    plot_position_convergence_metrics()
    plot_normalized_convergence_metrics()

if __name__ == "__main__":
    main()
