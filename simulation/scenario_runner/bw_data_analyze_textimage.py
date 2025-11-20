import json
import matplotlib.pyplot as plt
import numpy as np

# Load your data
with open('/home/po-han/Desktop/Projects/simulation/scenario_runner/bandwidth_test_20_21_10_24_textimage.json', 'r') as f:
    data = json.load(f)

# Extract key metrics
accepted = data['bandwidth_comparison']['accepted_cavs_only']
send_all = data['bandwidth_comparison']['send_to_all_cavs']
savings = data['bandwidth_comparison']['savings']
sim_summary = data['simulation_summary']

# Print key statistics
print("=" * 60)
print("BANDWIDTH SAVINGS SUMMARY")
print("=" * 60)
print(f"\nSimulation Overview:")
print(f"  - Total Ticks: {sim_summary['total_ticks']}")
print(f"  - Total CAVs: {sim_summary['total_cavs_in_simulation']}")
print(f"  - Duration: {sim_summary['total_simulation_timestamps']} timestamp units")
print(f"  - Avg Packet Size: {data['detailed_analysis']['avg_packet_size_bytes']:.1f} bytes")

print(f"\n{'Strategy':<25} {'Total Data (MB)':<20} {'Total Packets':<15} {'Avg/Tick (MB)'}")
print("-" * 80)
print(f"{'UNCAP':<25} {accepted['total_data_sent_mb']:<20.6f} {accepted['total_packets_sent']:<15} {data['detailed_analysis']['avg_data_per_tick_mb']['accepted_only']:.6f}")
print(f"{'UNCAP & w/o SPARE':<25} {send_all['total_data_sent_mb']:<20.6f} {send_all['total_packets_sent']:<15} {data['detailed_analysis']['avg_data_per_tick_mb']['send_to_all']:.6f}")

print(f"\n{'SAVINGS:':<25} {savings['data_saved_mb']:<20.6f} {savings['packets_saved']:<15} {savings['percentage_saved']:.2f}%")

print(f"\nPacket Reduction:")
print(f"  - UNCAP Packets: {accepted['total_packets_sent']}")
print(f"  - UNCAP & w/o SPARE Packets: {send_all['total_packets_sent']}")
print(f"  - Reduction: {savings['packets_saved']} packets ({savings['percentage_saved']:.2f}%)")

print(f"\nBandwidth Efficiency:")
print(f"  - Data saved: {savings['data_saved_mb']*1024:.2f} KB")
print(f"  - Bandwidth reduction: {savings['percentage_saved']:.2f}%")
print(f"  - Average per-tick savings: {(savings['data_saved_mb']/sim_summary['total_ticks'])*1024:.4f} KB/tick")

# Calculate acceptance rate
acceptance_rate = (accepted['total_packets_sent'] / send_all['total_packets_sent']) * 100
print(f"\nCAV Acceptance Rate: {acceptance_rate:.2f}%")
print("=" * 60)

# === Create visualizations ===
fig, axes = plt.subplots(1, 2, figsize=(16, 7))

# === 1. Total Data + Packets Bar Chart (converted to KB) ===
ax1 = axes[0]
strategies = ['UNCAP', 'UNCAP & w/o SPARE']

# Convert from MB → KB
data_kb = [accepted['total_data_sent_mb'] * 1024, send_all['total_data_sent_mb'] * 1024]
packets = [accepted['total_packets_sent'], send_all['total_packets_sent']]
colors = ['#2ecc71', '#e74c3c']

bars = ax1.bar(strategies, data_kb, color=colors, alpha=0.9, edgecolor='black', linewidth=2)

# Remove y-axis completely for a cleaner look
ax1.set_yticks([])
ax1.spines['left'].set_visible(False)
ax1.spines['right'].set_visible(False)
ax1.spines['top'].set_visible(False)
ax1.grid(False)

# Larger tick label font
ax1.tick_params(axis='x', labelsize=20)

# Add KB + packets label above bars
for bar, kb, pkt in zip(bars, data_kb, packets):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 20,
             f'{kb:.1f} KB\n[{pkt} packets]', ha='center', va='bottom',
             fontsize=18, fontweight='bold')

# Add centered savings annotation inside first bar
ax1.text(bars[0].get_x() + bars[0].get_width()/2, data_kb[0] / 2,
         f"{savings['percentage_saved']:.1f}% Total\nBandwidth Saved\n({savings['packets_saved']} packets)",
         ha='center', va='center', fontsize=20, fontweight='bold', color='white',
         bbox=dict(boxstyle='round,pad=0.6', facecolor='#3498db', alpha=0.9))

# === 2. Per-Tick Bandwidth Line Plot (KB) ===
ax2 = axes[1]
ticks = range(len(accepted['data_per_tick_mb']))

ax2.plot(ticks, [x*1024 for x in accepted['data_per_tick_mb']], 
         label='UNCAP', color='#2ecc71', linewidth=3.5, alpha=0.85)
ax2.plot(ticks, [x*1024 for x in send_all['data_per_tick_mb']], 
         label='UNCAP & w/o SPARE', color='#e74c3c', linewidth=3.5, alpha=0.85)

ax2.fill_between(ticks, [x*1024 for x in accepted['data_per_tick_mb']], 
                 [x*1024 for x in send_all['data_per_tick_mb']], 
                 color='#3498db', alpha=0.25, label='Bandwidth Saved')

# Larger axis labels and ticks
ax2.set_xlabel('Simulation Tick', fontsize=20, fontweight='bold')
ax2.set_ylabel('Data per Tick (KB)', fontsize=20, fontweight='bold')
ax2.legend(loc='upper right', fontsize=18)
ax2.grid(alpha=0.3, linestyle='--')
ax2.tick_params(axis='both', labelsize=18)

plt.tight_layout()

# Save as PDF
plt.savefig(
    '/home/po-han/Desktop/Projects/simulation/scenario_runner/bandwidth_comparison_textimage.pdf', 
    dpi=300, bbox_inches='tight', format='pdf'
)
print("\nVisualization saved as PDF: bandwidth_comparison_textimage.pdf")

plt.show()
