# analyze_relative_change.py

def analyze_file(filename):
    data = []
    with open(filename, 'r') as f:
        for line in f:
            if line.strip() == "" or line.strip().startswith("#"):
                continue  # skip empty lines or comments
            parts = line.strip().split()
            if len(parts) < 2:
                continue
            try:
                step = int(parts[0])
                val2 = float(parts[1])
                data.append((step, val2))
            except ValueError:
                continue  # skip malformed lines

    rel_changes = []
    for i in range(1, len(data)):
        prev_val = data[i-1][1]
        curr_val = data[i][1]
        rel = abs(curr_val - prev_val) / prev_val
        rel_changes.append((data[i][0], rel))

    first_below_0_01 = next((step for step, rel in rel_changes if rel < 0.01), None)
    first_below_0_001 = next((step for step, rel in rel_changes if rel < 0.001), None)

    print("First iteration where relative change < 0.01:", first_below_0_01)
    print("First iteration where relative change < 0.001:", first_below_0_001)

if __name__ == "__main__":
    analyze_file("/workspaces/mesa/data/results/seq/CSAIL_3d_geodesic-mesa_2025-08-03_18-44-06/residual_and_ate.txt")
