#!/usr/bin/env python3
"""
Script to plot communication vs. number of robots from convergence analysis results.
Extracts robot count from grid dimensions and creates visualization.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

def extract_robot_count(grid_size_str):
    """
    Extract robot count from grid size string like '15_15' -> 15
    Assumes square grids where both dimensions are the same
    """
    if pd.isna(grid_size_str):
        return None
    parts = grid_size_str.split('_')
    if len(parts) >= 2:
        return int(parts[0])  # Take the first dimension
    return None

def main():
    # Read the convergence analysis results
    df = pd.read_csv('convergence_analysis_results.csv')
    
    # Extract robot count from grid size
    df['robot_count'] = df['grid_size'].apply(extract_robot_count)
    
    # Remove rows where robot count couldn't be extracted
    df = df.dropna(subset=['robot_count'])
    
    # Sort by robot count for better plotting
    df = df.sort_values('robot_count')
    
    print(f"Data loaded: {len(df)} experiments")
    print(f"Algorithms: {sorted(df['algorithm'].unique())}")
    print(f"Robot counts: {sorted(df['robot_count'].unique())}")
    
    # Create the plot
    plt.style.use('default')
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Communication Analysis vs. Number of Robots', fontsize=16, fontweight='bold')
    
    # Define colors for algorithms
    colors = {'asapp': 'red', 'dgs': 'blue', 'geodesic-mesa': 'green'}
    
    # Plot 1: Total Communications vs Robot Count
    ax1 = axes[0, 0]
    for algorithm in df['algorithm'].unique():
        alg_data = df[df['algorithm'] == algorithm]
        ax1.plot(alg_data['robot_count'], alg_data['total_communications'], 
                'o-', label=algorithm, color=colors.get(algorithm, 'black'), linewidth=2, markersize=6)
    
    ax1.set_xlabel('Number of Robots')
    ax1.set_ylabel('Total Communications')
    ax1.set_title('Total Communications vs. Robot Count')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_yscale('log')  # Log scale due to large differences
    
    # Plot 2: Position Convergence Communications vs Robot Count
    ax2 = axes[0, 1]
    for algorithm in df['algorithm'].unique():
        alg_data = df[df['algorithm'] == algorithm]
        # Filter out NaN values for convergence communications
        valid_data = alg_data.dropna(subset=['position_convergence_comm'])
        if len(valid_data) > 0:
            ax2.plot(valid_data['robot_count'], valid_data['position_convergence_comm'], 
                    'o-', label=algorithm, color=colors.get(algorithm, 'black'), linewidth=2, markersize=6)
    
    ax2.set_xlabel('Number of Robots')
    ax2.set_ylabel('Communications to 1% Position Convergence')
    ax2.set_title('Position Convergence Communications vs. Robot Count')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_yscale('log')
    
    # Plot 3: Position Convergence Ratio vs Robot Count
    ax3 = axes[1, 0]
    for algorithm in df['algorithm'].unique():
        alg_data = df[df['algorithm'] == algorithm]
        valid_data = alg_data.dropna(subset=['position_convergence_ratio'])
        if len(valid_data) > 0:
            ax3.plot(valid_data['robot_count'], valid_data['position_convergence_ratio'] * 100, 
                    'o-', label=algorithm, color=colors.get(algorithm, 'black'), linewidth=2, markersize=6)
    
    ax3.set_xlabel('Number of Robots')
    ax3.set_ylabel('Position Convergence Ratio (%)')
    ax3.set_title('Position Convergence Efficiency vs. Robot Count')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    ax3.set_ylim(0, 105)
    
    # Plot 4: Final Position Error vs Robot Count
    ax4 = axes[1, 1]
    for algorithm in df['algorithm'].unique():
        alg_data = df[df['algorithm'] == algorithm]
        # Filter out extremely large values (likely diverged cases)
        valid_data = alg_data[alg_data['final_position_error'] < 1000]
        if len(valid_data) > 0:
            ax4.plot(valid_data['robot_count'], valid_data['final_position_error'], 
                    'o-', label=algorithm, color=colors.get(algorithm, 'black'), linewidth=2, markersize=6)
    
    ax4.set_xlabel('Number of Robots')
    ax4.set_ylabel('Final Position Error')
    ax4.set_title('Final Position Error vs. Robot Count')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    ax4.set_yscale('log')
    
    plt.tight_layout()
    plt.savefig('communication_vs_robots_analysis.png', dpi=300, bbox_inches='tight')
    print("Saved: communication_vs_robots_analysis.png")
    plt.close()
    
    # Create a separate detailed plot for communication scaling
    fig2, ax = plt.subplots(1, 1, figsize=(12, 8))
    
    for algorithm in df['algorithm'].unique():
        alg_data = df[df['algorithm'] == algorithm]
        ax.plot(alg_data['robot_count'], alg_data['total_communications'], 
                'o-', label=f'{algorithm} (total)', color=colors.get(algorithm, 'black'), 
                linewidth=3, markersize=8, alpha=0.8)
        
        # Also plot convergence communications if available
        valid_data = alg_data.dropna(subset=['position_convergence_comm'])
        if len(valid_data) > 0:
            ax.plot(valid_data['robot_count'], valid_data['position_convergence_comm'], 
                    's--', label=f'{algorithm} (1% conv.)', color=colors.get(algorithm, 'black'), 
                    linewidth=2, markersize=6, alpha=0.6)
    
    ax.set_xlabel('Number of Robots', fontsize=14)
    ax.set_ylabel('Communications', fontsize=14)
    ax.set_title('Communication Scaling with Robot Count', fontsize=16, fontweight='bold')
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.set_yscale('log')
    
    # Add scaling reference lines
    robot_range = np.array([5, 15])
    
    # Linear scaling reference
    linear_ref = robot_range * 1000  # Arbitrary scaling
    ax.plot(robot_range, linear_ref, 'k:', alpha=0.5, label='Linear reference')
    
    # Quadratic scaling reference
    quad_ref = (robot_range ** 2) * 100
    ax.plot(robot_range, quad_ref, 'k-.', alpha=0.5, label='Quadratic reference')
    
    ax.legend(fontsize=11)
    
    plt.tight_layout()
    plt.savefig('communication_scaling_detailed.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # Print summary statistics
    print("\nSummary Statistics by Algorithm:")
    print("=" * 50)
    
    for algorithm in sorted(df['algorithm'].unique()):
        alg_data = df[df['algorithm'] == algorithm]
        print(f"\n{algorithm.upper()}:")
        print(f"  Robot counts tested: {sorted(alg_data['robot_count'].unique())}")
        print(f"  Communication range: {alg_data['total_communications'].min():.0f} - {alg_data['total_communications'].max():.0f}")
        
        valid_conv = alg_data.dropna(subset=['position_convergence_ratio'])
        if len(valid_conv) > 0:
            print(f"  Avg convergence efficiency: {valid_conv['position_convergence_ratio'].mean():.1%}")
            print(f"  Convergence efficiency range: {valid_conv['position_convergence_ratio'].min():.1%} - {valid_conv['position_convergence_ratio'].max():.1%}")
        
        valid_errors = alg_data[alg_data['final_position_error'] < 1000]
        if len(valid_errors) > 0:
            print(f"  Final error range: {valid_errors['final_position_error'].min():.6f} - {valid_errors['final_position_error'].max():.6f}")
    
    # Create a data table for easy reference
    summary_table = df.groupby(['algorithm', 'robot_count']).agg({
        'total_communications': 'first',
        'position_convergence_comm': 'first',
        'position_convergence_ratio': 'first',
        'final_position_error': 'first'
    }).round(6)
    
    print("\nDetailed Results Table:")
    print("=" * 80)
    print(summary_table.to_string())
    
    # Save summary table
    summary_table.to_csv('communication_scaling_summary.csv')
    print(f"\nSummary table saved to: communication_scaling_summary.csv")
    print(f"Plots saved to: communication_vs_robots_analysis.png, communication_scaling_detailed.png")

if __name__ == "__main__":
    main()
