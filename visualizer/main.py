import viser
import trimesh
import numpy as np
import os
import time
import json
import imageio.v3 as iio  # for fast image loading

# === Config ===
ply_dir = "//Users/gemmechu/Documents/meta/code/output/all_color"
rgb_dir = "/Users/gemmechu/Documents/meta/data/cube/rgb/"
camera_json_path = "/Users/gemmechu/Documents/meta/data/cube/cameras.json"
fps = 10

def convert_pose(C2W):
    flip_yz = np.eye(4)
    flip_yz[1, 1] = -1
    flip_yz[2, 2] = -1
    C2W = np.matmul(C2W, flip_yz)
    return C2W

# === Load camera data ===
with open(camera_json_path) as f:
    camera_data = json.load(f)["frames"]

# === Load pointcloud frame list ===
ply_files = sorted([f for f in os.listdir(ply_dir) if f.endswith(".ply")])

# === Start Viser Server ===
server = viser.ViserServer(port=8081)
scene = server.scene


# === GUI: Frame Slider ===
frame_slider = server.gui.add_slider(
    label="Frame Index",
    min=0,
    max=len(ply_files) - 1,
    step=1,
    initial_value=0,
)

# === GUI: RGB Image Panel ===
image_panel = server.gui.add_image(
    label="RGB Frame",
    image=np.zeros((480, 640, 3), dtype=np.uint8)
)

# === Add Point Cloud to Scene ===
cloud = scene.add_point_cloud(
    name="cloud",
    points=np.zeros((1, 3)),
    colors=np.zeros((1, 3)),
    point_size=0.005
)

# === Add Camera Frustum ===
frustum = scene.add_camera_frustum(
    name="camera",
    fov=39.6,
    aspect=1.0,
    scale=0.2,
    wxyz=np.array([1.0, 0.0, 0.0, 0.0]),  # identity rotation
    position=np.array([0.0, 0.0, 0.0]),
    color=np.array([0.0, 1.0, 0.0])
)
# === Load Point Cloud + RGB Frame + Camera Pose ===

def update_frame(index: int):
    frame_id = f"{index+1:04d}"  # e.g., 0001, 0002 ...

    # Load .ply
    ply_path = os.path.join(ply_dir, ply_files[index])
    mesh = trimesh.load(ply_path)
    points = mesh.vertices
    if len(mesh.colors) >0:
        colors = mesh.colors[:, :3] / 255.0 
    else:
        colors = np.ones_like(points) * 0.5
    cloud.points = points
    cloud.colors = colors

    # Load RGB image
    img_path = os.path.join(rgb_dir, f"rgb_{index:04d}.png")
    if os.path.exists(img_path):
        img = iio.imread(img_path)
        image_panel.image = img
    # Update camera frustum pose
    if frame_id in camera_data:

        c2w = np.array(camera_data[frame_id]["c2w"])
        c2w = convert_pose(c2w)
        position = c2w[:3, 3]
        frustum.position = position
        quat = trimesh.transformations.quaternion_from_matrix(c2w)  # (w, x, y, z)
        quat = np.array(quat, dtype=np.float32).reshape(4,)         # ensure proper shape
        frustum.wxyz = quat
        
        

# === Callback: Slider Change ===
@frame_slider.on_update
def on_slider(event: viser.GuiEvent):
    update_frame(int(event.target.value))

# === GUI: Play/Pause Toggle Button ===
is_playing = [False]
play_button = server.gui.add_button(label="▶ Play")

@play_button.on_click
def toggle_play(event: viser.GuiEvent):
    is_playing[0] = not is_playing[0]
    play_button.label = "⏸ Pause" if is_playing[0] else "▶ Play"

# === Playback Loop ===
while True:
    if is_playing[0]:
        current = int(frame_slider.value)
        next_index = (current + 1) % len(ply_files)
        frame_slider.value = next_index
    time.sleep(1.0 / fps)
