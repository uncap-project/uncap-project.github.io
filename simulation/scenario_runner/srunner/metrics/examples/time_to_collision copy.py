"""
Metric that estimates the Time-To-Collision (TTC) between every ego vehicle
and every other vehicle in the simulation.
"""

import json
import math
import os
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np
import random
from srunner.metrics.examples.basic_metric import BasicMetric


class TimeToCollision(BasicMetric):
    """
    Metric class TimeToCollision
    """

    def _create_metric(self, town_map, log, criteria):
        """
        Computes TTC for each ego vs every other car and dumps
        <recorder>.time_to_collision.json
        """
        self._recorder = f"tmp_{random.randint(0, 999999):06d}.log"

        ego_ids = log.get_actor_ids_with_role_name("hero")
        other_car_ids = [
            aid for aid in log.get_actor_ids_with_type_id("vehicle.*")
            if aid not in ego_ids
        ]

        if not ego_ids or not other_car_ids:
            print("[TimeToCollision] No ego / no other car found.")
            return

        ttc_dict = defaultdict(lambda: defaultdict(dict))
        max_angle = math.radians(60)  # Field of view cone
        
        for ego_id in ego_ids:
            for other_id in other_car_ids:
                s_ego, e_ego = log.get_actor_alive_frames(ego_id)
                s_other, e_other = log.get_actor_alive_frames(other_id)

                if ego_id == 86 and other_id == 102:
                    print(f"Starting    Ego: {s_ego} Other: {s_other}\n")
                    print(f"Ending    Ego: {e_ego} Other: {e_other}\n")

                start = max(s_ego, s_other)
                end = min(e_ego, e_other)

                for frame in range(start, end + 1):
                    ego_t = log.get_actor_transform(ego_id, frame)
                    ego_v = log.get_actor_velocity(ego_id, frame)
                    other_t = log.get_actor_transform(other_id, frame)
                    other_v = log.get_actor_velocity(other_id, frame)

                    ego_pos = np.array([ego_t.location.x, ego_t.location.y, ego_t.location.z])
                    other_pos = np.array([other_t.location.x, other_t.location.y, other_t.location.z])
                    ego_vel = np.array([ego_v.x, ego_v.y, ego_v.z])
                    other_vel = np.array([other_v.x, other_v.y, other_v.z])

                    rel_pos = other_pos - ego_pos
                    rel_vel = other_vel - ego_vel

                    yaw = math.radians(ego_t.rotation.yaw)
                    forward = np.array([math.cos(yaw), math.sin(yaw), 0.0])
                    forward /= np.linalg.norm(forward)

                    lon_dist = np.dot(rel_pos, forward)

                    if lon_dist <= 0:
                        continue

                    # angle = math.acos(
                    #     np.clip(np.dot(rel_pos, forward) / 
                    #            (np.linalg.norm(rel_pos) + 1e-6), -1, 1)
                    # )
                    # if angle > max_angle:
                    #     continue

                    rel_speed_lon = np.dot(rel_vel, forward)

                    if rel_speed_lon >= 0:
                        continue

                    ttc = lon_dist / (-rel_speed_lon)
                    ttc_dict[ego_id][other_id][frame] = ttc

        out_file = os.path.splitext(self._recorder)[0] + ".time_to_collision.json"
        json_safe = {str(k): {str(kk): vv for kk, vv in v.items()}
                     for k, v in ttc_dict.items()}
        with open(out_file, "w") as f:
            json.dump(json_safe, f, indent=2)
        print(f"[TimeToCollision] Saved -> {out_file}")

        for ego_id in ego_ids:
            if ego_id != 86:
                continue
            for other_id, frame_ttc in ttc_dict[ego_id].items():
                if other_id != 102:
                    continue
                frames, ttcs = zip(*sorted(frame_ttc.items()))
                plt.plot(frames, ttcs, label=f"ego {134} vs car {150}")
            plt.ylabel("TTC [s]")
            plt.xlabel("Frame number")
            plt.title(f"Time-to-Collision for ego vehicle {134}")
            plt.legend()
            plt.show()
            