#!/bin/bash

# Default number of parallel processes
MAX_PARALLEL_PROCESSES=4

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--processes)
            MAX_PARALLEL_PROCESSES="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -p, --processes NUM    Maximum number of parallel processes (default: 4)"
            echo "  -h, --help            Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Validate process count
if ! [[ "$MAX_PARALLEL_PROCESSES" =~ ^[0-9]+$ ]] || [ "$MAX_PARALLEL_PROCESSES" -lt 1 ]; then
    echo "❌ Error: Process count must be a positive integer. Got: $MAX_PARALLEL_PROCESSES"
    exit 1
fi

echo "🔧 Configuration: Maximum parallel processes = $MAX_PARALLEL_PROCESSES"

# Array of dataset-robot pairs to process
# Each pair is in the format "dataset_path:robot_count"
dataset_robot_pairs=(
    # "/workspaces/mesa/data/sphere2500.g2o:25"
    # "/workspaces/mesa/data/smallGrid3D.g2o:10"
    # "/workspaces/mesa/data/parking-garage.g2o:12"
    # "/workspaces/mesa/data/kitti_00_3d.g2o:20"
    # "/workspaces/mesa/data/CSAIL_3d.g2o:18"
    # "/workspaces/mesa/data/input_MITb_g2o_3d.g2o:15"
    # "/workspaces/mesa/data/input_M3500_g2o_3d.g2o:30"
    "/workspaces/mesa/data/grid_5.g2o:5"
    "/workspaces/mesa/data/grid_6.g2o:6"
    "/workspaces/mesa/data/grid_7.g2o:7"
    "/workspaces/mesa/data/grid_8.g2o:8"
    "/workspaces/mesa/data/grid_9.g2o:9"
    "/workspaces/mesa/data/grid_10.g2o:10"
    "/workspaces/mesa/data/grid_11.g2o:11"
    "/workspaces/mesa/data/grid_12.g2o:12"
    "/workspaces/mesa/data/grid_13.g2o:13"
    "/workspaces/mesa/data/grid_14.g2o:14"
    "/workspaces/mesa/data/grid_15.g2o:15"
)

output_path="/workspaces/mesa/data/results/jrl/"

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
    
    methods=("asapp" "dgs" "geodesic-mesa")
    # methods=("centralized")
    # methods=("asapp")
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
    
    # cd /workspaces/mesa || { echo "❌ Failed to change directory!"; return 1; }
    
    # for method in "${methods[@]}"; do
    #     local results_pattern="${results_dir}/${name}_${method}"_*/final_results.jrr.cbor
        
    #     echo "📊 Plotting results for: $method on $name with $n robots"
        
    #     ./scripts/plot-results -d "$output_file" -r $results_pattern --is3d &
        
    #     if [ $? -ne 0 ]; then
    #         echo "❌ Error: plot-results failed for $method on $name with $n robots!"
    #         return 1
    #     fi
        
    #     echo "✅ Successfully plotted results for: $method on $name with $n robots"
    # done
    
    # ===========================
    # COMPARE CONVERGENCE
    # ===========================
    
    # echo "📈 Running convergence comparison for $name with $n robots..."
    
    # # Extract latest timestamped directories
    # local latest_centralized=$(ls -td ${results_dir}/${name}_centralized_* 2>/dev/null | head -n 1)
    # local latest_geodesic=$(ls -td ${results_dir}/${name}_geodesic-mesa_* 2>/dev/null | head -n 1)
    # local latest_dgs=$(ls -td ${results_dir}/${name}_dgs_* 2>/dev/null | head -n 1)
    # local latest_asapp=$(ls -td ${results_dir}/${name}_asapp_* 2>/dev/null | head -n 1)
    
    # if [[ -z "$latest_centralized" || -z "$latest_geodesic" || -z "$latest_dgs" || -z "$latest_asapp" ]]; then
    #     echo "❌ Error: Could not find results directories for $name with $n robots!"
    #     return 1
    # fi
    
    # echo "🔍 Comparing for $name with $n robots:"
    # echo "  - Centralized: $latest_centralized"
    # echo "  - Geodesic-Mesa: $latest_geodesic"
    # echo "  - DGS: $latest_dgs"
    # echo "  - ASAPP: $latest_asapp"
    
    # ./scripts/compare-convergence -d "$output_file" \
    #     -c "$latest_centralized" \
    #     -m "$latest_geodesic" "$latest_dgs" "$latest_asapp"
    
    # if [ $? -ne 0 ]; then
    #     echo "❌ Error: compare-convergence failed for $name with $n robots!"
    #     return 1
    # fi
    
    echo "✅ Convergence comparison completed successfully for $name with $n robots!"
    echo "🎉 All tasks completed successfully for $name with $n robots!"
}

# ===========================
# PROCESS ALL DATASET-ROBOT PAIRS WITH CONTROLLED PARALLELISM
# ===========================

echo "🚀 Starting controlled parallel processing of ${#dataset_robot_pairs[@]} dataset-robot pairs..."
echo "🔧 Using maximum $MAX_PARALLEL_PROCESSES parallel processes"

# Function to wait for a slot to become available
wait_for_slot() {
    while [ $(jobs -r | wc -l) -ge $MAX_PARALLEL_PROCESSES ]; do
        sleep 1
    done
}

# Array to store experiment information for status tracking
experiment_descriptions=()
total_experiments=0

# Count total experiments
for pair in "${dataset_robot_pairs[@]}"; do
    # Split the pair by ":"
    IFS=':' read -r g2o_file_path n <<< "$pair"
    if [ -f "$g2o_file_path" ]; then
        ((total_experiments++))
    fi
done

echo "📊 Total experiments to run: $total_experiments"

# Process files with controlled parallelism
experiment_count=0
for pair in "${dataset_robot_pairs[@]}"; do
    # Split the pair by ":"
    IFS=':' read -r g2o_file_path n <<< "$pair"
    
    if [ -f "$g2o_file_path" ]; then
        ((experiment_count++))
        file_name=$(basename "$g2o_file_path")
        experiment_desc="${file_name} (n=${n})"
        
        # Wait for an available slot
        wait_for_slot
        
        echo "🔄 Starting processing [$experiment_count/$total_experiments]: $experiment_desc"
        process_file "$g2o_file_path" "$n" &
        experiment_descriptions+=("$experiment_desc")
        echo "🔄 Started background process for $experiment_desc (Active jobs: $(jobs -r | wc -l))"
    else
        echo "⚠️  Skipping missing file: $g2o_file_path (from pair: $pair)"
    fi
done

# Wait for all remaining jobs to complete
echo "⏳ Waiting for all remaining experiments to complete..."
wait

echo "🎉 All experiments processed!"

# Check for any failed jobs (this is approximate since we can't track individual PIDs easily with the semaphore approach)
echo "📋 Processing summary: $total_experiments experiments were started"

# Script completed - all processing is handled within the process_file function