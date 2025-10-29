import json
import os
import matplotlib.pyplot as plt

# Path to your JSON distance file (change this to your actual file)
DISTANCE_JSON_PATH = "/home/po-han/Desktop/Projects/OpenCOOD/logreplay/scenario/metric_results/nearmiss/distances-comms.json"

# Output directory for plots
OUTPUT_DIR = "/home/po-han/Desktop/Projects/OpenCOOD/logreplay/scenario/metric_results/nearmiss/comm_dist_plots"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load JSON data
with open(DISTANCE_JSON_PATH, 'r') as f:
    distances = json.load(f)

# distances format: distances[ego_id][other_id][frame] = distance

for ego_id, other_cars in distances.items():
    plt.figure(figsize=(12, 6))
    for other_id, frames_dict in other_cars.items():
        # Convert frame keys and distances to sorted lists
        frames, dists = zip(*sorted((int(frame), dist) for frame, dist in frames_dict.items()))
        plt.plot(frames, dists, label=f"Car {other_id}")

    plt.title(f"Distances from CAV {ego_id} to other vehicles")
    plt.xlabel("Frame Number")
    plt.ylabel("Distance [m]")
    plt.legend(loc='upper right', fontsize='small', ncol=2)
    plt.grid(True)

    # Save figure per ego vehicle
    plt.savefig(os.path.join(OUTPUT_DIR, f"distance_CAV_{ego_id}.png"), dpi=300)
    plt.close()

print(f"Plots saved to {OUTPUT_DIR}")
