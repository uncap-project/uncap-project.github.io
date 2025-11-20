import json
import os
import matplotlib.pyplot as plt

# Path to your JSON distance file
DISTANCE_JSON_PATH = "/home/po-han/Desktop/Projects/OpenCOOD/logreplay/scenario/metric_results/comm-nearmiss-latest/comm-nearmiss-latest.json"

# Output directory for plots
OUTPUT_DIR = "/home/po-han/Desktop/Projects/OpenCOOD/logreplay/scenario/metric_results/comm-nearmiss-latest/dist_plots"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load JSON data
with open(DISTANCE_JSON_PATH, 'r') as f:
    distances = json.load(f)

# Actual IDs in the data
ego_id = "63"
target_id = "79"

# Labels to display in the plot
display_ego = "134"
display_target = "150"

# Check both IDs exist
if ego_id in distances and target_id in distances[ego_id]:
    frames_dict = distances[ego_id][target_id]

    # Convert frame keys and distances to sorted lists
    frames, dists = zip(*sorted((int(frame), dist) for frame, dist in frames_dict.items()))

    # Plotting
    plt.figure(figsize=(12, 6))
    plt.plot(frames, dists, label=f"{display_ego} → {display_target}")

    plt.title(f"Distance from CAV {display_ego} to CAV {display_target}")
    plt.xlabel("Frame Number")
    plt.ylabel("Distance [m]")
    plt.legend(loc='upper right')
    plt.grid(True)

    # Y-axis starts at 0 with increments of 10
    max_dist = max(dists)
    upper_limit = int((max_dist + 9) // 10) * 10
    plt.ylim(0, upper_limit)
    plt.yticks(range(0, upper_limit + 1, 10))

    plt.savefig(os.path.join(OUTPUT_DIR, f"distance_{ego_id}_to_{target_id}.png"), dpi=300)
    plt.close()

    print(f"Plot saved: distance_{ego_id}_to_{target_id}.png")
else:
    print(f"No distance data found between CAV {ego_id} and CAV {target_id}")
