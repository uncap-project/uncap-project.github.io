import os
from collections import OrderedDict
import carla

from opencood.hypes_yaml.yaml_utils import load_yaml
from logreplay.scenario.scene_manager import SceneManager

class ScenariosManager:
    def __init__(self, scenario_params):
        self.scene_params = scenario_params
        # Hardcode your single scenario folder here:
        self.scenario_folders = [
            "../OPV2V/test/2021_08_23_21_47_19"
        ]
        self.scenario_database = OrderedDict()
        import logreplay.scenario.scene_manager
        print("scene manager file:",logreplay.scenario.scene_manager.__file__)

        for scenario_folder in self.scenario_folders:
            scene_name = os.path.basename(scenario_folder)
            self.scenario_database[scene_name] = OrderedDict()

            protocol_yml = [x for x in os.listdir(scenario_folder) if x.endswith('.yaml')]
            collection_params = load_yaml(os.path.join(scenario_folder, protocol_yml[0]))

            cur_sg = SceneManager(scenario_folder, scene_name, collection_params, scenario_params)
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
    scene_params = load_yaml('./logreplay/hypes_yaml/replay.yaml')
    scenarion_manager = ScenariosManager(scenario_params=scene_params)
    scenarion_manager.tick()
    print('Scenario playback with recording complete.')
