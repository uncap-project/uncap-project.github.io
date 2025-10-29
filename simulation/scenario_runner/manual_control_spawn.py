import carla, random

client = carla.Client("127.0.0.1", 2000)
client.set_timeout(10.0)
client.load_world("Town07")
world = client.get_world()


bp = world.get_blueprint_library().filter("vehicle.tesla.model3")[0]
bp.set_attribute("role_name", "hero")

spawn_points = world.get_map().get_spawn_points()
vehicle = None

for sp in spawn_points:
    vehicle = world.try_spawn_actor(bp, sp)
    if vehicle is not None:
        print("Spawned hero at:", sp.location)
        break

if vehicle is None:
    print("⚠️ Failed to spawn vehicle at all spawn points.")
print("Current map:", world.get_map().name)