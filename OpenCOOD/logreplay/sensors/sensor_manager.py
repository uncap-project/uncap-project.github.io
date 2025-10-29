# -*- coding: utf-8 -*-
"""
Sensor Manager for each cav
"""
# Author: Runsheng Xu <rxx3386@ucla.edu>
# License: TDG-Attribution-NonCommercial-NoDistrib
import importlib
import os
from collections import OrderedDict
import carla


class SensorManager:
    def __init__(self, agent_id,
                 vehicle_content,
                 world, config_yaml, output_root):

        self.agent_id = agent_id
        self.output_root = output_root
        self.vehicle = vehicle_content['actor']
        self.world = world
        self.sensor_list = []
        self.sensor_meta = OrderedDict()
        self.sensor_cfg = config_yaml

        unique_collision_id = 0
        for sensor_content in config_yaml['sensor_list']:
            sensor = None
            sensor_name = sensor_content['name']
            sensor_filename = "logreplay.sensors." + sensor_name
            sensor_lib = importlib.import_module(sensor_filename)
            target_sensor_name = sensor_name.replace('_', '')

            for name, cls in sensor_lib.__dict__.items():
                if name.lower() == target_sensor_name.lower():
                    sensor = cls

            assert sensor is not None
            if 'args' in sensor_content:
                sensor_instance = sensor(self.agent_id,
                                         self.vehicle,
                                         self.world,
                                         sensor_content['args'],
                                         None)
            else:
                sensor_content['unique_id'] = unique_collision_id
                unique_collision_id += 1
                sensor_instance = sensor(self.agent_id,
                                         self.vehicle,
                                         self.world,
                                         sensor_content,
                                         None)

            self.sensor_list.append(sensor_instance)

        self._spawn_instance_seg_camera()

    def run_step(self, cur_timestamp):
        for sensor_instance in self.sensor_list:
            # Skip raw CARLA sensor actors (they don’t have `.name`)
            if not hasattr(sensor_instance, "name"):
                continue

            sensor_name = sensor_instance.name
            sensor_instance.visualize_data()

            meta_info = sensor_instance.tick()
            self.sensor_meta.update({sensor_name: meta_info})

            output_folder = os.path.join(self.output_root, self.agent_id)
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
            sensor_instance.data_dump(output_folder, cur_timestamp)


    def destroy(self):
        for sensor_instance in self.sensor_list:
            sensor_instance.destroy()

    def _spawn_instance_seg_camera(self):
        #print("S")
        cfg = self.sensor_cfg['instance_seg']

        bp = self.world.get_blueprint_library().find('sensor.camera.instance_segmentation')
        bp.set_attribute('image_size_x', str(cfg['image_size_x']))
        bp.set_attribute('image_size_y', str(cfg['image_size_y']))
        bp.set_attribute('fov', str(cfg['fov']))
        bp.set_attribute('sensor_tick', str(cfg['sensor_tick']))

        t = cfg['transform']
        transform = carla.Transform(
            carla.Location(x=t[0], y=t[1], z=t[2]),
            carla.Rotation(roll=t[3], pitch=t[4], yaw=t[5])
        )

        cam = self.world.spawn_actor(bp, transform, attach_to=self.vehicle)
        save_root = os.path.join(self.output_root, 'instance_seg', str(self.agent_id))
        os.makedirs(save_root, exist_ok=True)
        cam.listen(lambda img, r=save_root: (
            print(f"[InstanceSegCam] Got frame {img.frame}"),
            img.save_to_disk(os.path.join(r, f'{img.frame:06d}.png'))
        ))
        self.sensor_list.append(cam)
