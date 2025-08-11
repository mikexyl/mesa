#!/usr/bin/env python3
"""
Script to manually input new method statistics and add them to existing analysis.
This allows you to add new experimental results without having the full result folders.
"""

import pandas as pd
import os

def input_new_method_stats():
    """Interactive function to input new method statistics."""
    
    print("=" * 60)
    print("Manual Input for New Method Statistics")
    print("=" * 60)
    print()
    
    # Load existing data if available
    try:
        existing_df = pd.read_csv('enhanced_convergence_analysis.csv')
        print(f"Loaded existing data with {len(existing_df)} experiments")
        print(f"Existing algorithms: {sorted(existing_df['algorithm'].unique())}")
        print()
    except FileNotFoundError:
        print("No existing enhanced_convergence_analysis.csv found.")
        print("Creating new dataset...")
        existing_df = pd.DataFrame()
    
    new_entries = []
    
    while True:
        print("\nEnter new method statistics (press Enter with empty algorithm name to finish):")
        print("-" * 50)
        
        # Get basic experiment info
        algorithm = input("Algorithm name: ").strip()
        if not algorithm:
            break
            
        grid_size = input("Grid size (e.g., '15_15'): ").strip()
        if not grid_size:
            print("Grid size is required!")
            continue
            
        try:
            robot_count = int(input("Number of robots (e.g., 15): ").strip())
        except ValueError:
            print("Invalid robot count!")
            continue
        
        # Get convergence statistics
        print("\nConvergence Statistics:")
        try:
            total_comm = float(input("Total communications: ").strip())
            final_pos_error = float(input("Final position error: ").strip())
            final_rot_error = float(input("Final rotation error: ").strip())
            
            # Position convergence data
            pos_conv_comm = input("Position convergence communications (or 'final' to use total): ").strip()
            if pos_conv_comm.lower() == 'final':
                pos_conv_comm = total_comm
            else:
                pos_conv_comm = float(pos_conv_comm)
                
            pos_conv_iter = input("Position convergence iterations (or 'final' to use total): ").strip()
            if pos_conv_iter.lower() == 'final':
                pos_conv_iter = float(input("Total iterations: ").strip())
            else:
                pos_conv_iter = float(pos_conv_iter)
                
            pos_conv_time = input("Position convergence time in seconds (or 'final' to use total): ").strip()
            if pos_conv_time.lower() == 'final':
                pos_conv_time = float(input("Total time in seconds: ").strip())
            else:
                pos_conv_time = float(pos_conv_time)
                
        except ValueError:
            print("Invalid numeric input! Skipping this entry.")
            continue
        
        # Calculate ratios
        pos_conv_ratio = pos_conv_comm / total_comm if total_comm > 0 else 0
        
        # Create experiment name
        experiment_name = f"grid_{grid_size}_{algorithm}_manual_input"
        
        # Create new entry
        new_entry = {
            'file_path': f'manual_input/{experiment_name}/residual_and_ate.txt',
            'total_communications': total_comm,
            'final_position_error': final_pos_error,
            'final_rotation_error': final_rot_error,
            'position_convergence_comm': pos_conv_comm,
            'rotation_convergence_comm': pos_conv_comm,  # Assume same as position
            'position_convergence_ratio': pos_conv_ratio,
            'rotation_convergence_ratio': pos_conv_ratio,  # Assume same as position
            'total_iterations': pos_conv_iter,  # This will be updated later if needed
            'experiment_name': experiment_name,
            'algorithm': algorithm,
            'grid_size': grid_size,
            'robot_count': robot_count,
            'position_convergence_iteration': pos_conv_iter,
            'position_convergence_time': pos_conv_time,
            'rotation_convergence_iteration': pos_conv_iter,  # Assume same as position
            'rotation_convergence_time': pos_conv_time  # Assume same as position
        }
        
        new_entries.append(new_entry)
        
        print(f"\nAdded entry for {algorithm} with {robot_count} robots:")
        print(f"  Communications: {pos_conv_comm:.0f} / {total_comm:.0f}")
        print(f"  Iterations: {pos_conv_iter:.0f}")
        print(f"  Time: {pos_conv_time:.1f}s")
        print(f"  Final position error: {final_pos_error:.6f}")
        
        continue_input = input("\nAdd another entry? (y/N): ").strip().lower()
        if continue_input != 'y':
            break
    
    if not new_entries:
        print("No new entries added.")
        return
    
    # Convert to DataFrame
    new_df = pd.DataFrame(new_entries)
    
    # Combine with existing data
    if len(existing_df) > 0:
        # Ensure columns match
        all_columns = set(existing_df.columns) | set(new_df.columns)
        for col in all_columns:
            if col not in existing_df.columns:
                existing_df[col] = None
            if col not in new_df.columns:
                new_df[col] = None
        
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = new_df
    
    # Save updated data
    combined_df.to_csv('enhanced_convergence_analysis.csv', index=False)
    
    print(f"\nSuccessfully added {len(new_entries)} new entries!")
    print(f"Updated dataset now has {len(combined_df)} total experiments")
    print("Saved to: enhanced_convergence_analysis.csv")
    
    # Also update the summary files
    update_summary_files(combined_df)

