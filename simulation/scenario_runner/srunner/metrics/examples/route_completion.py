import os, math, yaml
import numpy as np
import matplotlib.pyplot as plt
from srunner.metrics.examples.basic_metric import BasicMetric

DIST_TOL_M = 2.0
ANG_TOL_DEG = 10.0
# CONST_SPEED=30.0
# CONST_TICK=50
# CONST_YAW=0
# CONST_TICKS=50

DEBUG_OUT = "/home/po-han/Downloads/OPV2V/debug_metrics/"

scenario_name = "2021_08_20_21_10_24"
SCENARIO_ROOT = "/home/po-han/Downloads/OPV2V/test/" + scenario_name

id_map = {
    "2021_08_20_21_10_24": {
        "1996": 120,
        "2005": 128,
        "2014": 136
    }
}

def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}

def extract_plan_xy(data):
    if "plan_trajectory" not in data: return None
    pts = data["plan_trajectory"]
    if not isinstance(pts, (list, tuple)) or len(pts) < 1: return None
    return np.asarray([[p[0], p[1]] for p in pts], dtype=float)

def angle_from_vec(v):
    return math.degrees(math.atan2(float(v[1]), float(v[0])))

def smallest_angle_diff_deg(a, b):
    d = (a - b + 180.0) % 360.0 - 180.0
    return abs(d)

def compute_poly_yaws(points):
    n = len(points)
    yaws = np.empty(n, dtype=float)
    last_yaw = None
    for i in range(n):
        if n == 1:
            yaws[i] = last_yaw if last_yaw is not None else 0.0
            last_yaw = yaws[i]
            continue
        if i == 0:
            d = points[1] - points[0]
        elif i == n - 1:
            d = points[i] - points[i - 1]
        else:
            d = points[i + 1] - points[i - 1]
        if np.allclose(d, 0.0):
            yaws[i] = last_yaw if last_yaw is not None else 0.0
        else:
            yaws[i] = angle_from_vec(d)
        last_yaw = yaws[i]
    return yaws

# def custom_direction(last_xy,waypoints,yaw_wp,hit):
#     yaw_rad=math.radians(CONST_YAW)
#     dx = math.cos(yaw_rad)*CONST_SPEED*0.1
#     dy = math.sin(yaw_rad)*CONST_SPEED*0.1
#     step_vec = np.array([dx,dy])
#     dist_thresh = DIST_TOL_M

#     for _ in range(CONST_TICKS):
#         last_xy=last_xy+step_vec
#         ego_xy=np.array(last_xy,dtype=float)
#         cand = np.flatnonzero(~hit)
#         if cand.size==0:
#             break
#         d2 = np.sum((waypoints[cand]-ego_xy[None,:])**2,axis=1)
#         near_idx = np.where(d2<=dist_thresh**2)[0]
#         for j in near_idx:
#             idx = cand[j]
#             wp_yaw = yaw_wp[idx]
#             if smallest_angle_diff_deg(CONST_YAW,wp_yaw)<=ANG_TOL_DEG:
#                 hit[idx]=True
#     return hit


def collect_all_plan_points_with_yaw(cav_dir):
    tick_dir = os.path.join(cav_dir, "yaml") if os.path.isdir(os.path.join(cav_dir, "yaml")) else cav_dir
    tick_files = sorted([f for f in os.listdir(tick_dir) if f.endswith(".yaml")])
    if not tick_files: return None, None
    data_list = [load_yaml(os.path.join(tick_dir, f)) for f in tick_files]

    pts_all = []
    yaws_all = []
    last_yaw_global = None

    for d in data_list:
        poly = extract_plan_xy(d)
        if poly is None or len(poly) == 0: continue
        yaws = compute_poly_yaws(poly)
        # carry-forward across polylines where needed
        for i in range(len(yaws)):
            if yaws[i] is None or not np.isfinite(yaws[i]):
                yaws[i] = last_yaw_global if last_yaw_global is not None else 0.0
            last_yaw_global = yaws[i]
        pts_all.append(poly)
        yaws_all.append(yaws)

    if not pts_all: return None, None
    P = np.vstack(pts_all)
    Y = np.concatenate(yaws_all)
    return P, Y  # no merging/dedup — check every waypoint

def global_plan_fulfillment_for_cav(cav_dir, log, cav_id):
    actor_id = id_map.get(scenario_name, {}).get(cav_id, None)
    if actor_id is None: return None

    waypoints, yaw_wp = collect_all_plan_points_with_yaw(cav_dir)
    if waypoints is None or len(waypoints) == 0: return None

    hit = np.zeros(len(waypoints), dtype=bool)

    s_frame, e_frame = log.get_actor_alive_frames(actor_id)
    if s_frame is None or e_frame is None or e_frame < s_frame: return None

    dist2_thresh = DIST_TOL_M ** 2

    for f in range(s_frame, e_frame + 1):
        t = log.get_actor_transform(actor_id, f)
        ex, ey = t.location.x, t.location.y
        ego_xy = np.array([ex, ey], dtype=float)
        ego_yaw = float(t.rotation.yaw)

        # if f==CONST_TICK:
        #     print(f"[INFO] Triggering custom extrapolation at tick {f}")
        #     hit = custom_direction(ego_xy,waypoints,yaw_wp,hit)
        #     break

        cand = np.flatnonzero(~hit)
        if cand.size == 0:
            break

        d2 = np.sum((waypoints[cand] - ego_xy[None, :])**2, axis=1)
        near_idx = np.where(d2 <= dist2_thresh)[0]
        if near_idx.size == 0:
            continue

        for j in near_idx:
            idx = cand[j]
            wp_yaw = yaw_wp[idx]
            if smallest_angle_diff_deg(ego_yaw, wp_yaw) <= ANG_TOL_DEG:
                hit[idx] = True

    score = 100.0 * (np.count_nonzero(hit) / len(waypoints))

    if DEBUG_OUT:
        os.makedirs(DEBUG_OUT, exist_ok=True)
        xs, ys = waypoints[:,0], waypoints[:,1]
        plt.figure(figsize=(6,6)); plt.axis("equal")
        plt.plot(xs, ys, "-", color="blue", label="All plan points")
        if np.any(hit): plt.scatter(xs[hit], ys[hit], s=20, c="green", label="Fulfilled")
        if np.any(~hit): plt.scatter(xs[~hit], ys[~hit], s=20, c="red", label="Unfulfilled")
        trail_x, trail_y = [], []
        for f in range(s_frame, e_frame + 1):
            t = log.get_actor_transform(actor_id, f)
            trail_x.append(t.location.x); trail_y.append(t.location.y)
        if trail_x: plt.plot(trail_x, trail_y, ".", label="Ego trail", alpha=0.6)
        plt.legend(); plt.title(f"CAV {cav_id} global plan fulfillment: {score:.1f}%")
        plt.savefig(os.path.join(DEBUG_OUT, f"global_{cav_id}.png")); plt.close()

    return score



class RouteCompletion(BasicMetric):
    def _create_metric(self, town_map, log, criteria):
        cav_ids = [d for d in os.listdir(SCENARIO_ROOT) if d.isdigit()]
        results = {}
        for cav in sorted(cav_ids, key=lambda x: int(x)):
            cav_dir = os.path.join(SCENARIO_ROOT, cav)
            if not os.path.isdir(cav_dir): continue
            score = global_plan_fulfillment_for_cav(cav_dir, log, cav)
            if score is not None:
                results[cav] = score
            print(cav, score)
