#!/usr/bin/env python3
import carla
import time

LOG_PATH = "/home/po-han/Desktop/Projects/OpenCOOD/logreplay/scenario/metric_record/recording-scene6.log"

client = carla.Client("localhost", 2000)
client.set_timeout(10.0)

# 1. Start replaying
client.replay_file(LOG_PATH, 0, 0, 0)

# 2. Give the server a moment to spawn everything
time.sleep(0.5)

# 3. List vehicles and their role
world = client.get_world()
vehicles = world.get_actors().filter('vehicle.*')
print(f"Found {len(vehicles)} vehicles in recorder snapshot:")
for v in vehicles:
    role = v.attributes.get('role_name', 'NOT_SET')
    print(f"  ID {v.id:4d}  type {v.type_id:35s}  role: {role}")

# 4. Stop the replay (False = destroy replayed actors)
client.stop_replayer(False)