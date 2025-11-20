import os
from collections import OrderedDict

from opencood.hypes_yaml.yaml_utils import load_yaml
from logreplay.scenario.scene_manager import SceneManager

from metrics_manager import MetricsManager


class ScenariosManager:
    """
    Format all scenes in a structured way.

    Parameters
    ----------
    scenario_params: dict
        Overall parameters for the replayed scenes.

    Attributes
    ----------

    """

    def __init__(self, scenario_params):
        # this defines carla world sync mode, weather, town name, and seed.
        self.scene_params = scenario_params

        # e.g. /opv2v/data/train
        root_dir = self.scene_params['root_dir']

        # first load all paths of different scenarios
        scenario_folders = [
            '/home/po-han/Downloads/OPV2V/test/2021_08_23_21_47_19'
        ]

        self.scenario_database = OrderedDict()

        """
        scenario_folders = [
            '/home/po-han/Downloads/OPV2V/train/2021_08_23_20_47_11',
            '/home/po-han/Downloads/OPV2V/validate/2021_08_21_17_30_41'
        ]
        """
        #scenario for early testing

        # loop over all scenarios
        for (i, scenario_folder) in enumerate(scenario_folders):  #temporarily run one
            scene_name = os.path.split(scenario_folder)[-1]
            self.scenario_database.update({scene_name: OrderedDict()})

            # load the collection yaml file
            protocol_yml = [x for x in os.listdir(scenario_folder)
                            if x.endswith('.yaml')]
            try:
                collection_params = load_yaml(os.path.join(scenario_folder,
                                                           protocol_yml[0]))
            except:
                print("Theres a bug here which you have to fix")
                print("by deleting ./additional from the input path")
                breakpoint()

            # create the corresponding scene manager
            cur_sg = SceneManager(scenario_folder,
                                  scene_name,
                                  collection_params,
                                  scenario_params)
            self.scenario_database[scene_name].update({'scene_manager':
                                                       cur_sg})

    def tick(self):

        for scene_name, scene_content in self.scenario_database.items():
            print(f'Log replay: {scene_name}')
            scene_manager = scene_content['scene_manager']
            run_flag = True

            # Start CARLA simulator
            scene_manager.start_simulator()

            # 🚀 SET UP METRICS MANAGER
            metrics_config = '/home/po-han/simulation/scenario_runner/srunner/tools/data/metrics_config.xml'
            world = scene_manager.world  # assuming your SceneManager has .world
            metrics_manager = MetricsManager(metrics_config, world)
            metrics_manager.set_scenario_name(scene_name)
            metrics_manager.start()

            # Run the playback
            while run_flag:
                run_flag = scene_manager.tick()

            # ✅ STOP METRICS & SAVE RESULTS
            metrics_manager.stop()
            metrics_manager.compute_final_results()
            metrics_output_path = os.path.join(
                '/home/po-han/Desktop/Projects/OpenCOOD/logreplay/scenario/metric_results', f'{scene_name}_metrics.json'
            )
            metrics_manager.write_to_file(metrics_output_path)

            print(f"Metrics saved to: {metrics_output_path}")

            # Close simulator
            scene_manager.close()



if __name__ == '__main__':
    from opencood.hypes_yaml.yaml_utils import load_yaml
    # print current working directory
    print(os.getcwd())
    scene_params = load_yaml('./logreplay/hypes_yaml/replay.yaml')
    scenarion_manager = ScenariosManager(scenario_params=scene_params)
    scenarion_manager.tick()
    print('test passed')



