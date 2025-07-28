#!/bin/bash

# g2o_file_path="/datasets/G2O/sphere2500.g2o"
# g2o_file_path="/datasets/G2O/smallGrid3D.g2o" # x
# g2o_file_path="/datasets/G2O/parking-garage.g2o"
# g2o_file_path="/datasets/G2O/torus3D.g2o" # x
# g2o_file_path="/datasets/G2O/kitti_00_3d.g2o" 
# # g2o_file_path="/datasets/G2O/input_INTEL_g2o_3d.g2o" #TODO: debug x
# g2o_file_path="/datasets/G2O/CSAIL_3d.g2o"
# g2o_file_path="/datasets/G2O/input_M3500_g2o_3d.g2o"
g2o_file_path="/datasets/G2O/torus3D.g2o.init"

output_path="/datasets/G2O/jrl/"

n=5
# g2o_file_path="/datasets/G2O/kitti_00.g2o"

if [ ! -f "$g2o_file_path" ]; then
    echo "Error: File '$g2o_file_path' not found!"
    exit 1
fi
# Extract the filename without path and extension
name=$(basename "$g2o_file_path" .g2o)

# Set the output path and name automatically
# ===========================
# FILE CHECK & SETUP
# ===========================

# Ensure the input file exists
if [ ! -f "$g2o_file_path" ]; then
    echo "❌ Error: File '$g2o_file_path' not found!"
    exit 1
fi

# Extract filename without extension
name=$(basename "$g2o_file_path" .g2o)
output_name="${name}.jrl"
output_file="${output_path}${output_name}"

echo "✅ Processing file: $g2o_file_path"
echo "🔹 Extracted name: $name"
echo "🔹 Output file: $output_file"

# Ensure output directory exists
mkdir -p "$output_path"

# ===========================
# RUN PREPROCESSING
# ===========================

cd /workspaces/src/mesa || { echo "❌ Failed to change directory!"; exit 1; }

echo "🚀 Running g2o-2-mr-jrl conversion..."
./build/experiments/g2o-2-mr-jrl -i "$g2o_file_path" -n "$name" -o "$output_file" -p "$n" > output.txt

# if [ $? -ne 0 ]; then
#     echo "❌ Error: g2o-2-mr-jrl failed!"
#     exit 1
# fi

echo "✅ Conversion successful!"

# ===========================
# RUN DISTRIBUTED BATCHES
# ===========================

cd /workspaces/src/ || { echo "❌ Failed to change directory!"; exit 1; }

methods=("centralized" "geodesic-mesa")
# methods=("centralized")
# methods=("geodesic-mesa")
results_dir="/workspaces/src/mesa/results"

mkdir -p "$results_dir"

for method in "${methods[@]}"; do
    echo "🚀 Running distributed batch: $method"
    cmd="./mesa/build/experiments/run-dist-batch -i \"$output_file\" -m \"$method\" -o \"$results_dir\" --is3d > /workspaces/src/mesa/graph.txt" 
    echo "📝 Running: $cmd"
    eval $cmd


    if [ $? -ne 0 ]; then
        echo "❌ Error: run-dist-batch failed for $method!"
        exit 1
    fi

    echo "✅ Finished batch processing for: $method"
done

# ===========================
# PLOTTING RESULTS
# ===========================

cd /workspaces/src/mesa || { echo "❌ Failed to change directory!"; exit 1; }

for method in "${methods[@]}"; do
    results_pattern="${results_dir}/${name}_${method}"_*/final_results.jrr.cbor
    
    echo "📊 Plotting results for: $method"
    
    ./scripts/plot-results -d "$output_file" -r $results_pattern --is3d &

    if [ $? -ne 0 ]; then
        echo "❌ Error: plot-results failed for $method!"
        exit 1
    fi

    echo "✅ Successfully plotted results for: $method"
done

# ===========================
# COMPARE CONVERGENCE
# ===========================

echo "📈 Running convergence comparison..."

# Extract latest timestamped directories
latest_centralized=$(ls -td ${results_dir}/${name}_centralized_* | head -n 1)
latest_geodesic=$(ls -td ${results_dir}/${name}_geodesic-mesa_* | head -n 1)

if [[ -z "$latest_centralized" || -z "$latest_geodesic" ]]; then
    echo "❌ Error: Could not find results directories!"
    exit 1
fi

echo "🔍 Comparing:"
echo "  - Centralized: $latest_centralized"
echo "  - Geodesic-Mesa: $latest_geodesic"

./scripts/compare-convergence -d "$output_file" \
    -c "$latest_centralized" \
    -m "$latest_geodesic" \
    # -rs 1 -ts 1

if [ $? -ne 0 ]; then
    echo "❌ Error: compare-convergence failed!"
    exit 1
fi

echo "✅ Convergence comparison completed successfully!"

# ===========================
# DONE
# ===========================
echo "🎉 All tasks completed successfully!"