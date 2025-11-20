#!/usr/bin/env python
# Copyright (c) 2020 Computer Vision Center (CVC) at the Universitat Autonoma de
# Barcelona (UAB).
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

"""
Metric that calculates the distance between every ego vehicle and every other
car in the simulation and dumps the result to a JSON file.
"""

import json
import math
import os
from collections import defaultdict
import random
import matplotlib.pyplot as plt

from srunner.metrics.examples.basic_metric import BasicMetric


class DistanceBetweenVehicles(BasicMetric):
    """
    Metric class DistanceBetweenVehicles
    """

    def _create_metric(self, town_map, log, criteria):
        """
        Computes the distance between each ego vehicle and every other vehicle.
        Results are written to
        <recorder_filename>.distance_between_vehicles.json
        """
        self._recorder = f"tmp_{random.randint(0, 999999):06d}.log"

        ego_ids = log.get_actor_ids_with_role_name("hero")
        # Any vehicle that is NOT an ego is considered "other car"
        other_car_ids = [
            aid for aid in log.get_actor_ids_with_type_id("vehicle.*")
            if aid not in ego_ids
        ]

        if not ego_ids or not other_car_ids:
            print("[DistanceBetweenVehicles] No ego / no other car found.")
            return

        distances = defaultdict(lambda: defaultdict(dict))

        for ego_id in ego_ids:
            for other_id in other_car_ids:

                # Life span intersection
                s_ego, e_ego = log.get_actor_alive_frames(ego_id)
                s_other, e_other = log.get_actor_alive_frames(other_id)

                
                start = max(s_ego, s_other)
                end   = min(e_ego, e_other)

                for frame in range(start, end + 1):
                    ego_t  = log.get_actor_transform(ego_id, frame)
                    other_t = log.get_actor_transform(other_id, frame)

                    # Skip underground vehicles (optional filter)
                    if other_t.location.z < -10:
                        continue

                    dx = ego_t.location.x - other_t.location.x
                    dy = ego_t.location.y - other_t.location.y
                    dz = ego_t.location.z - other_t.location.z
                    dist = math.sqrt(dx*dx + dy*dy + dz*dz)

                    distances[ego_id][other_id][frame] = dist

        base_name = "example"

        #    Build full output path
        # print(os.getcwd())
        out_file = os.path.join(
            "../../OpenCOOD/logreplay/scenario/metric_results/",
            base_name + ".distance_between_vehicles.json"
        )
        # Convert defaultdict to plain dict for JSON
        json_safe = {str(k): {str(kk): vv for kk, vv in v.items()}
                     for k, v in distances.items()}
        with open(out_file, "w") as f:
            json.dump(json_safe, f, indent=2)
        print(f"[DistanceBetweenVehicles] Saved -> {out_file}")

        for ego_id in ego_ids:
            if ego_id != 63:
                continue
            for other_id, frame_dist in distances[ego_id].items():
                if other_id!=79:
                    continue
                frames, dists = zip(*sorted(frame_dist.items()))
                plt.plot(frames, dists,
                         label=f"ego 134 vs car 150")
            plt.ylabel("Distance [m]")
            plt.xlabel("Frame number")
            plt.title(f"Distances for ego vehicle 134")
            plt.legend()

            plt.ylim(0, 60)
            plt.yticks(range(0, 61, 10))

            plt.show()