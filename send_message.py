import subprocess
import carla
import math
import numpy as np
import os


def carla_to_ros2(transform):
    ros2_transform = {}

    ros2_transform["x"] = transform.location.x
    ros2_transform["y"] = -transform.location.y
    ros2_transform["z"] = transform.location.z

    roll = np.radians(transform.rotation.roll)
    pitch = -np.radians(transform.rotation.pitch)
    yaw = -np.radians(transform.rotation.yaw)
    qx = np.sin(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) - np.cos(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
    qy = np.cos(roll/2) * np.sin(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.cos(pitch/2) * np.sin(yaw/2)
    qz = np.cos(roll/2) * np.cos(pitch/2) * np.sin(yaw/2) - np.sin(roll/2) * np.sin(pitch/2) * np.cos(yaw/2)
    qw = np.cos(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
    ros2_transform["qx"] = qx
    ros2_transform["qy"] = qy
    ros2_transform["qz"] = qz
    ros2_transform["qw"] = qw

    return ros2_transform

def get_destination_transform(ego_car):
    # #A demo for autoware
    # #Set a destination of going straight for 100 meters
    # current_transform  =ego_car.get_transform()
    # print("current_transform:",current_transform) 
    # current_location = current_transform.location
    # current_rotation = current_transform.rotation
    # forward_vector = carla.Location(x=math.cos(math.radians(current_rotation.yaw)), 
    #                                 y=math.sin(math.radians(current_rotation.yaw)))
    # current_transform.location.x+=forward_vector.x*50
    # carla_transform_destination=current_transform
    # print("carla destination:", carla_transform_destination)
    carla_transform_destination=carla.Transform(carla.Location(x=-64.71, y=-3.53, z=0.2), carla.Rotation(pitch=0.0, yaw=180, roll=0.0))
    return carla_transform_destination

def send_destination_2_autoware(carla_transform_destination):
    # ros2_transform_destination=carla_to_ros2(carla_transform_destination)
    ros2_transform_destination=carla_transform_destination
    print("ros2 destination:", ros2_transform_destination)
    set_goal_pose_cmd = "{{header: {{frame_id: 'map'}}, pose: {{position: {{x: {}, y: {}, z: {}}}, orientation: {{x: {}, y: {}, z: {}, w: {}}}}}}}".format(\
    ros2_transform_destination["x"], ros2_transform_destination["y"], ros2_transform_destination["z"], \
    ros2_transform_destination["qx"], ros2_transform_destination["qy"], ros2_transform_destination["qz"], ros2_transform_destination["qw"])
    subprocess.run(["ros2", "topic", "pub", "--once", "/planning/mission_planning/goal", "geometry_msgs/msg/PoseStamped", set_goal_pose_cmd])
    #subprocess.run(["/bin/bash", "ros2_change_to_autonomous.sh"])
    source_command = "source " + os.environ["HOME"] + "/carla-autoware-universe/autoware/install/setup.bash"
    change_operation_mode_cmd = "ros2 service call /api/operation_mode/change_to_autonomous autoware_adapi_v1_msgs/srv/ChangeOperationMode {}"
    subprocess.run(source_command + " && " + change_operation_mode_cmd, shell=True, executable="/bin/bash", stdout=subprocess.PIPE)
