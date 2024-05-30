import random
import carla
import math
import subprocess
import time
import logging
import os 
import psutil
import rclpy
from rclpy.node import Node
from reset_init_pose import SetInitialPoseNode

ATTACK_SUCCESS = False
COLLISION_OBJECT = None
ATTACK_COLLISION_OBJECT = None
REWIND=False

#SetInitialPoseNode=SetInitialPoseNode()


def start_carla():
    print("Initing Carla...")
    command='cd ~/carla/CARLA_0.9.13 && ./CarlaUE4.sh -preferNvidia -rpc-carla-port=2000'
    subprocess.Popen(['gnome-terminal','--', 'bash','-c', command])
    time.sleep(5)
    
def start_Autoware():

    print("Initing Autoware")
    command = "cd ~/carla-autoware-universe/autoware && source install/setup.bash && cd ~/carla-autoware-universe/op_carla/op_bridge/op_scripts && ./run_exploration_mode_ros2.sh"
    subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', command])
    time.sleep(35)

def find_all_process_id():
    process_names=[]
    for proc in psutil.process_iter(['pid']):
        process_names.append(proc.info['pid'])
    return process_names

def shutdown_carla():
    os.system("pkill -f CarlaUE4")

def shutdown_Autoware():
    os.system("pkill -SIGKILL -f ros")
      


#天气
weather_dict = {"cloud":random.randint(0, 100),
                    "rain":random.randint(0, 100),
                    "puddle":random.randint(0, 100),
                    "wetness":random.randint(0, 100),
                    "wind":random.randint(0, 100),
                    "fog":random.randint(0, 20),
                    "angle":random.randint(0, 100),
                    "altitude":random.randint(0, 100)}

def set_weather(world):
    weather = world.get_weather()
    weather.cloudiness = weather_dict["cloud"]
    weather.precipitation = weather_dict["rain"]
    weather.precipitation_deposits = weather_dict["puddle"]
    weather.wetness = weather_dict["wetness"]
    weather.wind_intensity = weather_dict["wind"]
    weather.fog_density = weather_dict["fog"]
    weather.sun_azimuth_angle = weather_dict["angle"]
    weather.sun_altitude_angle = weather_dict["altitude"]
    world.set_weather(weather)
    return weather

def load_world():
    world=(carla.Client("127.0.0.1",2000)).get_world()
    map=world.get_map()
    return world

def get_map(world):
    carlamap = world.get_map()
    return carlamap

def find_all_actor(world):
    actors=[]
    while not actors:
        actors=world.get_actors()
    return actors

def get_Autoware(world,actors):
    prius_actors = [actor.id for actor in actors if actor.type_id == "vehicle.toyota.prius"]
    for num_id in prius_actors:
        autoware=world.get_actor(num_id)
    return autoware

def Init_Autoware_postion():
    pos=carla.Transform(carla.Location(x=-6.7, y=-50.4, z=1), carla.Rotation(pitch=0.0, yaw=90, roll=0.0))
    return pos

def get_pos(vehicle):
    current_transform  =vehicle.get_transform()
    print(current_transform)
    current_location = current_transform.location
    current_rotation = current_transform.rotation

    return current_location,current_rotation

def destroy_npc(vehicle):

    vehicle.destroy()


def load_npc(world,current_location):
    blueprint_library = world.get_blueprint_library()
    vehicle_bp = blueprint_library.filter("vehicle.tesla.model3")[0] 
    npc_vheicle_model=blueprint_library.filter("vehicle.tesla.cybertruck")[0]
    attacker_spawn_point=carla.Transform(carla.Location(x=-12.0, y=-15.6, z=1.0), carla.Rotation(pitch=0.0, yaw=135, roll=0.0))
    # npc_spawn_point=carla.Transform(carla.Location(x=27.4, y=4.1, z=1.0), carla.Rotation(pitch=0, yaw=0, roll=0.0))
    npc_spawn_point=carla.Transform(carla.Location(x=300, y=300, z=100.0), carla.Rotation(pitch=0, yaw=0, roll=0.0))
    attacker=world.spawn_actor(vehicle_bp,attacker_spawn_point)
    npc=world.spawn_actor(npc_vheicle_model,npc_spawn_point)
    return attacker,npc

