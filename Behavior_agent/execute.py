import sys
sys.path.append('/home/test/carla/CARLA_0.9.13/PythonAPI/carla/dist/carla-0.9.13-py3.7-linux-x86_64.egg')
import carla
from carla import Location, Rotation, Transform
import random
import time
import math
import config
from Acero import *
import json


sys.path.append('/home/test/carla/CARLA_0.9.13/PythonAPI/carla')
from agents.navigation.behavior_agent import BehaviorAgent  # pylint: disable=import-error
from agents.navigation.basic_agent import BasicAgent  # pylint: disable=import-error

conf=config.Config()

def load_scene_data(file_path):
    with open(file_path, 'r') as file:
        log_data = json.load(file)
    return log_data

# 场景文件路径
global scene_file_path
scene_file_path = '/home/test/test050/Scene/Scene001.json'

# 从文件中加载场景数据
scene_data = load_scene_data(scene_file_path)


#配置天气的参数 这是一个函数调用 后面的那个world.set_weather(weather)这玩意是一个方法调用 这俩不一样 
def set_weather(world):
    weather = world.get_weather()
    weather.cloudiness = config.weather_dict["cloud"]
    weather.precipitation = config.weather_dict["rain"]
    weather.precipitation_deposits = config.weather_dict["puddle"]
    weather.wetness = config.weather_dict["wetness"]
    weather.wind_intensity = config.weather_dict["wind"]
    weather.fog_density = config.weather_dict["fog"]
    weather.sun_azimuth_angle = config.weather_dict["angle"]
    weather.sun_altitude_angle = config.weather_dict["altitude"]
    world.set_weather(weather)
    return weather

#初始化世界 参数：世界，天气，攻击车模型，攻击车位置，受害车模型，受害车位置，npc模型，npc位置
def scene_init(world,weather,original_attack_vehicle_model,attacker_pos,original_victim_vehicle_model,victim_pos,npc_vheicle_model,npc_vehicle_pos):

    
    world=None    #清空世界
    if world ==None:
        try:
            client = carla.Client('localhost', 2000) #创建一个到carla服务器的客户端对象client，服务器运行于本地主机的2000端口
            client.set_timeout(10.0) # 设置超时时间

            # 获取世界
            town=scene_data["town"]
            client.load_world(town) #加载名为 Town03 的地图
            world = client.get_world()#加载世界
            world.set_weather(weather)#世界设置天气
            
        except:
           print("\033[91mError: Cannot connect to the CARLA server!\033[0m")#失败 报错

    traffic_lights = world.get_actors().filter('traffic.traffic_light')#获得世界中所有的可交互对象，并过滤出交通灯
    for tl in traffic_lights:#对于每一个交通灯t1
        tl.freeze(True)#冻结交通灯（交通灯的颜色不会发生改变）
        tl.set_state(carla.TrafficLightState.Off)#关闭交通灯（灯不会呈现任何颜色）

        
    spectator=world.get_spectator()#获取当前世界的观察者视角（可以自由移动的相机视角）
    map=world.get_map()#获取当前世界的地图对象
    attack_vehicle_model = original_attack_vehicle_model#攻击车模型等于传入参数
    victim_vehicle_model=original_victim_vehicle_model#受害车模型等于传入参数

    victim=world.spawn_actor(victim_vehicle_model, victim_pos)#生成受害车，参数：受害车模型，受害车位置
    attacker=world.spawn_actor(attack_vehicle_model,attacker_pos)#生成攻击车，参数：攻击车模型，攻击车位置
    agent = BehaviorAgent(victim,behavior='normal')#创建一个代理 控制受害车的行为  指定代理的驾驶风格是谨慎
    current_transform  =victim.get_transform()
    current_location = current_transform.location
    current_rotation = current_transform.rotation
    forward_vector = carla.Location(x=math.cos(math.radians(current_rotation.yaw)), y=math.sin(math.radians(current_rotation.yaw)))
    destination_location = carla.Location(x=scene_data["destination_location_x"], y=scene_data["destination_location_y"] , z=current_location.z)
    agent.set_destination(destination_location)
    npc=world.spawn_actor(npc_vheicle_model,npc_vehicle_pos)#生成npc，参数：npc模型，npc位置
    cam_chase_player(victim,spectator)#让观察者的视角跟随受害车辆（使用时不能跟随 不知道是不是这个的问题）

    
    return victim,attacker,agent,npc#返回受害车，攻击车，代理，npc


