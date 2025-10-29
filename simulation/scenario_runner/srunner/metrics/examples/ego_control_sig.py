#!/usr/bin/env python3
# Copyright (c) 2020 Computer Vision Center (CVC) at the Universitat Autonoma de
# Barcelona (UAB).
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.
"""
Metric that plots brake, speed and steering signals over time
for every ego CAV.
"""
import json
import os
import math
from collections import defaultdict
import matplotlib.pyplot as plt
import random
from srunner.metrics.examples.basic_metric import BasicMetric

class EgoControlsPlot(BasicMetric):
    """
    Metric class EgoControlsPlot
    """
    def _create_metric(self, town_map, log, criteria):
        """
        Collects vehicle-control data (speed, brake, steer) for every
        ego vehicle and dumps a JSON file plus one figure per ego.
        """
        self._recorder = f"tmp_{random.randint(0, 999999):06d}.log"
        ego_ids = log.get_actor_ids_with_role_name("hero")
        if not ego_ids:
            print("[EgoControlsPlot] No ego vehicles found.")
            return

        # Nested dict: ego_id -> "speed"/"brake"/"steer" -> [value, ...]
        controls = defaultdict(lambda: defaultdict(list))

        for ego_id in ego_ids:
            if not(ego_id == 63 or ego_id==86):
                continue
            first, last = log.get_actor_alive_frames(ego_id)
            frames = list(range(first, last + 1))

            prev_yaw = None

            for frame in frames:
                ctrl = log.get_vehicle_control(ego_id, frame)
                if ctrl is None:
                    continue

                velocity = log.get_actor_velocity(ego_id, frame)
                transform = log.get_actor_transform(ego_id, frame)

                controls[ego_id]["frames"].append(frame)

                # Brake signal
                if hasattr(ctrl, 'brake') and ctrl.brake is not None:
                    controls[ego_id]["brake"].append(ctrl.brake)
                else:
                    controls[ego_id]["brake"].append(0.0)

                # Speed (m/s from velocity vector)
                if velocity is not None:
                    current_speed = math.sqrt(
                        velocity.x**2 + velocity.y**2 + velocity.z**2
                    )/0.05
                    # current_speed = velocity.length()
                    # print(current_speed)
                    controls[ego_id]["speed"].append(current_speed)
                else:
                    controls[ego_id]["speed"].append(0.0)

                # Steering from yaw changes
                if transform is not None and prev_yaw is not None:
                    current_yaw = math.radians(transform.rotation.yaw)
                    yaw_diff = current_yaw - prev_yaw

                    # Handle angle wraparound
                    if yaw_diff > math.pi:
                        yaw_diff -= 2 * math.pi
                    elif yaw_diff < -math.pi:
                        yaw_diff += 2 * math.pi

                    # Convert to steering signal (-1 to 1)
                    steer = max(-1.0, min(1.0, yaw_diff * 10.0))
                    controls[ego_id]["steer"].append(steer)
                else:
                    controls[ego_id]["steer"].append(0.0)

                # Update previous yaw
                if transform is not None:
                    prev_yaw = math.radians(transform.rotation.yaw)

        # Save JSON
        out_file = os.path.splitext(self._recorder)[0] + ".ego_controls.json"
        with open(out_file, "w") as f:
            json.dump(controls, f, indent=2)
        print(f"[EgoControlsPlot] Saved -> {out_file}")

        # Plot results
        for ego_id, data in controls.items():
            frames = data["frames"]
            plt.figure(figsize=(10, 6))
            plt.plot(frames, data["speed"], label="Speed (m/s)", color="g")
            plt.plot(frames, data["brake"], label="Brake", color="r")
            plt.plot(frames, data["steer"], label="Steer", color="b")
            plt.title(f"Control signals – ego vehicle {ego_id}")
            plt.xlabel("Frame")
            plt.ylabel("Value")
            plt.legend()
            plt.grid(True)
            plt.tight_layout()
            plt.show()