def set_destination(vehicle):
    location,rotation=get_pos(vehicle)
    forward_vector = carla.Location(x=math.cos(math.radians(rotation.yaw))
                                    , y=math.sin(math.radians(rotation.yaw)))
    destination_location=carla.Location(x=82.1, y=134.6, z=1.0)
    return destination_location

def get_state(actor):
    # Get the x and y coordinates of the actor
    actor_location = actor.get_location()
    return [actor_location.x, actor_location.y]

def carla_command(command):
    # Convert the command to carla command
    if command[0] < 0:  # brake
        return carla.VehicleControl(throttle=0, steer= command[1], brake=abs(command[0]))
    else:   # Throttle
        return carla.VehicleControl(throttle=command[0], steer=command[1], brake=0)
    
def check_os(vehicle):
    """
    Check weather the vehicle is over speed
    """
    # calculate the magnitude of the speed
    speed = vehicle.get_velocity()
    speed_magnitude = math.sqrt(speed.x**2 + speed.y**2 + speed.z**2)
    if speed_magnitude > 35:
        logging.info("Vehicle is over speed %.4s", speed_magnitude)
        global REMAKE
        REMAKE = True
        return True
    return False

#检查载具是否逆行 Wrong direction 返回布尔值
def check_wd(attacker, map):
    # 获取车辆当前位置和朝向
    vehicle_transform = attacker.get_transform()
    vehicle_location = vehicle_transform.location
    vehicle_forward_vector = vehicle_transform.get_forward_vector()
    # 获取当前位置的路点
    waypoint = map.get_waypoint(vehicle_location, project_to_road=True, lane_type=(carla.LaneType.Driving | carla.LaneType.Sidewalk))
    # 获取路点的朝向
    waypoint_forward_vector = waypoint.transform.get_forward_vector()
    # 计算车辆朝向和路点朝向的点积
    dot_product = vehicle_forward_vector.x * waypoint_forward_vector.x + vehicle_forward_vector.y * waypoint_forward_vector.y + vehicle_forward_vector.z * waypoint_forward_vector.z
    # 如果点积小于0，说明车辆方向与路点方向相反，即逆行
    if dot_product < 0:
        logging.info("Vehicle is going the wrong direction")
        global REMAKE
        REMAKE = True        
        return True
    return False

def check_autoware_speed(vehicle):
    speed = vehicle.get_velocity()
    speed_magnitude = math.sqrt(speed.x**2 + speed.y**2 + speed.z**2)
    return speed_magnitude


def reset_autoware_position(autoware_hero,transform):
    rclpy.init()
    set_initial_pose_node = SetInitialPoseNode(transform)
    print(f"reset car to {transform}")
    rclpy.spin_once(set_initial_pose_node)
    # rclpy.spin(set_initial_pose_node)
    set_initial_pose_node.destroy_node()
    rclpy.shutdown()
    autoware_hero.set_transform(transform)

def generate_walker(world, transform):
    # 获取所有行人的蓝图
    blueprint_library = world.get_blueprint_library()
    pedestrian_bp = blueprint_library.find('walker.pedestrian.0001')

    # 生成行人
    pedestrian = world.spawn_actor(pedestrian_bp, transform)

    # 返回生成的行人对象，以便于后续操作
    return pedestrian

def control_walker(walker,speed,x,y,z):
    walker_control = carla.WalkerControl()
    walker_control.speed = speed  # 设置行人速度为1.4米/秒
    walker_control.direction = carla.Vector3D(x, y, z)  # 设置行人前进方向
    walker.apply_control(walker_control)
