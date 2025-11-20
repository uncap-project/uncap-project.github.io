import carla
import time

# Connect to the CARLA simulator
client = carla.Client('localhost', 2000)  # Adjust IP and port if necessary
client.set_timeout(10.0)  # Set a timeout for connection

for scene_num in [3, 5, 6, 7, 8, 9]:
    try:
        # Specify the path to your CARLA log file
        log_file_path = f"/home/po-han/Desktop/Projects/OpenCOOD/logreplay/scenario/metric_record/recording-scene{scene_num}.log" # Replace with your actual log file name and path

        # Replay the file
        # Parameters: filename, start_time (seconds), duration (seconds), camera_actor_id
        # start_time: positive from beginning, negative from end (-2 = last 2 seconds)
        # duration: 0 for entire recording, or specific duration in seconds
        # camera_actor_id: ID of the actor to follow, 0 for free spectator camera
        
        if scene_num == 3:
            track_id = 8690
        elif scene_num == 5:
            track_id = 3152
        elif scene_num == 7:
            track_id = 2
        else:
            track_id = 1

        client.set_replayer_time_factor(2.0)
        
        res = client.replay_file(log_file_path, 0, 0, track_id)
        print(res)
        print(f"Replaying {log_file_path}...")
        # /home/po-han/Desktop/Projects/OpenCOOD/logreplay/scenario/metric_record/playback_log.py

        # Optional: Keep the simulation running for a bit to observe the replay
        # In a real-time scenario, you might have a loop with world.tick()
        time.sleep(20) # Replay for 30 seconds, adjust as needed

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        print("Replay finished or an error occurred.")
        # You might want to reset the world or perform other cleanup here
        # For example, client.stop_recorder() if you were also recording