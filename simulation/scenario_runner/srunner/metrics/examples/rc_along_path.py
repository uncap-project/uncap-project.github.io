import os, json, math, random, yaml
import numpy as np
from srunner.metrics.examples.basic_metric import BasicMetric

scenario_name = "2021_08_20_21_10_24"
SCENARIO_ROOT = "/home/po-han/Downloads/OPV2V/test/" + scenario_name

DIST_TOL_M = 2.0
ANG_TOL_DEG = 25.0
END_TOL_M = 1.5

import matplotlib.pyplot as plt

def debug_plot(plan_xy, ego_xy_list, projections, tick_idx, cav_id, vehicle_positions=None,
               outdir="/home/po-han/Downloads/OPV2V/debug_metrics/"):
    os.makedirs(outdir, exist_ok=True)

    plt.figure(figsize=(6,6))
    plt.axis("equal")

    # plan trajectory
    plt.plot(plan_xy[:,0], plan_xy[:,1], "-o", color="blue", label="Plan Trajectory")

    # ego true positions
    if ego_xy_list:
        ex, ey = zip(*ego_xy_list)
        plt.scatter(ex, ey, c="red", label="Ego positions", s=20)

    # projections
    if projections:
        px, py = zip(*projections)
        plt.scatter(px, py, c="green", label="Projections", s=30, marker="x")

    # other vehicles
    if vehicle_positions:
        vx, vy = zip(*vehicle_positions)
        plt.scatter(vx, vy, c="purple", label="Other vehicles", s=15, alpha=0.6)

    plt.legend()
    plt.title(f"Tick {tick_idx} (CAV {cav_id})")
    plt.xlim(-250,-150)
    plt.ylim(200,300)
    plt.savefig(os.path.join(outdir, f"tick_{cav_id}_{tick_idx:05d}.png"))
    plt.close()


def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}

def calc_length(points):
    segs = np.linalg.norm(points[1:] - points[:-1], axis=1)
    return np.concatenate([[0.0], np.cumsum(segs)])

def project_arclen(pt, poly, s):
    best_s, best_d2 = 0.0, float("inf")
    for i in range(len(poly) - 1):
        a, b = poly[i], poly[i + 1]
        ab = b - a
        ab2 = float(np.dot(ab, ab))
        t = 0.0 if ab2 < 1e-9 else np.clip(np.dot(pt - a, ab) / ab2, 0.0, 1.0)
        proj = a + t * ab
        d2 = float(np.dot(pt - proj, pt - proj))
        if d2 < best_d2:
            best_d2 = d2
            best_s = s[i] + t * (s[i + 1] - s[i])
    return best_s

def extract_plan_xy(data):
    if "plan_trajectory" not in data:
        return None
    pts = data["plan_trajectory"]
    if not isinstance(pts, (list, tuple)) or len(pts) < 2:
        return None
    try:
        return np.asarray([[p[0], p[1]] for p in pts], dtype=float)
    except Exception:
        return None

id_map = {
    "2021_08_20_21_10_24": {
        "1996": 120,
        "2005": 128,
        "2014": 136
    }
}

def extract_xy_yaw(data, log, cav_id, N_yaml, tick_idx):
    if scenario_name not in id_map:
        return None, None
    if cav_id not in id_map[scenario_name]:
        return None, None
    ego_id = log.get_ego_vehicle_id()
    ego_id = id_map[scenario_name][cav_id]
    s_ego, e_ego = log.get_actor_alive_frames(ego_id)
    ego_start = min(s_ego, e_ego)
    ego_end = max(s_ego, e_ego)
    N_log = ego_end - ego_start
    log_i = round((tick_idx + 1) * (N_log / N_yaml))
    transform = log.get_actor_transform(ego_id, log_i)
    loc = transform.location
    yaw = transform.rotation.yaw
    return np.array([loc.x, loc.y], dtype=float), yaw

def angle_from_vec(v):
    return math.degrees(math.atan2(float(v[1]), float(v[0])))

def smallest_angle_diff_deg(a, b):
    d = (a - b + 180.0) % 360.0 - 180.0
    return abs(d)

def route_tangent_deg(route_xy, idx):
    if idx == 0:
        d = route_xy[1] - route_xy[0]
    else:
        d = route_xy[idx] - route_xy[idx - 1]
    if np.allclose(d, 0.0):
        return None
    return angle_from_vec(d)