#随机变换车辆位置 参数：车辆位置
def random_transform_vehicle(agent_current_location):
    offset_x = 0#x,y偏移量
    offset_y = 0

    if random.choice([True, False]):#x偏移随机二选一 这里改了下 原来逻辑有点怪
        offset_x = random.uniform(5,10)
    else:
        offset_x = random.uniform(-5,-10)

    if random.choice([True, False]):#y偏移随机二选一 这里改了下 原来逻辑有点怪
        offset_y = random.uniform(5,10)
    else:
        offset_y = random.uniform(-5,-10)
    
    
    #print(agent_current_location)
    attack_vehicle_pos=agent_current_location
    attack_vehicle_pos.location.x +=offset_x#车变换后的x坐标等于原始位置+x偏移
    attack_vehicle_pos.location.y +=offset_y#车变换后的y坐标等于原始位置+y偏移

    return attack_vehicle_pos#返回变换后车的位置


#初始化攻击车、受害车、npc的位置与角度
def pos_init():
    #spawn_points= world.get_map().get_spawn_points()

    #生成受害车的位置，旋转（俯仰角，偏移角，翻滚）
    spawn_point=Transform(Location(x=scene_data["victim_x"], y=scene_data["victim_y"], z=scene_data["victim_z"]), Rotation(pitch=scene_data["victim_pitch"], yaw=scene_data["victim_yaw"], roll=scene_data["victim_roll"]))

    #agent_current_location = spawn_point
    #attack_vehicle_pos=random_transform_vehicle(agent_current_location)

    #生成攻击车的位置，旋转（俯仰角，偏移角，翻滚）
    attack_vehicle_pos=Transform(Location(x=scene_data["attacker_x"], y=scene_data["attacker_y"], z=scene_data["attacker_z"]), Rotation(pitch=scene_data["attacker_pitch"], yaw=scene_data["attacker_yaw"], roll=scene_data["attacker_roll"]))
    
    ##  npc pos   init

    #生成npc的位置，旋转（俯仰角，偏移角，翻滚）
    npc_vehicle_pos=Transform(Location(x=scene_data["npc_x"], y=scene_data["npc_y"], z=scene_data["npc_z"]), Rotation(pitch=scene_data["npc_pitch"], yaw=scene_data["npc_yaw"], roll=scene_data["npc_roll"]))
    return attack_vehicle_pos,spawn_point,npc_vehicle_pos

#获得一个对象的当前位置(x,y)
def get_state(actor):
    # Get the x and y coordinates of the actor
    actor_location = actor.get_location()
    return [actor_location.x, actor_location.y]


#观察者相机追踪player车辆
def cam_chase_player(player, spectator):
    location = player.get_location()
    rotation = player.get_transform().rotation

    # 放到车正上方
    # 假设我们不需要调整x和y，因为我们希望摄像头直接位于车辆的正上方
    # 只需要调整z轴（高度），以确保摄像头位于车辆上方一定高度
    length_x = scene_data["cam_x"]
    length_y = scene_data["cam_y"]
    length_z = scene_data["cam_z"]  # 摄像头距离车辆的高度，可以根据需要调整

    location.x += length_x
    location.y += length_y
    location.z += length_z    

    # 设置摄像头的旋转使其直接向下看
    # 旋转角度需要设置为向下看，所以将俯仰角（pitch）设置为-90度（直下），偏航角（yaw）和翻滚角（roll）不变
    rotation.yaw = scene_data["cam_yaw"]
    rotation.pitch = scene_data["cam_pitch"]  # 向下看
    # rotation.yaw = 保持不变，根据车辆当前的方向
    # rotation.roll = 保持不变，一般情况下摄像头不需要翻滚

    # 应用变换
    spectator.set_transform(
        carla.Transform(location, rotation)
    )


#随机生成速度，速度的取值范围是config文件的spped±2
def random_speed_vehicle( ):
    speed = random.uniform(conf.speed-2, conf.speed+2)
    return speed


