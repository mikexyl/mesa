#!/bin/bash

# Array of g2o files to process
g2o_files=(
    # "/workspaces/mesa/data/sphere2500.g2o"
    # "/workspaces/mesa/data/smallGrid3D.g2o"
    # "/workspaces/mesa/data/parking-garage.g2o"
    # "/workspaces/mesa/data/kitti_00_3d.g2o"
    # "/workspaces/mesa/data/CSAIL_3d.g2o"
    # "/workspaces/mesa/data/input_MITb_g2o_3d.g2o"
    # "/workspaces/mesa/data/input_M3500_g2o_3d.g2o"
    "/workspaces/mesa/data/torus3D.g2o"
)

output_path="/workspaces/mesa/data/results/jrl/"
n_values=(14 15)  # List of robot numbers to test

# Function to process a single file with a specific number of robots
process_file() {
    local g2o_file_path="$1"
    local n="$2"
    
    # ===========================
    # FILE CHECK & SETUP
    # ===========================
    
    # Ensure the input file exists
    if [ ! -f "$g2o_file_path" ]; then
        echo "❌ Error: File '$g2o_file_path' not found!"
        return 1
    fi
    
    # Extract filename without extension
    local name=$(basename "$g2o_file_path" .g2o)_$n
    local output_name="${name}.jrl"
    local output_file="${output_path}${output_name}"
    
    echo "✅ Processing file: $g2o_file_path with $n robots"
    echo "🔹 Extracted name: $name"
    echo "🔹 Output file: $output_file"
    
    # Ensure output directory exists
    mkdir -p "$output_path"
    
    # ===========================
    # RUN PREPROCESSING
    # ===========================
    
    cd /workspaces/mesa || { echo "❌ Failed to change directory!"; return 1; }
    
    echo "🚀 Running g2o-2-mr-jrl conversion for $name with $n robots..."
    ./build/experiments/g2o-2-mr-jrl -i "$g2o_file_path" -n "$name" -o "$output_file" -p "$n" > "output_${name}_${n}.txt"

    if [ $? -ne 0 ]; then
        echo "❌ Error: g2o-2-mr-jrl failed for $name with $n robots!"
        return 1
    fi
    
    echo "✅ Conversion successful for $name with $n robots!"
    
    # ===========================
    # RUN DISTRIBUTED BATCHES
    # ===========================
    
    cd /workspaces/ || { echo "❌ Failed to change directory!"; return 1; }
    
    methods=("centralized" "geodesic-mesa" "dgs" "asapp")
    results_dir="/workspaces/mesa/data/results/seq"
    
    mkdir -p "$results_dir"
    
    # Array to store background process PIDs for this file
    local method_pids=()
    
    for method in "${methods[@]}"; do
        echo "🚀 Starting distributed batch: $method for $name with $n robots"
        local cmd="./mesa/build/experiments/run-dist-batch -i \"$output_file\" -m \"$method\" -o \"$results_dir\" --is3d > /workspaces/mesa/graph_${name}_${n}_${method}.txt"
        echo "📝 Running: $cmd"
        
        # Run command in background and store PID
        eval $cmd &
        method_pids+=($!)
        
        echo "🔄 Started background process for $method on $name with $n robots (PID: ${method_pids[-1]})"
    done
    
    # Wait for all methods for this file to complete
    echo "⏳ Waiting for all methods to complete for $name with $n robots..."
    local failed_methods=()
    
    for i in "${!method_pids[@]}"; do
        local method="${methods[$i]}"
        local pid="${method_pids[$i]}"
        
        echo "⏳ Waiting for $method on $name with $n robots (PID: $pid)..."
        if wait $pid; then
            echo "✅ Finished batch processing for: $method on $name with $n robots"
        else
            echo "❌ Error: run-dist-batch failed for $method on $name with $n robots!"
            failed_methods+=("$method")
        fi
    done
    
    # Check if any methods failed
    if [ ${#failed_methods[@]} -ne 0 ]; then
        echo "❌ The following methods failed for $name with $n robots: ${failed_methods[*]}"
        return 1
    fi
    
    echo "✅ All batch processing completed successfully for $name with $n robots!"
    
    # ===========================
    # PLOTTING RESULTS
    # ===========================
    
    cd /workspaces/mesa || { echo "❌ Failed to change directory!"; return 1; }
    
    for method in "${methods[@]}"; do
        local results_pattern="${results_dir}/${name}_${method}"_*/final_results.jrr.cbor
        
        echo "📊 Plotting results for: $method on $name with $n robots"
        
        ./scripts/plot-results -d "$output_file" -r $results_pattern --is3d &
        
        if [ $? -ne 0 ]; then
            echo "❌ Error: plot-results failed for $method on $name with $n robots!"
            return 1
        fi
        
        echo "✅ Successfully plotted results for: $method on $name with $n robots"
    done
    
    # ===========================
    # COMPARE CONVERGENCE
    # ===========================
    
    echo "📈 Running convergence comparison for $name with $n robots..."
    
    # Extract latest timestamped directories
    local latest_centralized=$(ls -td ${results_dir}/${name}_centralized_* 2>/dev/null | head -n 1)
    local latest_geodesic=$(ls -td ${results_dir}/${name}_geodesic-mesa_* 2>/dev/null | head -n 1)
    local latest_dgs=$(ls -td ${results_dir}/${name}_dgs_* 2>/dev/null | head -n 1)
    local latest_asapp=$(ls -td ${results_dir}/${name}_asapp_* 2>/dev/null | head -n 1)
    
    if [[ -z "$latest_centralized" || -z "$latest_geodesic" || -z "$latest_dgs" || -z "$latest_asapp" ]]; then
        echo "❌ Error: Could not find results directories for $name with $n robots!"
        return 1
    fi
    
    echo "🔍 Comparing for $name with $n robots:"
    echo "  - Centralized: $latest_centralized"
    echo "  - Geodesic-Mesa: $latest_geodesic"
    echo "  - DGS: $latest_dgs"
    echo "  - ASAPP: $latest_asapp"
    
    ./scripts/compare-convergence -d "$output_file" \
        -c "$latest_centralized" \
        -m "$latest_geodesic" "$latest_dgs" "$latest_asapp"
    
    if [ $? -ne 0 ]; then
        echo "❌ Error: compare-convergence failed for $name with $n robots!"
        return 1
    fi
    
    echo "✅ Convergence comparison completed successfully for $name with $n robots!"
    echo "🎉 All tasks completed successfully for $name with $n robots!"
}

# ===========================
# PROCESS ALL FILES AND ROBOT COUNTS IN PARALLEL
# ===========================

echo "🚀 Starting parallel processing of ${#g2o_files[@]} files with ${#n_values[@]} robot configurations..."

# Array to store background process PIDs for each file-robot combination
experiment_pids=()
experiment_descriptions=()

for g2o_file_path in "${g2o_files[@]}"; do
    if [ -f "$g2o_file_path" ]; then
        for n in "${n_values[@]}"; do
            file_name=$(basename "$g2o_file_path")
            experiment_desc="${file_name} (n=${n})"
            echo "🔄 Starting processing for: $experiment_desc"
            process_file "$g2o_file_path" "$n" &
            experiment_pids+=($!)
            experiment_descriptions+=("$experiment_desc")
            echo "🔄 Started background process for $experiment_desc (PID: ${experiment_pids[-1]})"
        done
    else
        echo "⚠️  Skipping missing file: $g2o_file_path"
    fi
done

# Wait for all experiments to complete
echo "⏳ Waiting for all experiments to complete..."
failed_experiments=()

for i in "${!experiment_pids[@]}"; do
    experiment_desc="${experiment_descriptions[$i]}"
    pid="${experiment_pids[$i]}"
    
    echo "⏳ Waiting for $experiment_desc (PID: $pid)..."
    if wait $pid; then
        echo "✅ Completed processing for: $experiment_desc"
    else
        echo "❌ Error: Processing failed for $experiment_desc!"
        failed_experiments+=("$experiment_desc")
    fi
done

# Final status report
if [ ${#failed_experiments[@]} -ne 0 ]; then
    echo "❌ The following experiments failed processing:"
    for failed in "${failed_experiments[@]}"; do
        echo "   - $failed"
    done
    exit 1
fi

echo "🎉 All experiments processed successfully!"

# Script completed - all processing is handled within the process_file function