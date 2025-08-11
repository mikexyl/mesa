#!/usr/bin/env python3
"""
Create IEEE-style plots with proper font fallback
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def main():
    # Set up IEEE plotting style with font fallback
    plt.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif', 'serif'],
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
    
    # Load data
    try:
        df = pd.read_csv('enhanced_convergence_analysis.csv')
    except FileNotFoundError:
        print("enhanced_convergence_analysis.csv not found!")
        return
    
    df = df.dropna(subset=['robot_count']).sort_values('robot_count')
    
    colors = {'asapp': 'red', 'dgs': 'blue', 'geodesic-mesa': 'green', 'CBS': 'purple'}
    markers = {'asapp': 'o', 'dgs': 's', 'geodesic-mesa': '^', 'CBS': 'D'}
    
    # Legend override dictionary - modify these to change legend labels
    # Set to None to use original algorithm names
    legend_override = {
        'CBS': 'CBS',
        'asapp': 'ASAPP', 
        'dgs': 'DGS',
        'geodesic-mesa': 'Geodesic-MESA'
    }
    
    # Create both original and normalized plots
    create_original_plots(df, colors, markers, legend_override)
    create_normalized_plots(df, colors, markers, legend_override)

def create_original_plots(df, colors, markers, legend_override=None):
    """Create plots showing absolute metrics vs robot count"""
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(3.5, 4.5), sharex=True)
    
    # Store line objects for legend
    legend_lines = []
    legend_labels = []
    
    # Plot Communications vs Robots
    for algo in df['algorithm'].unique():
        if pd.isna(algo):
            continue
        algo_data = df[df['algorithm'] == algo]
        line = ax1.plot(algo_data['robot_count'], algo_data['position_convergence_comm'], 
                       color=colors[algo], marker=markers[algo], 
                       linewidth=1.5, markersize=4, label=algo)
        
        # Only add to legend once per algorithm
        if algo not in [label for label in legend_labels]:
            legend_lines.append(line[0])
            display_name = legend_override.get(algo, algo) if legend_override else algo
            legend_labels.append(display_name)
    
    ax1.set_ylabel('Communications')
    ax1.grid(True, alpha=0.3)
    
    # Plot Iterations vs Robots
    for algo in df['algorithm'].unique():
        if pd.isna(algo):
            continue
        algo_data = df[df['algorithm'] == algo]
        ax2.plot(algo_data['robot_count'], algo_data['position_convergence_iteration'], 
                color=colors[algo], marker=markers[algo], 
                linewidth=1.5, markersize=4)
    
    ax2.set_ylabel('Iterations')
    ax2.grid(True, alpha=0.3)
    
    # Plot Time vs Robots
    for algo in df['algorithm'].unique():
        if pd.isna(algo):
            continue
        algo_data = df[df['algorithm'] == algo]
        ax3.plot(algo_data['robot_count'], algo_data['position_convergence_time'], 
                color=colors[algo], marker=markers[algo], 
                linewidth=1.5, markersize=4)
    
    ax3.set_xlabel('Number of Robots')
    ax3.set_ylabel('Time (s)')
    ax3.grid(True, alpha=0.3)
    
    # Set x-axis ticks to include start and end points
    ax3.set_xticks(range(5, 16))  # 5 to 15 inclusive
    
    # Add shared legend at the bottom
    fig.legend(legend_lines, legend_labels, loc='lower center', 
               bbox_to_anchor=(0.5, -0.02), ncol=len(legend_labels), 
               fontsize=7, frameon=False)
    
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.08)  # Make room for legend
    plt.savefig('position_convergence_ieee.png', dpi=300, bbox_inches='tight')
    plt.show()
    print("Original plots saved as 'position_convergence_ieee.png'")

def create_normalized_plots(df, colors, markers, legend_override=None):
    """Create plots showing normalized metrics vs robot count"""
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(3.5, 3.9), sharex=True)
    
    # Store line objects for legend
    legend_lines = []
    legend_labels = []
    
    # Plot Communications per Robot vs Robots
    for algo in df['algorithm'].unique():
        if pd.isna(algo):
            continue
        algo_data = df[df['algorithm'] == algo]
        comm_per_robot = algo_data['position_convergence_comm'] / algo_data['robot_count']
        line = ax1.plot(algo_data['robot_count'], comm_per_robot, 
                       color=colors[algo], marker=markers[algo], 
                       linewidth=0.7, markersize=2, label=algo)
        
        # Only add to legend once per algorithm
        if algo not in [label for label in legend_labels]:
            legend_lines.append(line[0])
            display_name = legend_override.get(algo, algo) if legend_override else algo
            legend_labels.append(display_name)
    
    ax1.set_ylabel('Comm. per Robot')
    ax1.grid(True, alpha=0.3)
    
    # Plot Iterations per Robot vs Robots
    for algo in df['algorithm'].unique():
        if pd.isna(algo):
            continue
        algo_data = df[df['algorithm'] == algo]
        iter_per_robot = algo_data['position_convergence_iteration'] / algo_data['robot_count']
        ax2.plot(algo_data['robot_count'], iter_per_robot, 
                color=colors[algo], marker=markers[algo], 
                linewidth=0.7, markersize=2)

    ax2.set_ylabel('Iter. per Robot')
    ax2.grid(True, alpha=0.3)
    
    # Plot Time per Robot vs Robots
    for algo in df['algorithm'].unique():
        if pd.isna(algo):
            continue
        algo_data = df[df['algorithm'] == algo]
        time_per_robot = algo_data['position_convergence_time'] / algo_data['robot_count']
        ax3.plot(algo_data['robot_count'], time_per_robot, 
                color=colors[algo], marker=markers[algo], 
                linewidth=0.7, markersize=2)

    ax3.set_xlabel('Number of Robots')
    ax3.set_ylabel('Time per Robot (s)')
    ax3.grid(True, alpha=0.3)
    
    # Set x-axis ticks to include start and end points
    ax3.set_xticks(range(5, 16))  # 5 to 15 inclusive
    
    # Add shared legend at the bottom
    fig.legend(legend_lines, legend_labels, loc='lower center', 
               bbox_to_anchor=(0.5, -0.08), ncol=len(legend_labels), 
               fontsize=7, frameon=False)
    
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.08)  # Make room for legend
    plt.savefig('scalability.pdf', dpi=300, bbox_inches='tight')
    plt.show()
    print("Normalized plots saved as 'scalability.pdf'")

if __name__ == "__main__":
    main()
