#!/usr/bin/env python
"""
Script to interpret and plot Time To Collision data from the JSON output.
"""
import json
import matplotlib.pyplot as plt
import numpy as np

def load_ttc_data(json_file_path):
    """Load TTC data from JSON file."""
    with open(json_file_path, 'r') as f:
        data = json.load(f)
    return data

def plot_ttc_for_vehicles(json_file_path, vehicle_1_id, vehicle_2_id):
    """
    Plot Time To Collision between two specific vehicles.
    
    Args:
        json_file_path: Path to the TTC JSON file
        vehicle_1_id: ID of first vehicle (as string or int)
        vehicle_2_id: ID of second vehicle (as string or int)
    """
    # Convert to strings (JSON keys are strings)
    v1_id = str(vehicle_1_id)
    v2_id = str(vehicle_2_id)
    
    # Load data
    data = load_ttc_data(json_file_path)
    ttc_pairs = data["ttc_per_vehicle_pair"]
    
    plt.figure(figsize=(12, 8))
    
    # Check if v1 -> v2 relationship exists (v1 is ego, v2 is other)
    if v1_id in ttc_pairs and v2_id in ttc_pairs[v1_id]:
        frame_data = ttc_pairs[v1_id][v2_id]
        frames = [int(f) for f in frame_data.keys()]
        ttc_values = [frame_data[str(f)] for f in frames]
        
        # Sort by frame number
        sorted_data = sorted(zip(frames, ttc_values))
        frames, ttc_values = zip(*sorted_data)
        
        plt.plot(frames, ttc_values, 'b-o', linewidth=2, markersize=4,
                label=f'Vehicle {v1_id} (ego) → Vehicle {v2_id}', alpha=0.8)
        print(f"Found TTC data: Vehicle {v1_id} → Vehicle {v2_id}")
        print(f"  Frames: {min(frames)} to {max(frames)}")
        print(f"  Min TTC: {min(ttc_values):.2f}s")
        print(f"  Mean TTC: {np.mean(ttc_values):.2f}s")
    
    # Check if v2 -> v1 relationship exists (v2 is ego, v1 is other)
    if v2_id in ttc_pairs and v1_id in ttc_pairs[v2_id]:
        frame_data = ttc_pairs[v2_id][v1_id]
        frames = [int(f) for f in frame_data.keys()]
        ttc_values = [frame_data[str(f)] for f in frames]
        
        # Sort by frame number
        sorted_data = sorted(zip(frames, ttc_values))
        frames, ttc_values = zip(*sorted_data)
        
        plt.plot(frames, ttc_values, 'r-s', linewidth=2, markersize=4,
                label=f'Vehicle {v2_id} (ego) → Vehicle {v1_id}', alpha=0.8)
        print(f"Found TTC data: Vehicle {v2_id} → Vehicle {v1_id}")
        print(f"  Frames: {min(frames)} to {max(frames)}")
        print(f"  Min TTC: {min(ttc_values):.2f}s")
        print(f"  Mean TTC: {np.mean(ttc_values):.2f}s")
    
    # Add safety thresholds
    plt.axhline(y=3.0, color='orange', linestyle='--', alpha=0.7,
               label='Warning threshold (3s)')
    plt.axhline(y=1.5, color='red', linestyle='--', alpha=0.7,
               label='Critical threshold (1.5s)')
    
    plt.xlabel('Frame Number')
    plt.ylabel('Time To Collision (seconds)')
    plt.title(f'Time To Collision: Vehicles {vehicle_1_id} and {vehicle_2_id}')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Check if no data was found
    if not plt.gca().lines:
        plt.text(0.5, 0.5, f'No TTC data found between vehicles {vehicle_1_id} and {vehicle_2_id}',
                horizontalalignment='center', verticalalignment='center',
                transform=plt.gca().transAxes, fontsize=14, color='red')
        print(f"No TTC data found between vehicles {vehicle_1_id} and {vehicle_2_id}")
    
    plt.show()

