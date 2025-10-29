#!/usr/bin/env python
"""
Counts red-traffic-light violations by the ego vehicle.

Writes:
  total_violations          – scalar
  violations_per_frame      – list of (frame, light_id)
"""

import json
from srunner.metrics.examples.basic_metric import BasicMetric


class TrafficLightViolationCount(BasicMetric):
    """
    Metric class TrafficLightViolationCount
    """

    def _create_metric(self, town_map, log, criteria):
        
        ego_ids = log.get_actor_ids_with_role_name("hero")
        
        if not ego_ids:
            print("[EgoControlsPlot] No ego vehicles found.")
            return

        total_results = {}

        for ego_id in ego_ids:
            violations = []               # (frame, light_id)
            total = 0

            for frame_idx, frame in enumerate(log._frames):
                viols = frame["events"].get("traffic_light_violations", {})
                if ego_id in viols:
                    for light_id in viols[ego_id]:
                        violations.append((frame_idx + 1, light_id))
                        total += 1

            results = {
                "total_violations": total,
                "violations_per_frame": violations
            }

            total_results[ego_id] = results

        out_path = 'srunner/metrics/data/TrafficLightViolationCount_results_nearmiss_comms.json'
        with open(out_path, 'w') as f:
            json.dump(results, f, indent=4)

        print(f"[TrafficLightViolationCount] {total} violation(s) → {out_path}")