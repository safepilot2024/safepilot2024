import sys
sys.path.append('/home/test/carla/CARLA_0.9.13/PythonAPI/carla/dist/carla-0.9.13-py3.7-linux-x86_64.egg')
import carla
from carla import Location, Rotation, Transform
import random
import time
import math
from config import *
import Acero
from Acero import *
import execute
from execute import *
from attack_logging import *

sys.path.append('/home/test/carla/CARLA_0.9.13/PythonAPI/carla')
from agents.navigation.behavior_agent import BehaviorAgent  # pylint: disable=import-error
from agents.navigation.basic_agent import BasicAgent  # pylint: disable=import-error


# 从文件中加载场景数据
scene_data = execute.load_scene_data(scene_file_path)

def main():

    #连接本地主机的CARLA服务器，端口2000
    client = carla.Client('localhost', 2000)
    client.set_timeout(10.0) # 设置超时时间10s

    
    town=scene_data["town"]
    #加载名为 town 的世界。
    client.load_world(town)
    #获取当前加载的世界。
    world = client.get_world()
    #获取观察者
    spectator=world.get_spectator()
    #获取地图
    map=world.get_map()
    #设置世界的天气
    weather=set_weather(world)

    #从世界获取蓝图库
    blueprint_library = world.get_blueprint_library()
    #vehicle_bp：蓝图库里筛选出来的第一个特斯拉model3
    vehicle_bp = blueprint_library.filter("vehicle.tesla.model3")[0]      ## only for agent
    #player_bp:蓝图库里选出来的所有的车
    player_bp=blueprint_library.filter('vehicle.*')
    #蓝图库的所有车里四个轮子及以上的、不是特斯拉model3的，都存在filtered_vehicles_bp列表里
    filtered_vehicles_bp = []

    #把蓝图库的所有车里四个轮子及以上的、不是特斯拉model3的，都存在filtered_vehicles_bp列表里
    for bp in player_bp:
    # 检查轮子数量是否大于或等于4
        if int(bp.get_attribute('number_of_wheels')) >= 4:
            # 确保不是Tesla Model 3
            if not bp.id.endswith('tesla.model3'):
                    filtered_vehicles_bp.append(bp)


    #过滤后的车里随便选一个作为攻击车的模型
    attack_vehicle_model = random.choice(filtered_vehicles_bp)
    #特斯拉Cybertruck的第一个当npc的车型
    npc_vheicle_model=blueprint_library.filter("vehicle.tesla.cybertruck")[0]
    #获取世界中的所有的交通灯
    traffic_lights = world.get_actors().filter('traffic.traffic_light')

    #把世界中所有的交通灯冻结且关闭
    for tl in traffic_lights:
        tl.freeze(True)
        tl.set_state(carla.TrafficLightState.Off)

    #随机生成攻击车和受害车的速度
    attacker_speed=random_speed_vehicle()
    victim_speed=random.uniform(5,7)
    

    #随机生成攻击车，受害车，npc的位置
    attacker_pos,victim_pos,npc_vehicle_pos=pos_init()

    #生成攻击车 受害车 代理 npc
    victim,attacker,agent,npc=scene_init(world,weather,attack_vehicle_model,attacker_pos,vehicle_bp,victim_pos,npc_vheicle_model,npc_vehicle_pos)

    starttime = time.time()

    # attacker_collision_sensor = collision_attacker(attacker, world)
    # victim_collision_sensor = collision_victim(victim, world)


    #生成攻击车轨迹（生成 挑选 执行五轮命令）
    # attacker_trajectory,attack_commands,rewinding_details = trajectory_generation(world,attacker,victim,npc,spectator,agent,weather,victim_pos,attacker_pos,attack_vehicle_model,vehicle_bp,npc_vheicle_model,npc_vehicle_pos)

    endtime = time.time()

    #记录日志

    # attack_car_detail = vehicle_details(attack_vehicle_model.id, attacker_pos, attacker_speed, attacker_trajectory)
    # victim_car_detail = vehicle_details(vehicle_bp.id, victim_pos, victim_speed, trajectory=None)
    # stopped_car_detail = vehicle_details(npc_vheicle_model.id, npc_vehicle_pos, 0, trajectory=None)
    # agent_list = [stopped_car_detail]
    # setup = mission_setup(weather, agent_list, None)
    # duration = mission_duration(None, endtime-starttime)

    # attlogger("C001", Acero.ATTACK_SUCCESS, setup, duration, victim_car_detail, attack_car_detail, attack_commands, rewinding_details=rewinding_details)


    # for sensor in attacker_collision_sensor:
    #     sensor.destroy()

    # for sensor in victim_collision_sensor:
    #         sensor.destroy()
    
    #销毁代理 受害车 攻击车 npc
    # agent=None
    # victim.destroy()
    # attacker.destroy()
    # npc.destroy()
    




    # set destination
    '''
    destination = random.choice(world.get_map().get_spawn_points()).location
    destination_location = carla.Location(x=destination.x, y=destination.y, z=destination.z)
    agent.set_destination(destination_location)
    '''

    """
    current_transform  =vehicle.get_transform()
    current_location = current_transform.location
    current_rotation =while True:tion(destination_location)


    cam_chase_player(vehicle, spectator)
    #agent.update_information(vehicle)
    while True:
        control = agent.run_step()
        vehicle.apply_control(control)

        # 做一些基本的检查以确保目标是否已达到或者需要其他的终止条件
        if vehicle.get_location().distance(destination_location) < 1: # 如果车辆到目的地的距离小于5米,则认为到达目的地
            print("目的地已达到")
            break

        time.sleep(0.1) # 控制循环速率

    # 清理：删除车辆实体
    vehicle.destroy()
    """




if __name__ == '__main__':
    
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)