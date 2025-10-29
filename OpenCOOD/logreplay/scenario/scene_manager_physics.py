import os
import random
import sys
from collections import OrderedDict

import carla
import numpy as np

from logreplay.assets.utils import find_town, find_blue_print
from logreplay.assets.presave_lib import bcolors
from logreplay.map.map_manager import MapManager
from logreplay.sensors.sensor_manager_rgb import SensorManager
from opencood.hypes_yaml.yaml_utils import load_yaml

import json

class SceneManager:
    """
    Manager for each scene for spawning, moving and destroying.

    Parameters
    ----------
    folder : str
        The folder to the current scene.

    scene_name : str
        The scene's name.

    collection_params : dict
        The collecting protocol information.

    scenario_params : dict
        The replay params.
    """


    def __init__(self, folder, scene_name, collection_params, scenario_params):
        self.velocity_scale={
            "2021_08_20_21_10_24":{
                "2042":{"scale": 1.1, "no_vel_change": True, "boost_range": (76, 200),        # tick range to enforce boost
                        "boost_factor": 2.0 },
                # "2014":0.8,
                # "2046":0.8,
                # "2050":0.8,
                # "2026":0.8
            }
        }
            
        self.scene_name = scene_name
        self.town_name = find_town(scene_name)
        self.collection_params = collection_params
        self.scenario_params = scenario_params
        self.cav_id_list = []
        self.tick_numbers = [] 
        self.accepted_cavs_per_tick = []

        self.steering_controlled_vehicles = {}
        self.speed_controlled_vehicles = {}


        self.accepted_cav_log_file = "/home/po-han/Desktop/Projects/simulation/scenario_runner/accepted_cav_test_20_21_10_24.json"
        self.bandwidth_log_file = "/home/po-han/Desktop/Projects/simulation/scenario_runner/bandwidth_test_20_21_10_24.json"

        self.bandwidth_metrics = {
            # Accepted CAVs only strategy
            'accepted_only': {
                'total_data_sent_mb': 0.0,
                'total_packets_sent': 0,
                'packets_per_tick': [],
                'data_per_tick_mb': [],
                'recipient_count_per_tick': []
            },
            # Send to all CAVs strategy (for comparison)
            'send_to_all': {
                'total_data_sent_mb': 0.0,
                'total_packets_sent': 0,
                'packets_per_tick': [],
                'data_per_tick_mb': [],
                'recipient_count_per_tick': []
            }
        }
        # Timing for frequency calculation
        self.simulation_start_timestamp = None
        self.tick_timestamps = []

        # dumping related
        self.output_root = os.path.join(scenario_params['output_dir'],
                                        scene_name)

        if 'seed' in collection_params['world']:
            np.random.seed(collection_params['world']['seed'])
            random.seed(collection_params['world']['seed'])

        # at least 1 cav should show up
        cav_list = sorted([x for x in os.listdir(folder)
                           if os.path.isdir(
                os.path.join(folder, x))])
        assert len(cav_list) > 0
        print(cav_list)

        self.database = OrderedDict()
        # we want to save timestamp as the parent keys for cavs
        cav_sample = os.path.join(folder, cav_list[0])

        yaml_files = \
            sorted([os.path.join(cav_sample, x)
                    for x in os.listdir(cav_sample) if
                    x.endswith('.yaml') and 'additional' not in x])
        self.timestamps = self.extract_timestamps(yaml_files)

        # loop over all timestamps
        for timestamp in self.timestamps:
            self.database[timestamp] = OrderedDict()
            # loop over all cavs
            for (j, cav_id) in enumerate(cav_list):
                if cav_id not in self.cav_id_list:
                    self.cav_id_list.append(str(cav_id))

                self.database[timestamp][cav_id] = OrderedDict()
                cav_path = os.path.join(folder, cav_id)

                yaml_file = os.path.join(cav_path,
                                         timestamp + '.yaml')
                self.database[timestamp][cav_id]['yaml'] = \
                    yaml_file

        # this is used to dynamically save all information of the objects
        self.veh_dict = OrderedDict()
        # used to count timestamp
        self.cur_count = 0
        # used for HDMap
        self.map_manager = None
        self.stopped_vehicles = set()  # Track vehicles that should remain stopped

    def get_data_payload_size(self, cav_id):
        """
        Calculate the size of data that would be sent to a CAV.
        This simulates the actual data sharing payload.
        
        Parameters
        ----------
        cav_id : str
            The CAV ID to calculate data size for
            
        Returns
        -------
        int
            Size in bytes of the data payload
        """
        # Simulate typical V2X data payload including:
        # - Position data (GPS coordinates, heading, velocity)
        # - Sensor data summary
        # - Planning information
        # - Detection/perception data
        
        if cav_id not in self.veh_dict:
            return 0
            
        actor = self.veh_dict[cav_id]['actor']
        transform = actor.get_transform()
        velocity = actor.get_velocity()
        
        # Create a representative data payload (as JSON string)
        data_payload = {
            "cav_id": cav_id,
            "timestamp": self.timestamps[self.cur_count] if self.cur_count < len(self.timestamps) else "unknown",
            "position": {
                "x": float(transform.location.x),
                "y": float(transform.location.y),
                "z": float(transform.location.z)
            },
            "rotation": {
                "roll": float(transform.rotation.roll),
                "pitch": float(transform.rotation.pitch),
                "yaw": float(transform.rotation.yaw)
            },
            "velocity": {
                "x": float(velocity.x),
                "y": float(velocity.y),
                "z": float(velocity.z)
            },
            # Simulate additional sensor/perception data
            "detections": [
                {"object_id": i, "type": "vehicle", "distance": 10.5 + i*2.3, 
                 "angle": 15.2 + i*5.1, "confidence": 0.95 - i*0.1}
                for i in range(5)  # Simulate 5 detected objects
            ],
            "path_planning": {
                "waypoints": [[100.1 + i*10.2, 200.3 + i*5.7] for i in range(10)],
                "target_speed": 15.5,
                "lane_id": "lane_001"
            },
            "communication_metadata": {
                "sender_id": cav_id,
                "message_type": "cooperative_awareness",
                "protocol_version": "1.2",
                "encryption": "AES-256"
            }
        }
        
        # Convert to JSON string and get byte size
        json_string = json.dumps(data_payload)
        return len(json_string.encode('utf-8'))

    def calculate_bandwidth_metrics(self, accepted_cavs, cur_timestamp):
        """
        Calculate bandwidth metrics for both strategies:
        1. Send only to accepted CAVs
        2. Send to all CAVs
        
        Parameters
        ----------
        accepted_cavs : list
            List of accepted CAV IDs for current tick
        cur_timestamp : str
            Current simulation timestamp (e.g., "000069")
        """
        # Track simulation timestamps
        timestamp_int = int(cur_timestamp)
        if self.simulation_start_timestamp is None:
            self.simulation_start_timestamp = timestamp_int
        self.tick_timestamps.append(timestamp_int)
        
        # Get all active CAVs (excluding the ego CAV that's sending)
        all_active_cavs = [cav_id for cav_id in self.cav_id_list if cav_id in self.veh_dict]
        ego_cav_id = "1996"  # The sender CAV
        if ego_cav_id in all_active_cavs:
            all_active_cavs.remove(ego_cav_id)
        
        # Calculate data size per packet (from ego CAV perspective)
        ego_data_size = self.get_data_payload_size(ego_cav_id) if ego_cav_id in self.veh_dict else 1024  # Default 1KB if not found
        data_size_mb = ego_data_size / (1024 * 1024)  # Convert to MB
        
        # Strategy 1: Send only to accepted CAVs
        accepted_packets = len(accepted_cavs)
        accepted_data_mb = data_size_mb * accepted_packets
        
        self.bandwidth_metrics['accepted_only']['total_packets_sent'] += accepted_packets
        self.bandwidth_metrics['accepted_only']['total_data_sent_mb'] += accepted_data_mb
        self.bandwidth_metrics['accepted_only']['packets_per_tick'].append(accepted_packets)
        self.bandwidth_metrics['accepted_only']['data_per_tick_mb'].append(accepted_data_mb)
        self.bandwidth_metrics['accepted_only']['recipient_count_per_tick'].append(len(accepted_cavs))
        
        # Strategy 2: Send to all CAVs (comparison baseline)
        all_packets = len(all_active_cavs)
        all_data_mb = data_size_mb * all_packets
        
        self.bandwidth_metrics['send_to_all']['total_packets_sent'] += all_packets
        self.bandwidth_metrics['send_to_all']['total_data_sent_mb'] += all_data_mb
        self.bandwidth_metrics['send_to_all']['packets_per_tick'].append(all_packets)
        self.bandwidth_metrics['send_to_all']['data_per_tick_mb'].append(all_data_mb)
        self.bandwidth_metrics['send_to_all']['recipient_count_per_tick'].append(len(all_active_cavs))
        
        # Log current tick metrics
        print(f"[Bandwidth] Timestamp {cur_timestamp} (Tick {self.cur_count}):")
        print(f"  - Packet size: {ego_data_size} bytes ({data_size_mb:.6f} MB)")
        print(f"  - Accepted CAVs: {len(accepted_cavs)}, Data sent: {accepted_data_mb:.6f} MB")
        print(f"  - All CAVs: {len(all_active_cavs)}, Data sent: {all_data_mb:.6f} MB")
        print(f"  - Bandwidth saved: {(all_data_mb - accepted_data_mb):.6f} MB ({((all_data_mb - accepted_data_mb) / max(all_data_mb, 0.000001)) * 100:.2f}%)")

    def save_bandwidth_metrics(self):
        """
        Save comprehensive bandwidth metrics to file.
        """
        # Calculate frequency metrics based on simulation timestamps
        total_simulation_time_steps = 0
        avg_frequency = 0
        timestamp_interval = 0
        
        if len(self.tick_timestamps) > 1:
            # Calculate average time step between timestamps
            total_simulation_time_steps = self.tick_timestamps[-1] - self.tick_timestamps[0]
            
            # Calculate average interval between consecutive timestamps
            intervals = [self.tick_timestamps[i+1] - self.tick_timestamps[i] 
                        for i in range(len(self.tick_timestamps)-1)]
            timestamp_interval = sum(intervals) / len(intervals) if intervals else 0
            
            # Frequency = 1 / average_interval (assuming timestamp units are meaningful)
            avg_frequency = 1.0 / timestamp_interval if timestamp_interval > 0 else 0
        
        # Calculate savings
        total_saved_mb = (self.bandwidth_metrics['send_to_all']['total_data_sent_mb'] - 
                         self.bandwidth_metrics['accepted_only']['total_data_sent_mb'])
        total_saved_packets = (self.bandwidth_metrics['send_to_all']['total_packets_sent'] - 
                              self.bandwidth_metrics['accepted_only']['total_packets_sent'])
        
        savings_percentage = 0
        if self.bandwidth_metrics['send_to_all']['total_data_sent_mb'] > 0:
            savings_percentage = (total_saved_mb / self.bandwidth_metrics['send_to_all']['total_data_sent_mb']) * 100
        
        comprehensive_metrics = {
            'simulation_summary': {
                'total_ticks': len(self.tick_timestamps),
                'total_simulation_timestamps': total_simulation_time_steps,
                'average_timestamp_interval': timestamp_interval,
                'estimated_frequency_hz': avg_frequency,
                'timestamp_range': {
                    'start': self.tick_timestamps[0] if self.tick_timestamps else 0,
                    'end': self.tick_timestamps[-1] if self.tick_timestamps else 0
                },
                'total_cavs_in_simulation': len(self.cav_id_list)
            },
            'bandwidth_comparison': {
                'accepted_cavs_only': self.bandwidth_metrics['accepted_only'],
                'send_to_all_cavs': self.bandwidth_metrics['send_to_all'],
                'savings': {
                    'data_saved_mb': total_saved_mb,
                    'packets_saved': total_saved_packets,
                    'percentage_saved': savings_percentage
                }
            },
            'detailed_analysis': {
                'avg_packet_size_bytes': sum([self.get_data_payload_size(cav_id) for cav_id in self.cav_id_list if cav_id in self.veh_dict]) / max(len([cav_id for cav_id in self.cav_id_list if cav_id in self.veh_dict]), 1),
                'peak_data_per_tick_mb': {
                    'accepted_only': max(self.bandwidth_metrics['accepted_only']['data_per_tick_mb'], default=0),
                    'send_to_all': max(self.bandwidth_metrics['send_to_all']['data_per_tick_mb'], default=0)
                },
                'avg_data_per_tick_mb': {
                    'accepted_only': sum(self.bandwidth_metrics['accepted_only']['data_per_tick_mb']) / max(len(self.bandwidth_metrics['accepted_only']['data_per_tick_mb']), 1),
                    'send_to_all': sum(self.bandwidth_metrics['send_to_all']['data_per_tick_mb']) / max(len(self.bandwidth_metrics['send_to_all']['data_per_tick_mb']), 1)
                }
            }
        }
        
        try:
            with open(self.bandwidth_log_file, 'w') as f:
                json.dump(comprehensive_metrics, f, indent=2)
            print(f"[Bandwidth] Metrics saved to: {self.bandwidth_log_file}")
        except Exception as e:
            print(f"Error writing bandwidth metrics file: {e}")

    def get_vlm_file_path(self, timestamp):
        idx = int(timestamp)
        filename = f"{idx:06d}_vlm.txt"
        base_path = "/home/po-han/Downloads/OPV2V/vlm_query_testing/aug_4th_testing/scene2_decisions"
        return os.path.join(base_path, filename)

    def should_stop_based_on_vlm(self, vlm_text):
        if "action: stop" in vlm_text.lower():
            return True
        return False
    

    def get_cav_communications(self, cav_id):
        
        communications = {}

        for other_cav_id in self.cav_id_list:
            if other_cav_id == cav_id: 
                continue

            if other_cav_id not in self.veh_dict:
                continue  

            actor = self.veh_dict[other_cav_id]['actor']
            transform = actor.get_transform()
            loc = transform.location
            rot = transform.rotation

            communications[other_cav_id] = {
                "position": [loc.x, loc.y],
                "heading": rot.yaw  # yaw = heading in degrees
            }

        return communications
    
    import numpy as np

    def filter_accepted_cavs(self, ego_id, communications, ego_goal, epsilon=15.0):
        
        if ego_goal == [float('-inf'),float('-inf')]:
            return []
        accepted = []
        ego_actor = self.veh_dict[ego_id]['actor']
        ego_pos = ego_actor.get_transform().location
        pos_ego = np.array([ego_pos.x, ego_pos.y])
        pos_goal = np.array(ego_goal)
        
        for cav_id, info in communications.items():
            pos_cav = np.array(info["position"][:2])
            
            # condition 1: distance check
            dist = np.linalg.norm(pos_ego - pos_cav)
            if dist > epsilon:
                continue
                
            # Get CAV velocity
            cav_actor = self.veh_dict[cav_id]['actor']
            vel = cav_actor.get_velocity()
            vel_vec = np.array([vel.x, vel.y])
            
            # condition 2a: Original check - moving in ego's direction
            goal_dir = pos_goal - pos_ego
            original_check = np.dot(goal_dir, vel_vec) > 0
            
            # condition 2b: New check - moving toward ego's goal
            goal_from_cav = pos_goal - pos_cav
            convergence_check = np.dot(goal_from_cav, vel_vec) > 0
            
            # Accept only if both checks pass
            if original_check and convergence_check:
                accepted.append(cav_id)
                    
        return accepted

    def get_ego_goal(self, ego_goal_filepath, cur_timestamp):
        """
        Get the ego goal position from the plan_trajectory in the ego CAV's YAML file.
        
        Parameters
        ----------
        ego_goal_filepath : str
            The file path to the ego CAV's folder containing YAML files
        cur_timestamp : str
            Current timestamp string (e.g., "000069")
            
        Returns
        -------
        list[float]
            The goal position [x, y] from the last point in plan_trajectory
        """
        try:
            # Construct the file path
            ego_yaml_file = os.path.join(ego_goal_filepath, f"{cur_timestamp}.yaml")
            
            # Check if file exists
            if not os.path.exists(ego_yaml_file):
                print(f"Warning: Ego goal file not found: {ego_yaml_file}")
                return [float('-inf'),float('-inf')]  # fallback
                
            # Load the YAML content
            ego_content = load_yaml(ego_yaml_file)
            
            # Extract plan_trajectory
            if 'plan_trajectory' not in ego_content:
                print(f"Warning: No plan_trajectory found in {ego_yaml_file}")
                return [float('-inf'),float('-inf')]  # fallback
                
            plan_trajectory = ego_content['plan_trajectory']
            
            # Check if trajectory has points
            if not plan_trajectory or len(plan_trajectory) == 0:
                print(f"Warning: Empty plan_trajectory in {ego_yaml_file}")
                return [float('-inf'),float('-inf')]  # fallback
                
            # Get the last point and extract x, y coordinates
            last_point = plan_trajectory[-3]
            ego_goal = [last_point[0], last_point[1]]  # x, y only
            
            return ego_goal
            
        except Exception as e:
            print(f"Error getting ego goal from {ego_goal_filepath} at {cur_timestamp}: {e}")
            return [float('-inf'),float('-inf')]

    def start_simulator(self):
        """
        Connect to the carla simulator for log replay.
        """
        simulation_config = self.collection_params['world']

        # simulation sync mode time step
        fixed_delta_seconds = simulation_config['fixed_delta_seconds']
        weather_config = simulation_config[
            'weather'] if "weather" in simulation_config else None

        # setup the carla client
        self.client = \
            carla.Client('localhost', simulation_config['client_port'])
        self.client.set_timeout(10.0)

        # load the map
        if self.town_name != 'Culver_City':
            try:
                self.world = self.client.load_world(self.town_name)
            except RuntimeError:
                print(
                    f"{bcolors.FAIL} %s is not found in your CARLA repo! "
                    f"Please download all town maps to your CARLA "
                    f"repo!{bcolors.ENDC}" % self.town_name)
        else:
            self.world = self.client.get_world()

        if not self.world:
            sys.exit('World loading failed')

        # setup the new setting
        self.origin_settings = self.world.get_settings()
        new_settings = self.world.get_settings()

        new_settings.synchronous_mode = True
        new_settings.fixed_delta_seconds = fixed_delta_seconds

        

        self.world.apply_settings(new_settings)
        # set weather if needed
        if weather_config is not None:
            weather = self.set_weather(weather_config)
            self.world.set_weather(weather)
        # get map
        self.carla_map = self.world.get_map()
        # spectator
        self.spectator = self.world.get_spectator()
        # hd map manager per scene
        self.map_manager = MapManager(self.world,
                                      self.scenario_params['map'],
                                      self.output_root,
                                      self.scene_name)
        
        record_dir = '/home/po-han/Desktop/Projects/OpenCOOD/logreplay/scenario/metric_record'
        os.makedirs(record_dir, exist_ok=True)
        record_path = os.path.join(record_dir, 'recording.log')
        self.client.start_recorder(record_path, additional_data=True)
        print(f"[SceneManager] Recording started: {record_path}")

    def log_accepted_cavs(self, tick_number, accepted_cavs):
        import json
        self.tick_numbers.append(tick_number)
        self.accepted_cavs_per_tick.append(accepted_cavs.copy())
        
        # Write to file immediately for real-time monitoring
        log_data = {
            'tick_numbers': self.tick_numbers,
            'accepted_cavs_per_tick': self.accepted_cavs_per_tick
        }
        
        try:
            with open(self.accepted_cav_log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
        except Exception as e:
            print(f"Error writing CAV log file: {e}")

    def get_vlm_merge_file_path(self, timestamp):
        """
        Get the file path for VLM merge decision files.
        
        Parameters
        ----------
        timestamp : str
            Current timestamp string (e.g., "000069")
            
        Returns
        -------
        str
            Full path to the VLM merge decision file
        """
        idx = int(timestamp)
        filename = f"{idx:06d}.txt"
        base_path = "/home/po-han/Downloads/OPV2V/vlm_query_testing/scene4_fast_merge_decisions_comms"
        return os.path.join(base_path, filename)

    def should_merge_based_on_vlm(self, vlm_text):
        """
        Parse VLM text to determine if merge action should be taken.
        
        Parameters
        ----------
        vlm_text : str
            Content of the VLM decision file
            
        Returns
        -------
        bool
            True if action indicates merge, False otherwise
        """
        if "action: merge" in vlm_text.lower():
            return True
        return False
    
    def apply_steering_control(self, vehicle_id, steering_angle=0.3, duration_ticks=60, throttle=0.5):
        """
        Apply manual steering control to a vehicle for a specified duration.
        
        Parameters
        ----------
        vehicle_id : str
            ID of the vehicle to control
        steering_angle : float
            Steering angle (-1.0 to 1.0, positive = right turn)
        duration_ticks : int
            How many ticks to maintain steering control
        throttle : float
            Throttle amount (0.0 to 1.0)
        """
        if vehicle_id not in self.veh_dict:
            print(f"[SceneManager] Cannot apply steering - vehicle {vehicle_id} not found")
            return
        
        vehicle = self.veh_dict[vehicle_id]['actor']
        vehicle.set_autopilot(False)  # Disable autopilot to take manual control

        vehicle.set_target_velocity(carla.Vector3D(x=10.0, y=0.0, z=0.0))
        
        self.steering_controlled_vehicles[vehicle_id] = {
            'start_tick': self.cur_count,
            'steering_angle': steering_angle,
            'duration': duration_ticks,
            'throttle': throttle
        }
        
        print(f"[SceneManager] Vehicle {vehicle_id} under manual steering control (angle: {steering_angle:.2f}, duration: {duration_ticks} ticks)")

    def update_steering_controlled_vehicles(self):
        """
        Update all vehicles currently under manual steering control.
        """
        vehicles_to_release = []
        
        for vehicle_id, control_data in self.steering_controlled_vehicles.items():
            if vehicle_id not in self.veh_dict:
                vehicles_to_release.append(vehicle_id)
                continue
                
            vehicle = self.veh_dict[vehicle_id]['actor']
            ticks_elapsed = self.cur_count - control_data['start_tick']

            
            if ticks_elapsed < control_data['duration']:
                # Create sine wave steering pattern
                max_steering = control_data['steering_angle']  # Peak steering angle
                total_duration = control_data['duration']
                
                # Sine wave: starts at 0, peaks at duration/2, returns to 0
                # Use pi to create one complete half-cycle over the duration
                progress = ticks_elapsed / total_duration  # 0 to 1
                sine_value = np.sin(progress * np.pi)  # 0 to 1 and back to 0
                current_steering = max_steering * sine_value
                
                
                control = carla.VehicleControl(
                    throttle=control_data['throttle'],
                    steer=current_steering,  # Use sine wave steering
                    brake=0.0
                )
                vehicle.apply_control(control)
            else:
                # Release control - re-enable autopilot
                vehicle.set_autopilot(True)
                print(f"[SceneManager] Releasing steering control for vehicle {vehicle_id}")
                vehicles_to_release.append(vehicle_id)
        
        # Clean up completed steering controls
        for vehicle_id in vehicles_to_release:
            if vehicle_id in self.steering_controlled_vehicles:
                del self.steering_controlled_vehicles[vehicle_id]

    def should_slow_down_based_on_vlm(self, vlm_text):
        """
        Parse VLM text to determine if slow down action should be taken.
        
        Parameters
        ----------
        vlm_text : str
            Content of the VLM decision file
            
        Returns
        -------
        bool
            True if action indicates slow down, False otherwise
        """
        if "action: slow down" in vlm_text.lower():
            return True
        return False

    def apply_speed_control(self, vehicle_id, speed_factor=0.75, duration_ticks=60):
        """
        Apply speed reduction to a vehicle for a specified duration.
        
        Parameters
        ----------
        vehicle_id : str
            ID of the vehicle to control
        speed_factor : float
            Factor to multiply current speed by (0.75 = 3/4 speed)
        duration_ticks : int
            How many ticks to maintain speed control
        """
        if vehicle_id not in self.veh_dict:
            print(f"[SceneManager] Cannot apply speed control - vehicle {vehicle_id} not found")
            return
        
        vehicle = self.veh_dict[vehicle_id]['actor']
        current_velocity = vehicle.get_velocity()
        
        # Calculate the reduced velocity once
        reduced_velocity = carla.Vector3D(
            x=current_velocity.x * speed_factor,
            y=current_velocity.y * speed_factor,
            z=current_velocity.z * speed_factor
        )
        
        self.speed_controlled_vehicles[vehicle_id] = {
            'start_tick': self.cur_count,
            'target_velocity': reduced_velocity,  # Store the fixed target velocity
            'duration': duration_ticks
        }
        
        print(f"[SceneManager] Vehicle {vehicle_id} under speed control (factor: {speed_factor:.2f}, duration: {duration_ticks} ticks)")

    def update_speed_controlled_vehicles(self):
        """
        Update all vehicles currently under speed control.
        """
        vehicles_to_release = []
        
        for vehicle_id, control_data in self.speed_controlled_vehicles.items():
            if vehicle_id not in self.veh_dict:
                vehicles_to_release.append(vehicle_id)
                continue
                
            vehicle = self.veh_dict[vehicle_id]['actor']
            ticks_elapsed = self.cur_count - control_data['start_tick']
            
            if ticks_elapsed < control_data['duration']:
                # Apply the same fixed reduced velocity every tick
                vehicle.set_target_velocity(control_data['target_velocity'])
                print(f"[SceneManager] Applying speed reduction to vehicle {vehicle_id}")
            else:
                # Release speed control
                print(f"[SceneManager] Releasing speed control for vehicle {vehicle_id}")
                vehicles_to_release.append(vehicle_id)
        
        # Clean up completed speed controls
        for vehicle_id in vehicles_to_release:
            if vehicle_id in self.speed_controlled_vehicles:
                del self.speed_controlled_vehicles[vehicle_id]

    def tick(self):
        """
        Spawn the vehicle to the correct position
        """
        if self.cur_count >= len(self.timestamps):
            return False

        cur_timestamp = self.timestamps[self.cur_count]
        cur_database = self.database[cur_timestamp]

        for i, (cav_id, cav_yml) in enumerate(cur_database.items()):
            cav_content = load_yaml(cav_yml['yaml'])

            if cav_id not in self.veh_dict:
                self.spawn_cav(cav_id, cav_content, cur_timestamp)
            else:
                self.move_vehicle(cav_id,
                                cur_timestamp,
                                self.structure_transform_cav(
                                    cav_content['true_ego_pos']))
            if cav_id in self.stopped_vehicles or cav_id in self.steering_controlled_vehicles or cav_id in self.speed_controlled_vehicles:
                self.veh_dict[cav_id]['cur_count'] = cur_timestamp  # update manually

            self.veh_dict[cav_id]['cav'] = True

            # Spawn sensor manager if not yet created
            if 'sensor_manager' not in self.veh_dict[cav_id]:
                self.veh_dict[cav_id]['sensor_manager'] = \
                    SensorManager(cav_id, self.veh_dict[cav_id],
                                self.world, self.scenario_params['sensor'],
                                self.output_root)

            # Set spectator on first CAV
            if i == 0:
                transform = self.structure_transform_cav(
                    cav_content['true_ego_pos'])
                self.spectator.set_transform(
                    carla.Transform(transform.location + carla.Location(z=70),
                                    carla.Rotation(pitch=-90)))

        # Then spawn or move all background vehicles (excluding any CAVs)
        for cav_id, cav_yml in cur_database.items():
            cav_content = load_yaml(cav_yml['yaml'])
        
            for bg_veh_id, bg_veh_content in cav_content['vehicles'].items():
                if str(bg_veh_id) in self.cav_id_list:
                    continue  # skip: this is a CAV, already handled

                if str(bg_veh_id) not in self.veh_dict:
                    self.spawn_bg_vehicles(bg_veh_id,
                                        bg_veh_content,
                                        cur_timestamp)
                else:
                    self.move_vehicle(str(bg_veh_id),
                                    cur_timestamp,
                                    self.structure_transform_bg_veh(
                                        bg_veh_content['location'],
                                        bg_veh_content['angle']))

        # vlm_path = self.get_vlm_file_path(cur_timestamp)
        # if os.path.exists(vlm_path):
        #     with open(vlm_path, 'r') as f:
        #         vlm_text = f.read()
        #     stop_flag = self.should_stop_based_on_vlm(vlm_text)
        #     if stop_flag:
        #         cav_to_stop = "243"
        #         if cav_to_stop in self.veh_dict and cav_to_stop not in self.stopped_vehicles:
        #             vehicle = self.veh_dict[cav_to_stop]['actor']
        #             vehicle.set_autopilot(False)
        #             vehicle.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0))
        #             self.stopped_vehicles.add(cav_to_stop)
        #             print(f"[SceneManager] CAV {cav_to_stop} stopped due to VLM output")

        #         cav_to_stop = "2488"
        #         if cav_to_stop in self.veh_dict and cav_to_stop not in self.stopped_vehicles:
        #             vehicle = self.veh_dict[cav_to_stop]['actor']
        #             vehicle.set_autopilot(False)
        #             vehicle.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0))
        #             self.stopped_vehicles.add(cav_to_stop)
        #             print(f"[SceneManager] CAV {cav_to_stop} stopped due to VLM output")

        # ego_cav_comms = "1996"
        # ego_goal_filepath = "/home/po-han/Downloads/OPV2V/test/2021_08_20_21_10_24/1996"

        # comms = self.get_cav_communications(ego_cav_comms)
        # ego_goal = self.get_ego_goal(ego_goal_filepath, cur_timestamp)

        # accepted_cavs = self.filter_accepted_cavs(ego_cav_comms, comms, ego_goal,epsilon=50)
        # #self.calculate_bandwidth_metrics(accepted_cavs, cur_timestamp)

        # self.log_accepted_cavs(cur_timestamp, accepted_cavs)


        # if accepted_cavs:
        #     print("Accepted_CAVS",accepted_cavs)

        vlm_merge_path = self.get_vlm_merge_file_path(cur_timestamp)
        if os.path.exists(vlm_merge_path):
            try:
                with open(vlm_merge_path, 'r') as f:
                    vlm_text = f.read().strip()
                merge_flag = self.should_merge_based_on_vlm(vlm_text)
                if merge_flag:
                    print(f"[SceneManager] Timestamp {cur_timestamp}: MERGE")

                    merging_vehicle_id = "1996"
                
                    if (merging_vehicle_id in self.veh_dict and 
                        merging_vehicle_id not in self.steering_controlled_vehicles):
                        # Positive steering = right turn, negative = left turn
                        self.apply_steering_control(
                            vehicle_id=merging_vehicle_id,
                            steering_angle=0.25,    # Adjust for merge intensity
                            duration_ticks=12,     # How long to steer
                            throttle=1          # Maintain forward speed
                        )

                slowdown_flag = self.should_slow_down_based_on_vlm(vlm_text)
                if slowdown_flag:
                    print(f"[SceneManager] Timestamp {cur_timestamp}: SLOW DOWN")
                    slowing_vehicle_id = "1996"
                    if (slowing_vehicle_id in self.veh_dict and 
                        slowing_vehicle_id not in self.speed_controlled_vehicles and
                        slowing_vehicle_id not in self.steering_controlled_vehicles):  # Don't conflict with steering
                        # self.apply_speed_control(
                        #     vehicle_id=slowing_vehicle_id,
                        #     speed_factor=0.75,  # Reduce to 75% of current speed
                        #     duration_ticks=30   # Slow down for 30 ticks
                        # )
                        self.speed_controlled_vehicles[slowing_vehicle_id] = {
                        'speed_factor':0.7
                        }
                        print(self.speed_controlled_vehicles)
                        
            except Exception as e:
                print(f"[SceneManager] Error reading VLM merge file {vlm_merge_path}: {e}")

        self.update_steering_controlled_vehicles()
        # self.update_speed_controlled_vehicles()

        self.cur_count += 1
        self.destroy_vehicle(cur_timestamp)
        self.world.tick()

        self.sensor_dumping(cur_timestamp)
        self.map_dumping()

        #if self.cur_count % 10 == 0:
            #self.save_bandwidth_metrics()

        return True


    def map_dumping(self):
        """
        Dump bev map related.

        Parameters
        ----------
        """
        for veh_id, veh_content in self.veh_dict.items():
            if 'cav' in veh_content:
                self.map_manager.run_step(veh_id, veh_content, self.veh_dict)
        
    def sensor_dumping(self, cur_timestamp):
        for veh_id, veh_content in self.veh_dict.items():
            if 'sensor_manager' in veh_content:
                veh_content['sensor_manager'].run_step(cur_timestamp)

    def spawn_cav(self, cav_id, cav_content, cur_timestamp):
        """
        Spawn the cav based on current content.

        Parameters
        ----------
        cav_id : str
            The saved cav_id.

        cav_content : dict
            The information in the cav's folder.

        cur_timestamp : str
            This is used to judge whether this vehicle has been already
            called in this timestamp.
        """

        # cav always use lincoln
        model = 'vehicle.lincoln.mkz_2017'

        blueprint_library = self.world.get_blueprint_library()
        cav_bp = blueprint_library.find(model)
        # cav is always green
        color = '0, 0, 255'
        cav_bp.set_attribute('color', color)

        # Set role to hero for metrics manager
        cav_bp.set_attribute('role_name', 'hero')

        cur_pose = cav_content['true_ego_pos']
        # convert to carla needed format
        cur_pose = self.structure_transform_cav(cur_pose)

        # spawn the vehicle
        vehicle = \
            self.world.try_spawn_actor(cav_bp, cur_pose)
        
        while not vehicle:
            cur_pose.location.z += 0.01
            vehicle = \
                self.world.try_spawn_actor(cav_bp, cur_pose)

        #For metrics manager
        role = vehicle.attributes.get('role_name', 'unknown')
        print(f"[SceneManager] CAV {cav_id}  -->  CARLA actor ID = {vehicle.id}, role: {role}")

        self.veh_dict.update({str(cav_id): {
            'cur_pose': cur_pose,
            'model': model,
            'color': color,
            'actor_id': vehicle.id,
            'actor': vehicle,
            'cur_count': cur_timestamp
        }})

    def spawn_bg_vehicles(self, bg_veh_id, bg_veh_content, cur_timestamp):
        """
        Spawn the background vehicle.

        Parameters
        ----------
        bg_veh_id : str
            The id of the bg vehicle.
        bg_veh_content : dict
            The contents of the bg vehicle
        cur_timestamp : str
            This is used to judge whether this vehicle has been already
            called in this timestamp.
        """
        # retrieve the blueprint library
        blueprint_library = self.world.get_blueprint_library()

        cur_pose = self.structure_transform_bg_veh(bg_veh_content['location'],
                                                   bg_veh_content['angle'])
        if str(bg_veh_id) in self.cav_id_list:
            model = 'vehicle.lincoln.mkz_2017'
            veh_bp = blueprint_library.find(model)
            color = '0, 0, 255'
        else:
            model = find_blue_print(bg_veh_content['extent'])
            if not model:
                print('model net found for %s' % bg_veh_id)
            veh_bp = blueprint_library.find(model)

            color = random.choice(
                veh_bp.get_attribute('color').recommended_values)

        veh_bp.set_attribute('color', color)

        # spawn the vehicle
        vehicle = \
            self.world.try_spawn_actor(veh_bp, cur_pose)

        while not vehicle:
            cur_pose.location.z += 0.01
            vehicle = \
                self.world.try_spawn_actor(veh_bp, cur_pose)

        #For metrics manager
        role = vehicle.attributes.get('role_name', 'unknown')
        print(f"[SceneManager] CAV {bg_veh_id}  -->  CARLA actor ID = {vehicle.id}, role: {role}")

        self.veh_dict.update({str(bg_veh_id): {
            'cur_pose': cur_pose,
            'model': model,
            'color': color,
            'actor_id': vehicle.id,
            'actor': vehicle,
            'cur_count': cur_timestamp
        }})
    def move_vehicle(self, veh_id, cur_timestamp, transform):
        if veh_id in self.stopped_vehicles or veh_id in self.steering_controlled_vehicles:
            return
        if self.veh_dict[veh_id]['cur_count'] == cur_timestamp:
            return

        vehicle = self.veh_dict[veh_id]['actor']
        prev_pose = self.veh_dict[veh_id]['cur_pose']
        dt = self.collection_params['world']['fixed_delta_seconds']

        dx = transform.location.x - prev_pose.location.x
        dy = transform.location.y - prev_pose.location.y
        dz = transform.location.z - prev_pose.location.z

        vx, vy, vz = dx/dt, dy/dt, dz/dt
        new_speed = np.linalg.norm([vx, vy, vz])

        if veh_id in self.speed_controlled_vehicles:
            control_data = self.speed_controlled_vehicles[veh_id]
            speed_factor = control_data['speed_factor']
            print(vx," vy ",vy)
            vx *=speed_factor
            vy *=speed_factor
            vz *= 1
            
            vehicle.set_target_velocity(carla.Vector3D(vx, vy, vz))

            # Rotation correction only if still aligned
            cur_loc = vehicle.get_transform().location
            dist = cur_loc.distance(transform.location)
            

            self.veh_dict[veh_id]['cur_count'] = cur_timestamp
            self.veh_dict[veh_id]['cur_pose'] = transform
            print(f"[SceneManager] Applying speed reduction to vehicle {veh_id} in move_vehicle")
            return

        # Defaults
        scale = 1.0
        boost_range = None

        if self.scene_name in self.velocity_scale and veh_id in self.velocity_scale[self.scene_name]:
            cfg = self.velocity_scale[self.scene_name][veh_id]
            if isinstance(cfg, dict):
                scale = cfg.get("scale", 1.0)
                boost_range = cfg.get("boost_range", None)
            else:
                scale = cfg

        vx *= scale
        vy *= scale
        vz *= scale

        # --- Boost rule: if inside boost_range, prevent slowdown ---
        if boost_range:
            start, end = boost_range
            if start <= self.cur_count <= end:
                prev_vel = vehicle.get_velocity()
                prev_speed = np.linalg.norm([prev_vel.x, prev_vel.y, prev_vel.z])
                # If new speed < previous speed → freeze velocity
                if new_speed < prev_speed:
                    vx, vy, vz = prev_vel.x*1.007, prev_vel.y*1.07, prev_vel.z

        # Apply through physics
        vehicle.set_target_velocity(carla.Vector3D(vx, vy, vz))

        # Rotation correction only if still aligned
        cur_loc = vehicle.get_transform().location
        dist = cur_loc.distance(transform.location)
        if dist < 1 and veh_id not in self.velocity_scale.get(self.scene_name, {}):
            vehicle.set_transform(transform)

        self.veh_dict[veh_id]['cur_count'] = cur_timestamp
        self.veh_dict[veh_id]['cur_pose'] = transform

        # before boost
    # def move_vehicle(self, veh_id, cur_timestamp, transform):
    #     if veh_id in self.stopped_vehicles:
    #         return
    #     if self.veh_dict[veh_id]['cur_count'] == cur_timestamp:
    #         return

    #     vehicle = self.veh_dict[veh_id]['actor']
    #     prev_pose = self.veh_dict[veh_id]['cur_pose']
    #     dt = self.collection_params['world']['fixed_delta_seconds']

    #     dx = transform.location.x - prev_pose.location.x
    #     dy = transform.location.y - prev_pose.location.y
    #     dz = transform.location.z - prev_pose.location.z

    #     vx, vy, vz = dx/dt, dy/dt, dz/dt

    #     # Check if scaling is needed
    #     scale = 1.0
    #     if self.scene_name in self.velocity_scale and veh_id in self.velocity_scale[self.scene_name]:
    #         scale = self.velocity_scale[self.scene_name][veh_id]

    #     vx *= scale
    #     vy *= scale
    #     vz *= scale

    #     # Apply rotation from log but keep physics location
    #     # Apply velocity through physics (collisions enabled)
    #     vehicle.set_target_velocity(carla.Vector3D(vx, vy, vz))

    #     # --- Rotation handling ---
    #     # Only force rotation if the car hasn't been disturbed (close to log location)
    #     cur_loc = vehicle.get_transform().location
    #     dist = cur_loc.distance(transform.location)

    #     if dist < 1 and veh_id not in self.velocity_scale.get(self.scene_name, {}):  # still close to replay trajectory
    #         self.veh_dict[veh_id]['actor'].set_transform(transform)
    #     # else: physics takes over completely (rotation + position)


    #     self.veh_dict[veh_id]['cur_count'] = cur_timestamp
    #     self.veh_dict[veh_id]['cur_pose'] = transform

    # def move_vehicle(self, veh_id, cur_timestamp, transform):
    #     if veh_id in self.stopped_vehicles:
    #         return
    #     if self.veh_dict[veh_id]['cur_count'] == cur_timestamp:
    #         return

    #     vehicle = self.veh_dict[veh_id]['actor']

    #     if self.scene_name in self.velocity_scale and veh_id in self.velocity_scale[self.scene_name]:
    #         scale = self.velocity_scale[self.scene_name][veh_id]

    #         # get last pose (previous tick) and new pose (current tick)
    #         prev_pose = self.veh_dict[veh_id]['cur_pose']
    #         dt = self.collection_params['world']['fixed_delta_seconds']

    #         dx = transform.location.x - prev_pose.location.x
    #         dy = transform.location.y - prev_pose.location.y
    #         dz = transform.location.z - prev_pose.location.z

    #         vx, vy, vz = dx/dt, dy/dt, dz/dt
    #         vx *= scale
    #         vy *= scale
    #         vz *= scale

    #         # apply scaled velocity through physics
    #         vehicle.set_target_velocity(carla.Vector3D(vx, vy, vz))

    #         # keep rotation from log but DO NOT teleport location
    #         cur_rot = transform.rotation
    #         cur_loc = vehicle.get_transform().location  # use current physics location
    #         vehicle.set_transform(carla.Transform(cur_loc, cur_rot))

    #     else:
    #         # default: just teleport as before
    #         vehicle.set_transform(transform)

    #     self.veh_dict[veh_id]['cur_count'] = cur_timestamp
    #     self.veh_dict[veh_id]['cur_pose'] = transform


    def close(self):
        self.world.apply_settings(self.origin_settings)
        actor_list = self.world.get_actors()
        for actor in actor_list:
            actor.destroy()
        self.map_manager.destroy()
        self.sensor_destory()

        self.client.stop_recorder()
        print("[SceneManager] Recording stopped")

    def sensor_destory(self):
        for veh_id, veh_content in self.veh_dict.items():
            if 'sensor_manager' in veh_content:
                veh_content['sensor_manager'].destroy()

    def destroy_vehicle(self, cur_timestamp):
        destroy_list = []
        for veh_id, veh_content in self.veh_dict.items():
            if veh_id in self.stopped_vehicles or veh_id in self.steering_controlled_vehicles or veh_id in self.speed_controlled_vehicles:
                continue  # <--- Don't destroy stopped vehicles!
            if veh_content['cur_count'] != cur_timestamp:
                veh_content['actor'].destroy()
                destroy_list.append(veh_id)

        for veh_id in destroy_list:
            self.veh_dict.pop(veh_id)


    def structure_transform_cav(self, pose):
        """
        Convert the pose saved in list to transform format.

        Parameters
        ----------
        pose : list
            x, y, z, roll, yaw, pitch

        Returns
        -------
        carla.Transform
        """
        cur_pose = carla.Transform(carla.Location(x=pose[0],
                                                  y=pose[1],
                                                  z=pose[2]),
                                   carla.Rotation(roll=pose[3],
                                                  yaw=pose[4],
                                                  pitch=pose[5]))

        return cur_pose

    @staticmethod
    def structure_transform_bg_veh(location, rotation):
        """
        Convert the location and rotation in list to carla transform format.

        Parameters
        ----------
        location : list
        rotation : list
        Returns
        -------
        carla.Transform
        """
        cur_pose = carla.Transform(carla.Location(x=location[0],
                                                  y=location[1],
                                                  z=location[2]),
                                   carla.Rotation(roll=rotation[0],
                                                  yaw=rotation[1],
                                                  pitch=rotation[2]))

        return cur_pose

    @staticmethod
    def extract_timestamps(yaml_files):
        """
        Given the list of the yaml files, extract the mocked timestamps.

        Parameters
        ----------
        yaml_files : list
            The full path of all yaml files of ego vehicle

        Returns
        -------
        timestamps : list
            The list containing timestamps only.
        """
        timestamps = []

        for file in yaml_files:
            res = file.split('/')[-1]

            timestamp = res.replace('.yaml', '')
            timestamps.append(timestamp)

        return timestamps

    @staticmethod
    def set_weather(weather_settings):
        """
        Set CARLA weather params.

        Parameters
        ----------
        weather_settings : dict
            The dictionary that contains all parameters of weather.

        Returns
        -------
        The CARLA weather setting.
        """
        weather = carla.WeatherParameters(
            sun_altitude_angle=weather_settings['sun_altitude_angle'],
            cloudiness=weather_settings['cloudiness'],
            precipitation=weather_settings['precipitation'],
            precipitation_deposits=weather_settings['precipitation_deposits'],
            wind_intensity=weather_settings['wind_intensity'],
            fog_density=weather_settings['fog_density'],
            fog_distance=weather_settings['fog_distance'],
            fog_falloff=weather_settings['fog_falloff'],
            wetness=weather_settings['wetness']
        )
        return weather
