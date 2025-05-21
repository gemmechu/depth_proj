import bpy
import os
import json
import numpy as np

# ---------- CONFIG ----------
output_root = "/Users/gemmechu/Documents/meta/data/table/"
rgb_dir = os.path.join(output_root, "rgb")
depth_dir = os.path.join(output_root, "depth")
os.makedirs(rgb_dir, exist_ok=True)
os.makedirs(depth_dir, exist_ok=True)

scene = bpy.context.scene
camera = scene.camera

# ---------- FUNCTIONS ----------
def get_camera_params(cam):
    render = scene.render
    res_x = render.resolution_x
    res_y = render.resolution_y
    aspect_ratio = render.pixel_aspect_x / render.pixel_aspect_y
    sensor_width = cam.data.sensor_width

    if cam.data.sensor_fit == 'VERTICAL':
        sensor_height = cam.data.sensor_height
    else:
        sensor_height = sensor_width * res_y / (res_x * aspect_ratio)

    focal_len = cam.data.lens
    fx = focal_len / sensor_width * res_x
    fy = focal_len / sensor_height * res_y
    cx = res_x / 2.0
    cy = res_y / 2.0

    K = np.array([
        [fx, 0, cx],
        [0, fy, cy],
        [0,  0,  1]
    ])

    c2w = np.array(cam.matrix_world)

    return K, c2w, res_x, res_y

def setup_compositor(depth_output_path):
    scene.use_nodes = True
    tree = scene.node_tree
    tree.nodes.clear()

    rlayers = tree.nodes.new(type='CompositorNodeRLayers')
    file_output = tree.nodes.new(type='CompositorNodeOutputFile')
    file_output.label = 'Depth Output'
    file_output.base_path = depth_output_path
    file_output.file_slots[0].path = ""
    file_output.format.file_format = 'OPEN_EXR'
    tree.links.new(rlayers.outputs['Depth'], file_output.inputs[0])

# ---------- RENDER LOOP ----------
view_layer = bpy.context.view_layer
bpy.context.view_layer.use_pass_z = True
setup_compositor(depth_dir)
cam_info = {}
cam_info["frames"] = {}
for frame in range(scene.frame_start, scene.frame_end + 1):
    scene.frame_set(frame)
    frame_str = f"{frame:04d}"
    dpt_str = f"{frame:04d}"
    
    # Save camera parameters
    K, c2w, W, H = get_camera_params(camera)
    if "intrinsics" not in cam_info:
        cam_info["intrinsics"] = K.tolist()
    cam_info["frames"][frame_str] = {
    "rgb": f"{frame_str}.png",
    "depth": f"{dpt_str}.exr",
                "c2w": c2w.tolist(),
                "width": W,
                "height": H
            }
       # Save RGB image
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = os.path.join(rgb_dir, f"{frame_str}.png")
    bpy.ops.render.render(write_still=True)

    # Save depth (EXR)
#    scene.node_tree.nodes["File Output"].file_slots[0].path = f"depth_{frame_str}"
#    bpy.ops.render.render(write_still=True)
with open(os.path.join(output_root, f"metadata.json"), "w") as f:
    json.dump(cam_info, f, indent=4)

print("Done rendering animation!")