#计算碰撞时间 参数：物体a，物体b
def time_to_collision(object_a, object_b):
    """
    Calculate the TTC of between two objects
    (Need to consider the direction of the object)
    """

    # 1. Decide which one is the front object. Here we assume the front direction is to 'positive_x' direction for simplicity
    #确定哪个对象是在前方的 x大的定为前方对象
    if object_a.get_transform().location.x > object_b.get_transform().location.x:
        front_object = object_a
        back_object = object_b
    else:
        front_object = object_b
        back_object = object_a
    
    # 2. Decide which one is the left object. Here we assume the right direction is to 'positive_y' direction for simplicity
    #确定哪个对象是在左侧的 y小的定为左侧对象
    if object_a.get_transform().location.y < object_b.get_transform().location.y:
        left_object = object_a
        right_object = object_b
    else:
        left_object = object_b
        right_object = object_a
    
    # 3. Decide the potential collision part
    #确定潜在的碰撞区域
    #最左侧点是右面的物体的y减去右面的物体y尺寸的一半 就是右面物体的最左侧点

    #计算右面对象最左侧点、左面对象最右侧点、前面对象最后点、后面对象最前点
    most_left_point = right_object.get_transform().location.y - right_object.bounding_box.extent.y
    most_right_point = left_object.get_transform().location.y + left_object.bounding_box.extent.y

    most_front_point = back_object.get_transform().location.x + back_object.bounding_box.extent.x
    most_back_point = front_object.get_transform().location.x - front_object.bounding_box.extent.x


    different_direction = False
    #如果两个对象的偏航角yaw差值大于0.45 则认为他们是不同向的
    #最后点变成了前方对象x坐标减去前方对象y尺寸的一半
    #最前点变成了后方对象x坐标加上后方对象y尺寸的一半
    if abs(front_object.get_transform().rotation.yaw - back_object.get_transform().rotation.yaw) > 0.45:
        different_direction = True
        most_back_point = front_object.get_transform().location.x - front_object.bounding_box.extent.y
        most_front_point = back_object.get_transform().location.x + back_object.bounding_box.extent.y

    # If collision is not possible, return -1
    # 1. Check if the front object is in the potential collision area
    # 2. Check if the back object has a higher speed
    #如果不同向且前车x轴速度小于x轴后车速度 返回碰撞时间
    if different_direction and front_object.get_velocity().x < back_object.get_velocity().x:
        return (most_back_point-most_front_point)/(back_object.get_velocity().x - front_object.get_velocity().x)
    #这里原来是<我改成>了 这个情况代表 右侧对象的最左端在左侧物体最右端的右面 表示这俩虽然x轴上有相撞的可能 但是这俩在y轴上离得太远了 他俩会错开 因此没有碰撞可能
    #或者 前方速度大于后方速度 这两个之间距离越来越大 不会碰撞
    elif most_left_point > most_right_point or front_object.get_velocity().x >= back_object.get_velocity().x:
        return -1
    else:
        return (most_back_point-most_front_point)/(back_object.get_velocity().x - front_object.get_velocity().x)


#计算对象与最近的车道线之间的距离 参数：对象，地图
def Dist(obj, map):
    """
    Calculate the distance between two objects
    """

    # 1. Get the nearst way point of vehicle
    #得到对象当前位置最近的车道路点
    obj_waypoint = map.get_waypoint(obj.get_location(), project_to_road=True)
    
    # 2. Calculate the distance between the vehicle and the cloest lane mark
    #dist = 车道宽度的一半 - 对象y坐标与路点y坐标的差值绝对值（对象到车道中线的y距离） 
    #大于0代表没有出线，小于0代表出线，等于0代表压线
    dist = obj_waypoint.lane_width/2 - abs(obj.get_location().y - obj_waypoint.transform.location.y)

    return dist

#将输入的command转化成carla能够识别的命令 参数command是一个列表 [0]是油门/刹车，[1]是方向盘转向值
def carla_command(command):
    # Convert the command to carla command
    if command[0] < 0:  # brake
        return carla.VehicleControl(throttle=0, steer= command[1], brake=abs(command[0]))
    else:   # Throttle
        return carla.VehicleControl(throttle=command[0], steer=command[1], brake=0)


