import sys
sys.path.append('/home/reasult/CARLA_0.9.13/PythonAPI/carla/dist/carla-0.9.13-py3.7-linux-x86_64.egg')
import carla
from carla import Location, Rotation, Transform
import random
import time
import math
from config import *
import Acero
from Acero import *
from execute import *
from attack_logging import *
sys.path.append('/home/reasult/CARLA_0.9.13/PythonAPI/carla')
from agents.navigation.behavior_agent import BehaviorAgent  # pylint: disable=import-error
from agents.navigation.basic_agent import BasicAgent  # pylint: disable=import-error
import json
import re

actors_destroyed = False

def load_log_data(file_path):
    with open(file_path, 'r') as file:
        log_data = json.load(file)
    return log_data

def destroy_actors(victim_vehicle, attacker_vehicle, npc_vehicle):
    global actors_destroyed
    victim_vehicle.destroy()
    attacker_vehicle.destroy()
    npc_vehicle.destroy()
    actors_destroyed = True

# 在尝试操作actors之前，检查标志变量
def apply_control_to_actor(actor, control):
    global actors_destroyed
    if not actors_destroyed:
        actor.apply_control(control)


def parse_transform(transform_str):
    # 使用正则表达式提取位置和旋转的数值
    location_pattern = r"Location\(x=(.*?), y=(.*?), z=(.*?)\)"
    rotation_pattern = r"Rotation\(pitch=(.*?), yaw=(.*?), roll=(.*?)\)"
    
    location_match = re.search(location_pattern, transform_str)
    rotation_match = re.search(rotation_pattern, transform_str)
    
    # 如果匹配成功，则创建并返回Transform对象
    if location_match and rotation_match:
        location = carla.Location(
            x=float(location_match.group(1)),
            y=float(location_match.group(2)),
            z=float(location_match.group(3))
        )
        rotation = carla.Rotation(
            pitch=float(rotation_match.group(1)),
            yaw=float(rotation_match.group(2)),
            roll=float(rotation_match.group(3))
        )
        return carla.Transform(location, rotation)
    
    # 如果匹配失败，则返回None
    return None

def recreate_scenario_from_log(client, log_data):
    # 连接到CARLA服务器
    client = carla.Client('localhost', 2000)
    client.set_timeout(10.0)

    # 加载世界
    world = client.load_world('Town03')

    # 设置天气
    weather_params = carla.WeatherParameters(
        cloudiness=log_data['mission_setup']['weather']['cloudiness'],
        precipitation=log_data['mission_setup']['weather']['precipitation'],
        precipitation_deposits=log_data['mission_setup']['weather']['precipitation_deposits'],
        sun_altitude_angle=log_data['mission_setup']['weather']['sun_altitude_angle']
    )
    world.set_weather(weather_params)

    # 获取蓝图库
    blueprint_library = world.get_blueprint_library()

    # 创建一个列表来跟踪所有actors
    actors = []

    try:
        # 设置受害车辆
        victim_bp = blueprint_library.find(log_data['victim_car_details']['model'])
        victim_transform = parse_transform(log_data['victim_car_details']['starting_position'])
        if victim_transform is None:
            raise ValueError("Unable to parse victim transform data")
        victim_vehicle = world.spawn_actor(victim_bp, victim_transform)
        actors.append(victim_vehicle)
        victim_vehicle.set_autopilot(True)

        # 设置攻击车辆
        attacker_bp = blueprint_library.find(log_data['attacker_car_details']['model'])
        attacker_transform = parse_transform(log_data['attacker_car_details']['starting_position'])
        if attacker_transform is None:
            raise ValueError("Unable to parse attacker transform data")
        attacker_vehicle = world.spawn_actor(attacker_bp, attacker_transform)
        actors.append(attacker_vehicle)

        # 设置NPC车辆
        npc_bp = blueprint_library.find(log_data['mission_setup']['traffic']['model'][0])
        npc_transform = parse_transform(log_data['mission_setup']['traffic']['traffic_vehicle_starting_positions'][0])
        if npc_transform is None:
            raise ValueError("Unable to parse NPC transform data")
        npc_vehicle = world.spawn_actor(npc_bp, npc_transform)
        actors.append(npc_vehicle)
        npc_vehicle.set_autopilot(True)

        # 应用攻击车辆的命令
        for command in log_data['attack_commands']:
            throttle, steer = command
            attacker_vehicle.apply_control(carla.VehicleControl(throttle=throttle, steer=steer))
            # 这里可以添加一个时间延迟，以模拟命令的持续时间

    finally:
        # 清理：销毁所有actors
        destroy_actors(victim_vehicle, attacker_vehicle, npc_vehicle)

# 日志文件路径
log_file_path = '/home/reasult/Documents/CarlaData001/C001/log/success/07-19-29.json'

# 从文件中加载日志数据
log_data = load_log_data(log_file_path)

# 创建CARLA客户端
client = carla.Client('localhost', 2000)
client.set_timeout(10.0)

# 重现日志记录的场景
recreate_scenario_from_log(client, log_data)