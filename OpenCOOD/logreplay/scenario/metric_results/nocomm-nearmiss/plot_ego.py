import json
import matplotlib.pyplot as plt

# Paths to your two JSON files
file_63 = "/home/po-han/Desktop/Projects/simulation/scenario_runner/tmp_461719.ego_controls.json"
file_86 = "/home/po-han/Desktop/Projects/simulation/scenario_runner/tmp_557219.ego_controls.json"

# Load JSON data
with open(file_63, "r") as f:
    data_63 = json.load(f)
with open(file_86, "r") as f:
    data_86 = json.load(f)

# Extract the dicts
controls_63 = list(data_63.values())[0]
controls_86 = list(data_86.values())[0]

# Global font settings for visibility
plt.rcParams.update({
    "font.size": 20,
    "axes.titlesize": 22,
    "axes.labelsize": 30,
    "legend.fontsize": 20,
    "xtick.labelsize": 22,
    "ytick.labelsize": 22
})

# Create figure
plt.figure(figsize=(12, 7))

# Plot signals (solid = UNCAP, dashed = No-Comm)
line_speed_nc, = plt.plot(controls_86["frames"], controls_86["speed"], "g--", linewidth=3)
line_speed_uc, = plt.plot(controls_63["frames"], controls_63["speed"], "g-", linewidth=3)

line_brake_nc, = plt.plot(controls_86["frames"], controls_86["brake"], "r--", linewidth=3)
line_brake_uc, = plt.plot(controls_63["frames"], controls_63["brake"], "r-", linewidth=3)

line_steer_nc, = plt.plot(controls_86["frames"], controls_86["steer"], "b--", linewidth=3)
line_steer_uc, = plt.plot(controls_63["frames"], controls_63["steer"], "b-", linewidth=3)

# Custom legend (one per color only)
plt.legend(
    [line_speed_uc, line_brake_uc, line_steer_uc],
    ["Speed (x0.05) [m/s]", "Brake", "Steer"],
    loc="upper right"
)

# Formatting
plt.title("Control Signals – No-Comm (dotted) vs UNCAP (solid)")
plt.xlabel("Frame Number")
plt.ylabel("Value")
plt.grid(True, linewidth=1.5, alpha=0.4)
plt.tight_layout()

# Save as high-resolution PDF
plt.savefig(
    "/home/po-han/Desktop/Projects/OpenCOOD/logreplay/scenario/metric_results/control_signals.pdf",
    dpi=300,
    bbox_inches="tight"
)

plt.show()
