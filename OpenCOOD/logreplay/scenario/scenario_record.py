# scenario_record.py
import os
import sys
from collections import OrderedDict
import carla
from opencood.hypes_yaml.yaml_utils import load_yaml
from logreplay.scenario.scene_manager import SceneManager

# Import scene_config from the OPV2V directory
sys.path.insert(0, os.path.abspath('../../../OPV2V'))
from scene_config import get_scene_config, list_available_scenes


class ScenariosManager:
    def __init__(self, scenario_params, scene_number):
        """
        Initialize the scenarios manager with a specific scene.
        
        Parameters
        ----------
        scenario_params : dict
            The scenario parameters from replay.yaml
        scene_number : int or float
            The scene number to load (1, 2, 3, 4, 4.5, etc.)
        """
        self.scene_params = scenario_params
        
        # Get scene configuration
        self.scene_config = get_scene_config(scene_number)
        print(f"\n{'='*60}")
        print(f"Loading {self.scene_config['name']}")
        print(f"Folder: {self.scene_config['folder']}")
        print(f"Type: {self.scene_config['type']}")
        print(f"Ego CAV: {self.scene_config['ego_cav']}")
        print(f"Helper CAVs: {self.scene_config['helper_cavs']}")
        print(f"{'='*60}\n")
        
        # Use the configured folder
        self.scenario_folders = [self.scene_config['folder']]
        self.scenario_database = OrderedDict()
        
        for scenario_folder in self.scenario_folders:
            scene_name = os.path.basename(scenario_folder)
            self.scenario_database[scene_name] = OrderedDict()
            
            protocol_yml = [x for x in os.listdir(scenario_folder) if x.endswith('.yaml')]
            collection_params = load_yaml(os.path.join(scenario_folder, protocol_yml[0]))
            
            # Pass scene config to SceneManager
            cur_sg = SceneManager(
                scenario_folder, 
                scene_name, 
                collection_params, 
                scenario_params,
                scene_config=self.scene_config  # Pass the config
            )
            self.scenario_database[scene_name]['scene_manager'] = cur_sg
    
    def tick(self):
        for scene_name, scene_content in self.scenario_database.items():
            print(f'Log replay: {scene_name}')
            scene_manager = scene_content['scene_manager']
            run_flag = True
            
            # Start the simulator for this scenario
            scene_manager.start_simulator()
            
            # Run scenario tick loop
            while run_flag:
                run_flag = scene_manager.tick()
            
            # Close the simulator cleanly
            scene_manager.close()


if __name__ == '__main__':
    print("Working dir:", os.getcwd())
    
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("\nUsage: python scenario_record.py <scene_number>")
        print("\nExample: python scenario_record.py 2")
        print()
        list_available_scenes()
        sys.exit(1)
    
    try:
        scene_number = float(sys.argv[1])
    except ValueError:
        print(f"Error: Invalid scene number '{sys.argv[1]}'. Must be a number.")
        sys.exit(1)
    
    # Load scenario params
    scene_params = load_yaml('./logreplay/hypes_yaml/replay.yaml')
    
    # Create and run scenario manager
    scenario_manager = ScenariosManager(
        scenario_params=scene_params,
        scene_number=scene_number
    )
    scenario_manager.tick()
    
    print('Scenario playback with recording complete.')