def explore_ttc_data(json_file_path):
    """
    Explore the structure of TTC data to understand available vehicle pairs.
    """
    data = load_ttc_data(json_file_path)
    ttc_pairs = data["ttc_per_vehicle_pair"]
    
    print("=== TTC Data Structure ===")
    print(f"Parameters used: {data.get('parameters', {})}")
    print("\nAvailable ego vehicles and their target vehicles:")
    
    for ego_id, targets in ttc_pairs.items():
        print(f"\nEgo Vehicle {ego_id}:")
        for target_id, frame_data in targets.items():
            num_frames = len(frame_data)
            if num_frames > 0:
                ttc_values = list(frame_data.values())
                min_ttc = min(ttc_values)
                print(f"  → Target {target_id}: {num_frames} frames, min TTC = {min_ttc:.2f}s")
    
    # Show minimum TTC per frame data
    min_ttc_data = data.get("min_ttc_per_frame", {})
    if min_ttc_data:
        print("\nMinimum TTC per frame available for ego vehicles:")
        for ego_id, frame_data in min_ttc_data.items():
            print(f"  Ego {ego_id}: {len(frame_data)} frames with minimum TTC data")

def plot_minimum_ttc_timeline(json_file_path, ego_vehicle_id):
    """
    Plot the minimum TTC timeline for a specific ego vehicle.
    """
    ego_id = str(ego_vehicle_id)
    data = load_ttc_data(json_file_path)
    min_ttc_data = data.get("min_ttc_per_frame", {})
    
    if ego_id not in min_ttc_data:
        print(f"No minimum TTC data found for ego vehicle {ego_vehicle_id}")
        return
    
    frame_data = min_ttc_data[ego_id]
    frames = [int(f) for f in frame_data.keys()]
    min_ttc_values = [frame_data[str(f)] for f in frames]
    
    # Sort by frame number
    sorted_data = sorted(zip(frames, min_ttc_values))
    frames, min_ttc_values = zip(*sorted_data)
    
    plt.figure(figsize=(12, 6))
    plt.plot(frames, min_ttc_values, 'b-', linewidth=2, label=f'Min TTC for Ego {ego_vehicle_id}')
    
    # Add safety thresholds
    plt.axhline(y=3.0, color='orange', linestyle='--', alpha=0.7,
               label='Warning threshold (3s)')
    plt.axhline(y=1.5, color='red', linestyle='--', alpha=0.7,
               label='Critical threshold (1.5s)')
    
    plt.xlabel('Frame Number')
    plt.ylabel('Minimum Time To Collision (seconds)')
    plt.title(f'Minimum TTC Timeline for Ego Vehicle {ego_vehicle_id}')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
    
    print(f"Minimum TTC Statistics for Ego Vehicle {ego_vehicle_id}:")
    print(f"  Overall minimum: {min(min_ttc_values):.2f}s")
    print(f"  Mean minimum: {np.mean(min_ttc_values):.2f}s")
    print(f"  Critical frames (≤1.5s): {sum(1 for ttc in min_ttc_values if ttc <= 1.5)}")
    print(f"  Warning frames (1.5s-3.0s): {sum(1 for ttc in min_ttc_values if 1.5 < ttc <= 3.0)}")

# Example usage
if __name__ == "__main__":
    # Replace with your actual JSON file path
    json_file = "/home/po-han/Desktop/Projects/OpenCOOD/logreplay/scenario/metric_results/tmp_798332.time_to_collision.json"
    
    # Explore the data structure first
    print("Step 1: Exploring TTC data structure...")
    explore_ttc_data(json_file)
    
    print("\n" + "="*50)
    print("Step 2: Plotting TTC between vehicles 63 and 79...")
    # Plot TTC between vehicles 63 and 79
    plot_ttc_for_vehicles(json_file, 63, 79)
    
    print("\n" + "="*50)
    print("Step 3: Plotting minimum TTC timeline...")
    # If 63 or 79 is an ego vehicle, plot its minimum TTC timeline
    plot_minimum_ttc_timeline(json_file, 63)
    plot_minimum_ttc_timeline(json_file, 79)