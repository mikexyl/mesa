#!/usr/bin/env python3
"""
Script to analyze residual and ATE data to find when APE and ATE reach within 1% of final values.

The script reads a text file with columns:
- Communications count
- Residual 
- Position errors (APE)
- Rotation errors (ATE)
"""

import numpy as np
import argparse
import sys
from pathlib import Path


def analyze_convergence(file_path, threshold_percent=1.0):
    """
    Analyze when APE and ATE reach within threshold_percent of their final values.
    
    Args:
        file_path (str): Path to the residual_and_ate.txt file
        threshold_percent (float): Percentage threshold (default: 1.0 for 1%)
    
    Returns:
        dict: Results containing convergence information
    """
    try:
        # Read the data
        data = np.loadtxt(file_path)
        
        if data.shape[1] != 4:
            raise ValueError(f"Expected 4 columns, got {data.shape[1]}")
        
        communications = data[:, 0]
        residual = data[:, 1]
        ape = data[:, 2]  # Position errors
        ate = data[:, 3]  # Rotation errors
        
        # Get final values (last row)
        final_ape = ape[-1]
        final_ate = ate[-1]
        final_residual = residual[-1]
        
        print(f"Final values:")
        print(f"  Communications: {int(communications[-1])}")
        print(f"  Residual: {final_residual:.6f}")
        print(f"  APE (Position): {final_ape:.6f}")
        print(f"  ATE (Rotation): {final_ate:.6f}")
        print()
        
        # Calculate threshold values
        threshold_factor = threshold_percent / 100.0
        ape_threshold = final_ape * (1 + threshold_factor)
        ate_threshold = final_ate * (1 + threshold_factor)
        
        print(f"Threshold values ({threshold_percent}% above final):")
        print(f"  APE threshold: {ape_threshold:.6f}")
        print(f"  ATE threshold: {ate_threshold:.6f}")
        print()
        
        # Find when APE reaches within threshold
        ape_converged_idx = np.where(ape <= ape_threshold)[0]
        ape_convergence_comm = None
        if len(ape_converged_idx) > 0:
            ape_convergence_comm = int(communications[ape_converged_idx[0]])
        
        # Find when ATE reaches within threshold
        ate_converged_idx = np.where(ate <= ate_threshold)[0]
        ate_convergence_comm = None
        if len(ate_converged_idx) > 0:
            ate_convergence_comm = int(communications[ate_converged_idx[0]])
        
        # Find when both reach within threshold
        both_converged_idx = np.where((ape <= ape_threshold) & (ate <= ate_threshold))[0]
        both_convergence_comm = None
        if len(both_converged_idx) > 0:
            both_convergence_comm = int(communications[both_converged_idx[0]])
        
        # Print results
        print("Convergence analysis:")
        if ape_convergence_comm is not None:
            print(f"  APE reaches within {threshold_percent}% at communication: {ape_convergence_comm}")
        else:
            print(f"  APE never reaches within {threshold_percent}% of final value")
        
        if ate_convergence_comm is not None:
            print(f"  ATE reaches within {threshold_percent}% at communication: {ate_convergence_comm}")
        else:
            print(f"  ATE never reaches within {threshold_percent}% of final value")
        
        if both_convergence_comm is not None:
            print(f"  Both APE and ATE reach within {threshold_percent}% at communication: {both_convergence_comm}")
        else:
            print(f"  Both APE and ATE never simultaneously reach within {threshold_percent}% of final values")
        
        # Calculate percentage of total communications
        total_comm = int(communications[-1])
        if both_convergence_comm is not None:
            percentage = (both_convergence_comm / total_comm) * 100
            print(f"  This represents {percentage:.1f}% of total communications")
        
        return {
            'final_ape': final_ape,
            'final_ate': final_ate,
            'final_residual': final_residual,
            'total_communications': total_comm,
            'ape_convergence': ape_convergence_comm,
            'ate_convergence': ate_convergence_comm,
            'both_convergence': both_convergence_comm,
            'threshold_percent': threshold_percent
        }
        
    except Exception as e:
        print(f"Error analyzing file: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Analyze convergence of APE and ATE in optimization results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python analyze_convergence.py residual_and_ate.txt
  python analyze_convergence.py --threshold 0.5 residual_and_ate.txt
  python analyze_convergence.py data/results/seq/*/residual_and_ate.txt
        """
    )
    
    parser.add_argument(
        'file_path',
        help='Path to the residual_and_ate.txt file'
    )
    
    parser.add_argument(
        '--threshold', '-t',
        type=float,
        default=1.0,
        help='Percentage threshold for convergence (default: 1.0%%)'
    )
    
    args = parser.parse_args()
    
    file_path = Path(args.file_path)
    
    if not file_path.exists():
        print(f"Error: File '{file_path}' does not exist")
        sys.exit(1)
    
    print(f"Analyzing file: {file_path}")
    print(f"Threshold: {args.threshold}%")
    print("=" * 60)
    
    results = analyze_convergence(file_path, args.threshold)
    
    if results is None:
        sys.exit(1)


if __name__ == "__main__":
    main()
