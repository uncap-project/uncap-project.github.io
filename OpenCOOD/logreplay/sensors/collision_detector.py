"""
Collision sensor for detecting if/how many collisions occur.
I wrote this in house based on ./semantic_lidar.py - so there might be some bugs
"""
import weakref
import os.path
import carla
import cv2
import numpy as np
from logreplay.sensors.base_sensor import BaseSensor
from opencood.hypes_yaml.yaml_utils import save_yaml_wo_overwriting


class CollisionDetector(BaseSensor):
    def __init__(self, agent_id, vehicle, world, config, global_position):
        super().__init__(agent_id, vehicle, world, config, global_position)

        if vehicle is not None:
            world = vehicle.get_world()

        self.agent_id = agent_id
        self.vehicle = vehicle

        blueprint = world.get_blueprint_library().find('sensor.other.collision')

        self.name = 'collision_detector' + str(agent_id) + str(config['unique_id'])

        if vehicle is not None:
            self.sensor = world.spawn_actor(
                blueprint, carla.Transform(), attach_to=vehicle
            )

            print(f"Spawned collision sensor: {self.sensor.id}")
        else:
            self.sensor = world.spawn_actor(blueprint, carla.Transform())
        
        # # no attributes to set for collision sensor
        # #relative_position = config['relative_pose']
        # spawn_point = self.spawn_point_estimation(global_position)
        #self.thresh = config['thresh']

        self.collision_distances = []
        self.nearby_vehicle_distances = []
        self.turning_point = []
        self.previous_yaw = None
        # tracking any nearby vehicles

        # lidar data - some code expects to see this so they're left as None
        # self.points = None
        self.obj_idx = None
        self.obj_tag = None

        self.timestamp = None
        self.frame = 0
        self.num_ticks = 0 # alternative to global "timestamp", used for turn detector
        
        # collision numbers
        self.collisions = 0

        weak_self = weakref.ref(self)
        self.sensor.listen(
            lambda event: CollisionDetector._on_data_event(
                weak_self, event))

    @staticmethod
    def _on_data_event(weak_self, event):
        """Collision Detector  method"""
        self = weak_self()
        if not self:
            return
        
        self.collisions += 1
        self.timestamp = event.timestamp
        self.frame = event.frame

        if self.vehicle is not None and event.other_actor is not None:
            vehicle_loc = self.vehicle.get_transform().location
            other_loc = event.other_actor.get_transform().location

            distance = vehicle_loc.distance(other_loc)
            self.collision_distances.append(distance)


        print(f"Collision detected at frame {event.frame}")

    def check_turning(self, current_yaw):
        # move this into asynchronous post processing over yaml coordinates

        # check docs for yaw units
        if self.previous_yaw is not None:
            yaw_diff = abs(current_yaw - self.previous_yaw)
            if yaw_diff > 10:  
                self.turning_point.append(self.num_ticks)
                print(f"Turning detected at tick {self.num_ticks}")
        self.previous_yaw = current_yaw

    def tick(self):
        world = self.sensor.get_world()
        curr_location = self.vehicle.get_transform().location

        curr_yaw = self.vehicle.get_transform().rotation.yaw
        self.check_turning(curr_yaw)

        vehicles = world.get_actors().filter('vehicle.*') # checking for all vehicles

        min_distance = None

        for v in vehicles:
            if v.id == self.vehicle.id:
                continue  # skip self

            v_location = v.get_transform().location
            distance = curr_location.distance(v_location)

            if min_distance is None or distance < min_distance:
                min_distance = distance

        if min_distance is not None:
            self.nearby_vehicle_distances.append(min_distance)

        self.num_ticks += 1

        return None
    
    def get_timestamps_from_ticks(self, cur_timestamp):
        # assumes that final number of ticks corresponds to current timestamp

        if (not self.turning_point): return []

        final_ticks = self.turning_point[-1]
        res = [float(tick) * cur_timestamp / final_ticks for tick in self.turning_point]

        return res
    
    def data_dump(self, output_root, cur_timestamp):
        # dump the yaml
        save_yaml_name = os.path.join(output_root,
                                      cur_timestamp +
                                      '_additional.yaml')

        collision_det_info = {
            'collision_detector': {
                'collision_events': self.collisions,
                'collision_distances': self.collision_distances,
                'nearby_vehicle_distances': min(self.nearby_vehicle_distances),
                'turning ticks': self.turning_point,
                'turning timestamps': self.get_timestamps_from_ticks(int(cur_timestamp))
            }
        }
        save_yaml_wo_overwriting(collision_det_info,
                                 save_yaml_name)
