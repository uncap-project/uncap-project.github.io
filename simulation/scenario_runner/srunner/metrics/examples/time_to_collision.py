"""
Metric that estimates the Time-To-Collision (TTC) between every ego vehicle
and every other vehicle in the simulation.
"""

import json
import math
import os
from collections import defaultdict
import yaml

import matplotlib.pyplot as plt
import numpy as np
import random
from srunner.metrics.examples.basic_metric import BasicMetric

BASE = os.getcwd()

#reaplce examples:
ego_vehicle="134"
collision_vehicle = "150"
yaml_dir = f"{BASE}/OPV2V/test/2021_08_23_21_47_19/243"


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
        
        
        yaml_files = sorted([f for f in os.listdir(yaml_dir) if f.endswith(".yaml")])
        for yf in yaml_files:
            curtick = os.path.splitext(yf)[0] 
            frame = int(curtick)           
            # print(os.path.join(yaml_dir, yf))   
            yaml_path = os.path.join(yaml_dir, yf)

            with open(yaml_path, "r") as f:
                data = yaml.safe_load(f)

            ego_key = str(243)
            other_key = (261)

            
            other_data = data["vehicles"].get(other_key)
            if  other_data is None:
                print("none")
                continue

            ego_pos = np.array(data["true_ego_pos"][:3])
            other_pos = np.array(other_data["location"])

            ego_speed = data["ego_speed"]
            ego_yaw = math.radians(data["true_ego_pos"][4])
            ego_vel = np.array([ego_speed * math.cos(ego_yaw), ego_speed * math.sin(ego_yaw), 0.0])
            # print(ego_speed,ego_yaw,ego_vel)
            other_speed = other_data["speed"]
            other_yaw = math.radians(other_data["angle"][1])
            other_vel = np.array([other_speed * math.cos(other_yaw), other_speed * math.sin(other_yaw), 0.0])
            # print(other_speed,other_yaw,other_vel)
            # print()
            rel_pos = other_pos - ego_pos
            rel_vel = other_vel - ego_vel
            # print(rel_pos,rel_vel)
            if np.dot(rel_vel, rel_vel) < 1e-6:
                continue

            t = -np.dot(rel_vel, rel_pos) / np.dot(rel_vel, rel_vel)
            ttc_dict[ego_vehicle][collision_vehicle][frame] = t
            continue

                

        out_file = os.path.splitext(self._recorder)[0] + ".time_to_collision.json"
        json_safe = {str(k): {str(kk): vv for kk, vv in v.items()}
                     for k, v in ttc_dict.items()}
        with open(out_file, "w") as f:
            json.dump(json_safe, f, indent=2)
        print(f"[TimeToCollision] Saved -> {out_file}")