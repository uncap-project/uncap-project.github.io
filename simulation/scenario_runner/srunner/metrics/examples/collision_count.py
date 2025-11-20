#!/usr/bin/env python
"""
Counts the number of collisions the ego vehicle had,
categorized by collision type (vehicle, pedestrian, static),
and dumps the result to JSON.
"""
import json
from srunner.metrics.examples.basic_metric import BasicMetric

class CollisionCount(BasicMetric):
    """
    Metric class CollisionCount - custom
    """
    
    def _categorize_collision(self, type_id):
        """
        Categorize the collision based on actor type_id string.
        
        Args:
            type_id: String representing the actor type (e.g., 'vehicle.tesla.model3', 'walker.pedestrian.0001')
            
        Returns:
            Category string: 'vehicle', 'pedestrian', or 'static'
        """
        if not type_id or type_id == 'unknown':
            return 'unknown'
            
        type_id_lower = type_id.lower()
        
        if type_id_lower.startswith('vehicle.'):
            return 'vehicle'
        elif type_id_lower.startswith('walker.'):
            return 'pedestrian'
        else:
            return 'static'
    
    def _create_metric(self, town_map, log, criteria):
        ego_id = log.get_ego_vehicle_id()
        collisions = log.get_actor_collisions(ego_id)

        
        vehicle_collisions = []
        pedestrian_collisions = []
        static_collisions = []
        unknown_collisions = []
        
        total_impacts = 0
        frames = list(collisions.keys())
        per_frame_categorized = {}
        
        for frame, collision_list in collisions.items():
            frame_collisions = {
                'vehicle': [],
                'pedestrian': [],
                'static': [],
                'unknown': []
            }
            
            for other_actor_id in collision_list:
                total_impacts += 1
                
                other_actor_type = 'unknown'
                inferred = False
                
                try:
                    actor_attrs = log.get_actor_attributes(other_actor_id)
                    if actor_attrs and isinstance(actor_attrs, dict):
                        other_actor_type = actor_attrs.get('type_id', 'unknown')
                except:
                    pass
                
                # If actor_id is -1 or type is unknown, infer from nearest actor
                if other_actor_id == -1 or other_actor_type == 'unknown':
                    try:
                        ego_transform = log.get_actor_transform(ego_id, frame)
                        ego_location = ego_transform.location
                        all_transforms = log.get_actor_transforms_at_frame(frame)
                        
                        nearest_actor = None
                        min_distance = float('inf')
                        
                        for actor_id in all_transforms.keys():
                            if actor_id == ego_id:
                                continue
                            try:
                                attrs = log.get_actor_attributes(actor_id)
                                if attrs and 'type_id' in attrs:
                                    actor_transform = all_transforms[actor_id]
                                    actor_location = actor_transform.location
                                    distance = ((ego_location.x - actor_location.x)**2 + 
                                              (ego_location.y - actor_location.y)**2 + 
                                              (ego_location.z - actor_location.z)**2)**0.5
                                    
                                    if distance < min_distance:
                                        min_distance = distance
                                        nearest_actor = {
                                            'id': actor_id,
                                            'type': attrs['type_id'],
                                            'distance': round(distance, 2)
                                        }
                            except:
                                pass
                        
                        if nearest_actor and nearest_actor['distance'] < 5.0:
                            other_actor_id = nearest_actor['id']
                            other_actor_type = nearest_actor['type']
                            inferred = True
                    except:
                        pass
                
                category = self._categorize_collision(other_actor_type)
                
                collision_entry = {
                    'frame': frame,
                    'other_actor_id': other_actor_id,
                    'other_actor_type': other_actor_type
                }
                
                if inferred:
                    collision_entry['inferred'] = True
                    collision_entry['note'] = 'Actor inferred from nearest object (CARLA recorded -1)'
                
                frame_collisions[category].append(collision_entry)
                
                if category == 'vehicle':
                    vehicle_collisions.append(collision_entry)
                elif category == 'pedestrian':
                    pedestrian_collisions.append(collision_entry)
                elif category == 'static':
                    static_collisions.append(collision_entry)
                else:
                    unknown_collisions.append(collision_entry)
            
            per_frame_categorized[str(frame)] = frame_collisions
        
        results = {
            "total_impacts": total_impacts,
            "vehicle_collisions": len(vehicle_collisions),
            "pedestrian_collisions": len(pedestrian_collisions),
            "static_collisions": len(static_collisions),
            "unknown_collisions": len(unknown_collisions),
            "frames": frames,
            "collisions_by_type": {
                "vehicles": vehicle_collisions,
                "pedestrians": pedestrian_collisions,
                "static": static_collisions,
                "unknown": unknown_collisions
            },
            "per_frame": {str(k): v for k, v in collisions.items()},
            "per_frame_categorized": per_frame_categorized,
            "note": "Some collisions may be inferred from nearest actor when CARLA's recorder doesn't capture the actor ID (recorded as -1)."
        }
        
        out_path = 'srunner/metrics/data/CollisionCount_results.json'
        with open(out_path, 'w') as f:
            json.dump(results, f, indent=4)
        
        print(f"[CollisionCount] {total_impacts} collision(s) recorded → {out_path}")
        print(f"  - Vehicles: {len(vehicle_collisions)}")
        print(f"  - Pedestrians: {len(pedestrian_collisions)}")
        print(f"  - Static objects: {len(static_collisions)}")
        if unknown_collisions:
            print(f"  - Unknown: {len(unknown_collisions)}")