# scene_config.py


SCENE_CONFIGS = {
    1: {
        'name': 'Scene 1',
        'set': 'validate',
        'id': '2021_08_21_17_30_41',
        'folder': './validate/2021_08_21_17_30_41',
        'type': 'stop',
        'ego_cav': '2488',
        'helper_cavs': ['2506'],
        'vlm_base_path': './structured_format/2021_08_21_17_30_41',
        'ego_goal_filepath': './validate/2021_08_21_17_30_41/2488',
        'eval_intention': 'would like to move north',
        'eval_facing': 'north',
        'intersection_coordinates': None,
    },
    2: {
        'name': 'Scene 2',
        'set': 'test',
        'id': '2021_08_23_21_47_19',
        'folder': './test/2021_08_23_21_47_19',
        'type': 'stop',
        'ego_cav': '243',
        'helper_cavs': ['234'],
        'vlm_base_path': './structured_format/2021_08_23_21_47_19',
        'ego_goal_filepath': './test/2021_08_23_21_47_19/243',
        'intersection_coordinates': [35, 66, 4, 30],
        'eval_intention': 'would like to move north',
        'eval_facing': 'north',
    },
    3: {
        'name': 'Scene 3',
        'set': 'test',
        'id': '2021_08_23_15_19_19',
        'folder': './test/2021_08_23_15_19_19',
        'type': 'stop',
        'ego_cav': '8690',
        'helper_cavs': ['8699'],
        'vlm_base_path': './structured_format/2021_08_23_15_19_19',
        'ego_goal_filepath': './test/2021_08_23_15_19_19/8690',
        'intersection_coordinates': [-262, -250, -258, -240],
        'eval_intention': 'would like to move west',
        'eval_facing': 'west',
    },
    4: {
        'name': 'Scene 4 (Original)',
        'set': 'test',
        'id': '2021_08_20_21_10_24',
        'folder': './test/2021_08_20_21_10_24',
        'type': 'merge',
        'ego_cav': '1996',
        'helper_cavs': ['2014'],
        'intersection_coordinates': None,
        'merge_params': {
            'steering_angle': 0.4,
            'duration_ticks': 15,
            'throttle': 1.0
        },
        'vlm_base_path': './structured_format/2021_08_20_21_10_24',
        'vlm_merge_path': './vlm_query_testing/plain_output/scene4_decisions',
        'ego_goal_filepath': './test/2021_08_20_21_10_24/1996',
        'eval_intention': "would like to merge into the lane to its right (the one directly North) once it is on the highway",
        'eval_facing': 'west'
    },
    # LEAVING OUT SCENE 4.5 SPECIAL CASE
    # 4.5: {
    #     'name': 'Scene 4.5 (Fast)',
    #     'folder': '../../../OPV2V/test/2021_08_20_21_10_24_fast',
    #     'type': 'merge',
    #     'ego_cav': '1996',
    #     'helper_cavs': ['2014'],
    #     'merge_params': {
    #         'steering_angle': 0.4,
    #         'duration_ticks': 15,
    #         'throttle': 1.0
    #     },
    #     'vlm_merge_path': '../../../OPV2V/vlm_query_testing/plain_output/scene4_decisions',
    #     'ego_goal_filepath': '../../../OPV2V/test/2021_08_20_21_10_24_fast/1996',
    # },
    5: {
        'name': 'Scene 5',
        'set': 'train',
        'id': '2021_08_22_06_43_37',
        'folder': './train/2021_08_22_06_43_37',
        'type': 'stop',
        'ego_cav': '3152',
        'helper_cavs': ['3170'],
        'vlm_base_path': './structured_format/2021_08_22_06_43_37',
        'ego_goal_filepath': './train/2021_08_22_06_43_37/3152',
        'intersection_coordinates': [180, 205, 75, 104],
        'eval_intention': 'would like to move north',
        'eval_facing': 'north',
    },
    6: {
        'name': 'Scene 6 (Custom)',
        'set': 'custom_scenario',
        'id': '2025_09_14_16_04_20',
        'folder': './custom_scenario/2025_09_14_16_04_20',
        'type': 'stop',
        'ego_cav': '001',
        'helper_cavs': ['002'],
        'vlm_base_path': './structured_format/2025_09_14_16_04_20',
        'ego_goal_filepath': './custom_scenario/2025_09_14_16_04_20/001',
        'intersection_coordinates': None,
        'eval_intention': 'would like to turn south',
        'eval_facing': 'west',
    },
    7: {
        'name': 'Scene 7 (Custom)',
        'set': 'custom_scenario',
        'id': '2025_09_14_16_23_41',
        'folder': './custom_scenario/2025_09_14_16_23_41',
        'type': 'stop',
        'ego_cav': '002',
        'helper_cavs': ['001'],
        'vlm_base_path': './structured_format/2025_09_14_16_23_41',
        'ego_goal_filepath': './custom_scenario/2025_09_14_16_23_41/002',
        'intersection_coordinates': None,
        'eval_intention': 'would like to move west',
        'eval_facing': 'west',
    },
    8: {
        'name': 'Scene 8 (Custom)',
        'set': 'custom_scenario',
        'id': '2025_10_07_01_09_57',
        'folder': './custom_scenario/2025_10_07_01_09_57',
        'type': 'stop',
        'ego_cav': '001',
        'helper_cavs': ['002'],
        'vlm_base_path': './structured_format/2025_10_07_01_09_57',
        'ego_goal_filepath': './custom_scenario/2025_10_07_01_09_57/001',
        'intersection_coordinates': None,
        'eval_intention': 'would like to move south',
        'eval_facing': 'south',
    },
    9: {
        'name': 'Scene 9 (Custom)',
        'set': 'custom_scenario',
        'id': '2025_10_07_01_13_20',
        'folder': './custom_scenario/2025_10_07_01_13_20',
        'type': 'stop',
        'ego_cav': '001',
        'helper_cavs': ['002'],
        'vlm_base_path': './structured_format/2025_10_07_01_13_20',
        'ego_goal_filepath': './custom_scenario/2025_10_07_01_13_20/001',
        'intersection_coordinates': None,
        'eval_intention': 'would like to turn south',
        'eval_facing': 'east',
    },
}


def get_scene_config(scene_number):
    
    if scene_number not in SCENE_CONFIGS:
        available = ', '.join(map(str, sorted(SCENE_CONFIGS.keys())))
        raise ValueError(f"Scene {scene_number} not found. Available scenes: {available}")
    
    return SCENE_CONFIGS[scene_number]


def list_available_scenes():
    print("Available Scenes:")
    print("-" * 60)
    for num in sorted(SCENE_CONFIGS.keys()):
        config = SCENE_CONFIGS[num]
        print(f"Scene {num}: {config['name']}")
        print(f"  Type: {config['type']}")
        print(f"  Ego CAV: {config['ego_cav']}")
        print(f"  Helper CAVs: {config['helper_cavs']}")
        print(f"  Intention: {config.get('intention', 'N/A')}")
        print(f"  Folder: {config['folder']}")
        print()