def update_summary_files(df):
    """Update summary files with the new data."""
    
    # Update position convergence summary
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
    summary_df.to_csv('position_convergence_summary.csv', index=False)
    print("Updated: position_convergence_summary.csv")

def show_template():
    """Show a template for bulk data entry."""
    
    print("\nTemplate for bulk data entry (CSV format):")
    print("=" * 60)
    print("algorithm,grid_size,robot_count,total_communications,final_position_error,final_rotation_error,position_convergence_comm,position_convergence_iter,position_convergence_time")
    print("new_algorithm,15_15,15,9000,0.02,0.01,8500,850,600.5")
    print("new_algorithm,14_14,14,8000,0.025,0.012,7500,750,550.2")
    print("# Use 'final' for convergence values to use total values")
    print("# Example: algorithm,grid_size,robot_count,total_comm,final_pos_err,final_rot_err,final,final,final")

def load_from_csv():
    """Load data from a CSV file."""
    
    csv_file = "raido_nr.csv"
    if not os.path.exists(csv_file):
        print(f"File {csv_file} not found!")
        return
    
    try:
        new_data = pd.read_csv(csv_file)
        required_cols = ['algorithm', 'grid_size', 'robot_count', 'total_communications', 
                        'final_position_error', 'final_rotation_error']
        
        if not all(col in new_data.columns for col in required_cols):
            print(f"CSV must contain columns: {required_cols}")
            return
        
        # Load existing data
        try:
            existing_df = pd.read_csv('enhanced_convergence_analysis.csv')
        except FileNotFoundError:
            existing_df = pd.DataFrame()
        
        # Process new data
        processed_entries = []
        for _, row in new_data.iterrows():
            # Handle 'final' values
            pos_conv_comm = row['total_communications'] if str(row.get('position_convergence_comm', '')).lower() == 'final' else row.get('position_convergence_comm', row['total_communications'])
            pos_conv_iter = row.get('position_convergence_iter', pos_conv_comm)
            pos_conv_time = row.get('position_convergence_time', 500.0)  # Default time
            
            if str(pos_conv_iter).lower() == 'final':
                pos_conv_iter = pos_conv_comm
            if str(pos_conv_time).lower() == 'final':
                pos_conv_time = 500.0  # You'll need to provide this
            
            pos_conv_ratio = pos_conv_comm / row['total_communications'] if row['total_communications'] > 0 else 0
            
            experiment_name = f"grid_{row['grid_size']}_{row['algorithm']}_manual_input"
            
            entry = {
                'file_path': f'manual_input/{experiment_name}/residual_and_ate.txt',
                'total_communications': row['total_communications'],
                'final_position_error': row['final_position_error'],
                'final_rotation_error': row['final_rotation_error'],
                'position_convergence_comm': pos_conv_comm,
                'rotation_convergence_comm': pos_conv_comm,
                'position_convergence_ratio': pos_conv_ratio,
                'rotation_convergence_ratio': pos_conv_ratio,
                'total_iterations': pos_conv_iter,
                'experiment_name': experiment_name,
                'algorithm': row['algorithm'],
                'grid_size': row['grid_size'],
                'robot_count': row['robot_count'],
                'position_convergence_iteration': pos_conv_iter,
                'position_convergence_time': pos_conv_time,
                'rotation_convergence_iteration': pos_conv_iter,
                'rotation_convergence_time': pos_conv_time
            }
            processed_entries.append(entry)
        
        # Combine and save
        new_df = pd.DataFrame(processed_entries)
        if len(existing_df) > 0:
            all_columns = set(existing_df.columns) | set(new_df.columns)
            for col in all_columns:
                if col not in existing_df.columns:
                    existing_df[col] = None
                if col not in new_df.columns:
                    new_df[col] = None
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df
        
        combined_df.to_csv('enhanced_convergence_analysis.csv', index=False)
        update_summary_files(combined_df)
        
        print(f"Successfully loaded {len(processed_entries)} entries from {csv_file}")
        
    except Exception as e:
        print(f"Error loading CSV: {e}")

def main():
    print("Manual Method Statistics Input Tool")
    print("=" * 40)
    print("1. Interactive input")
    print("2. Load from CSV file")
    print("3. Show CSV template")
    print("4. Exit")
    
    while True:
        choice = input("\nChoose option (1-4): ").strip()
        
        if choice == '1':
            input_new_method_stats()
        elif choice == '2':
            load_from_csv()
        elif choice == '3':
            show_template()
        elif choice == '4':
            break
        else:
            print("Invalid choice!")

if __name__ == "__main__":
    main()
