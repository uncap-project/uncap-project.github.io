#!/usr/bin/env python

import json
from srunner.metrics.examples.basic_metric import BasicMetric
import math

class InfractionsMetric(BasicMetric):
    """
    Calculates infraction score from collisions, lane invasions, and traffic light violations
    """

    def _create_metric(self, town_map, log, criteria):
        ego_ids = log.get_actor_ids_with_role_name("hero")
        ego_id = ego_ids[0]
        infraction_score = 1.0

        # Penalty multipliers
        penalties = {
            "collision_vehicle": 0.50,
            "collision_pedestrian": 0.00,
            "collision_static": 0.80,
            "lane_invasion": 0.90,
            "red_light": 0.70
        }

        # Collisions
        collisions = log.get_actor_collisions(ego_id)
        print(collisions)
        for c in collisions:
            other_actor = c[1]  # (frame, other_actor_id, impulse)
            other_type = log.get_actor_type(other_actor)

            if "vehicle" in other_type:
                infraction_score *= penalties["collision_vehicle"]
            elif "walker" in other_type:
                infraction_score *= penalties["collision_pedestrian"]
            else:
                infraction_score *= penalties["collision_static"]

        # Lane invasions
        lane_deviation_count = 0
        start, end = log.get_actor_alive_frames(ego_id)

        LANE_THRESHOLD = 1.0  # meters, adjust based on lane width

        for i in range(start, end + 1):
            ego_location = log.get_actor_transform(ego_id, i).location
            ego_waypoint = town_map.get_waypoint(ego_location)

            a = ego_location - ego_waypoint.transform.location
            b = ego_waypoint.transform.get_right_vector()
            b_norm = math.sqrt(b.x * b.x + b.y * b.y + b.z * b.z)

            ab_dot = a.x * b.x + a.y * b.y + a.z * b.z
            dist_v = ab_dot/(b_norm*b_norm)*b
            dist = math.sqrt(dist_v.x * dist_v.x + dist_v.y * dist_v.y + dist_v.z * dist_v.z)

            c = ego_waypoint.transform.get_forward_vector()
            ac_cross = c.x * a.y - c.y * a.x
            if ac_cross < 0:
                dist *= -1

            if abs(dist) > LANE_THRESHOLD:
                lane_deviation_count += 1
                infraction_score *= penalties["lane_invasion"]

        # Traffic light violations
        red_light_count = 0
        world = town_map.get_world()
        traffic_lights = world.get_actors().filter("*traffic_light*")

        for i in range(start, end + 1):
            ego_tf = log.get_actor_transform(ego_id, i)
            ego_location = ego_tf.location

            for tl in traffic_lights:
                tl_state = log.get_traffic_light_state(tl.id, i) 
                print(tl_state)
                if tl_state:
                    if self._in_stop_line(ego_location, tl):
                        red_light_count += 1
                        infraction_score *= penalties["red_light"]

        # -------------------------
        # Save results
        # -------------------------
        results = {
            "infraction_score": infraction_score,
            "collisions": len(collisions),
            "lane_invasions": lane_deviation_count,
            "red_light_violations": red_light_count
        }

        with open('srunner/metrics/data/InfractionsMetric_results.json', 'w') as fw:
            json.dump(results, fw, indent=4)