def fulfill_one_plan(plan_xy, future_ticks_data, log, cav_id, N_yaml, tick_idx):
    M = len(plan_xy)
    if M < 2:
        return None
    s_plan = calc_length(plan_xy)
    total_len = float(s_plan[-1])
    next_wp = 0
    max_s = 0.0
    for data in future_ticks_data:
        ego_xy, ego_yaw = extract_xy_yaw(data, log, cav_id, N_yaml, tick_idx)
        if ego_xy is None:
            continue
        cur_s = project_arclen(ego_xy, plan_xy, s_plan)
        if cur_s > max_s:
            max_s = cur_s
        if total_len > 0.0 and max_s >= total_len - END_TOL_M:
            return 100.0
        while next_wp < M:
            wp_xy = plan_xy[next_wp]
            if float(np.linalg.norm(ego_xy - wp_xy)) > DIST_TOL_M:
                break
            tan_deg = route_tangent_deg(plan_xy, next_wp)
            if tan_deg is not None and ego_yaw is not None:
                if smallest_angle_diff_deg(ego_yaw, tan_deg) > ANG_TOL_DEG:
                    break
            next_wp += 1

    ego_positions = []
    proj_positions = []

    for data in future_ticks_data:
        ego_xy, ego_yaw = extract_xy_yaw(data, log, cav_id, N_yaml, tick_idx)
        if ego_xy is None:
            continue
        ego_positions.append(ego_xy)

        cur_s = project_arclen(ego_xy, plan_xy, s_plan)
        # reconstruct the projection point itself
        for i in range(len(plan_xy)-1):
            a, b = plan_xy[i], plan_xy[i+1]
            ab = b - a
            ab2 = float(np.dot(ab, ab))
            t = 0.0 if ab2 < 1e-9 else np.clip(np.dot(ego_xy - a, ab) / ab2, 0.0, 1.0)
            proj = a + t * ab
            proj_positions.append(proj)
            break  # just first segment projection for visualization
    vehicle_positions = []
    if "vehicles" in future_ticks_data[0]:
        for vid, vinfo in future_ticks_data[0]["vehicles"].items():
            if "location" in vinfo and len(vinfo["location"]) >= 2:
                x, y = float(vinfo["location"][0]), float(vinfo["location"][1])
                vehicle_positions.append((x,y))

    # call once per tick
    debug_plot(plan_xy, ego_positions, proj_positions, tick_idx,cav_id,vehicle_positions)

    return 100.0 * (next_wp / M)

def per_tick_plan_fulfillment_for_cav(cav_dir, log, cav_id):
    tick_dir = os.path.join(cav_dir, "yaml") if os.path.isdir(os.path.join(cav_dir, "yaml")) else cav_dir
    tick_files = sorted([f for f in os.listdir(tick_dir) if f.endswith(".yaml")])
    if not tick_files:
        return None
    data_list = [load_yaml(os.path.join(tick_dir, f)) for f in tick_files]
    per_tick = []
    N_yaml = len(tick_files)
    for i in range(len(tick_files)):
        plan_xy = extract_plan_xy(data_list[i])
        if plan_xy is None:
            continue
        pct = fulfill_one_plan(plan_xy, data_list[i:], log, cav_id, N_yaml, i)
        if pct is not None:
            per_tick.append(pct)
    return float(np.mean(per_tick)) if per_tick else None

class TrafficLightViolationCount(BasicMetric):
    def _create_metric(self, town_map, log, criteria):
        self._recorder = f"tmp_{random.randint(0, 999999):06d}.log"
        cav_ids = [d for d in os.listdir(SCENARIO_ROOT) if d.isdigit()]
        results = {}
        for cav in sorted(cav_ids, key=lambda x: int(x)):
            cav_dir = os.path.join(SCENARIO_ROOT, cav)
            if not os.path.isdir(cav_dir):
                continue
            mean_pct = per_tick_plan_fulfillment_for_cav(cav_dir, log, cav)
            if mean_pct is not None:
                results[cav] = mean_pct
            print(cav, mean_pct)

    

    
    # #This is for yaml info
    # if "true_ego_pos" in data and isinstance(data["true_ego_pos"], (list, tuple)) and len(data["true_ego_pos"]) >= 5:
    #     x, y = float(data["true_ego_pos"][0]), float(data["true_ego_pos"][1])
    #     yaw_deg = float(data["true_ego_pos"][4])
        
    #     return np.array([x, y], dtype=float), yaw_deg
    # return None, None
    