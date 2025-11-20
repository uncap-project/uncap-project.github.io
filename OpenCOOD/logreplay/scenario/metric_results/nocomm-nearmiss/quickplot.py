import json
import os
import matplotlib.pyplot as plt

# Paths to your JSON files
PATH_COMMS = "/home/po-han/Desktop/Projects/OpenCOOD/logreplay/scenario/metric_results/tmp_471155.distance_between_vehicles.json"
PATH_NO_COMMS = "/home/po-han/Desktop/Projects/OpenCOOD/logreplay/scenario/metric_results/tmp_970868.distance_between_vehicles.json"

# Output directory
OUTPUT_DIR = "/home/po-han/Desktop/Projects/OpenCOOD/logreplay/scenario/metric_results/nearmiss/comm_vs_nocomm"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_distance_data(path, ego_id, target_id):
    with open(path, 'r') as f:
        data = json.load(f)
    if ego_id in data and target_id in data[ego_id]:
        frames_dict = data[ego_id][target_id]
        frames, dists = zip(*sorted((int(frame), dist) for frame, dist in frames_dict.items()))
        return frames, dists
    else:
        print(f"No distance data found between {ego_id} and {target_id} in {path}")
        return None, None

# Load comms data (UNCAP)
frames_comms, dists_comms = load_distance_data(PATH_COMMS, "63", "79")

# Load No-Comm data
frames_no_comms, dists_no_comms = load_distance_data(PATH_NO_COMMS, "86", "102")

# Global font and style settings (match second example)
plt.rcParams.update({
    "font.size": 20,         # base font size
    "axes.titlesize": 22,    # title size
    "axes.labelsize": 30,    # x/y label size
    "legend.fontsize": 20,   # legend size
    "xtick.labelsize": 22,   # x tick size
    "ytick.labelsize": 22    # y tick size
})

# Plot
plt.figure(figsize=(12, 6))

# Plot No-Comm first (dashed)
if frames_no_comms:
    line_no_comms, = plt.plot(
        frames_no_comms, dists_no_comms,
        color="#CC5500", linewidth=3, linestyle="--", label="No-Comm"
    )

# Plot UNCAP second (solid)
if frames_comms:
    line_uncap, = plt.plot(
        frames_comms, dists_comms,
        color="#CC5500", linewidth=3, linestyle="-", label="UNCAP"
    )

# Labels and title formatting (match second script)
plt.title("Vehicle Distance Margin - No-Comm vs UNCAP")
plt.xlabel("Frame Number")
plt.ylabel("Distance [m]")

# Axes limits and ticks
plt.xlim(0, 100)
plt.xticks(range(0, 101, 20))
plt.ylim(0, 60)
plt.yticks(range(0, 61, 10))

# Legend: No-Comm on top
plt.legend([line_no_comms, line_uncap], ["No-Comm", "UNCAP"], loc="upper right")

# Grid and layout
plt.grid(True, linestyle="--", linewidth=1.5, alpha=0.5)
plt.tight_layout()

# Save PNG and PDF
output_base = os.path.join(OUTPUT_DIR, "distance_comms_vs_nocomms")
plt.savefig(f"{output_base}.png", dpi=300, bbox_inches="tight")
plt.savefig(f"{output_base}.pdf", dpi=300, bbox_inches="tight")
plt.close()

print(f"Plots saved:\n - {output_base}.png\n - {output_base}.pdf")
