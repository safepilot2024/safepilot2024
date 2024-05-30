import sys
sys.path.append('/home/test/carla/CARLA_0.9.13/PythonAPI/carla/dist/carla-0.9.13-py3.7-linux-x86_64.egg')
import carla
from carla import Location, Rotation, Transform
import random
import time
import math
import config
import copy
from execute  import*
from config import*
import logging
import threading
import datetime

sys.path.append('/home/test/carla/CARLA_0.9.13/PythonAPI/carla')
from agents.navigation.behavior_agent import BehaviorAgent  # pylint: disable=import-error
from agents.navigation.basic_agent import BasicAgent  # pylint: disable=import-error


global filename

log_directory = "/home/test/文档/carlalog"
current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"{log_directory}/{current_time}.log"

ATTACK_SUCCESS = False

# 从文件中加载场景数据
scene_data = load_scene_data(scene_file_path)

#配置carla的基本设置，world：世界实例，conf：配置文件
def init_settings(world,conf):
    #获取当前世界的设置
    settings = world.get_settings()
    #开启同步模式
    settings.synchronous_mode = True
    #设置每帧的时间（时间步长），1/帧率
    settings.fixed_delta_seconds = 1.0 / conf.FRAME_RATE  # FPS
    #把不渲染图像给关了，就是渲染图像
    settings.no_rendering_mode = False
    #世界应用新的设置
    world.apply_settings(settings)

REMAKE=False

#指令生成：
#参数：第几轮
#返回：一条可以执行的不违反规则的命令
#参数：计数器，指导元组，历史命令，世界，攻击车，受害车，npc，地图，观察者，代理，天气，受害车位置，攻击车位置，攻击车原始模型，受害车原始模型，npc原始模型，npc位置
def command_generation(counter, guide,history_commands,world,attacker, victim,npc,spectator,agent,weather,victim_pos,attacker_pos,original_attack_vehicle_model,original_victim_vehicle_model,npc_vheicle_model,npc_vehicle_pos,vic_traj,att_traj):
    global REMAKE
    REMAKE = True

    command=[0,0]
    try_count=0
    while REMAKE == True and try_count<4:
        #未检验的随机指令生成
        if(counter==0):
            command[0]=random.uniform(4/5,1)
            command[1]=random.uniform(-0.4,0.4)
        elif(counter==1):
            command[0]=random.uniform(2/3,1)
            command[1]=random.uniform(-0.4,0.4)
        else:
            if(guide[0]<0):#x轴的间距变小了 攻击车应该加速
                command[0]=random.uniform(2/4,3/4)
            else:
                command[0]=random.uniform(0,1/4)
            
            if(guide[1]>0):#y轴的间距变小了 攻击车应该左转
                command[1]=random.uniform(-0.3,0.1)
            else:
                command[1]=random.uniform(-0.1,0.3)                


        #打印当前正在评估的命令，使用特定的颜色代码来高亮显示。
        print("\033[93m{Command:", command, "}\033[0m\n")
        #把攻击车，受害车，npc，代理的状态回溯到特定的状态
        attacker, victim,agent,npc=rewind_scene(world,weather,attacker,victim,npc,agent,history_commands,spectator,victim_pos,attacker_pos,original_attack_vehicle_model,original_victim_vehicle_model,npc_vheicle_model,npc_vehicle_pos)
        #攻击车执行指令
        REMAKE = exec_command(attacker,agent,victim, spectator,command,world,npc,vic_traj,att_traj)
        time.sleep(1)

        global ATTACK_SUCCESS
        if ATTACK_SUCCESS == True and ATTACK_COLLISION_OBJECT == False:
            REMAKE = False
            try_count = 0
            return command,attacker,victim,agent,npc,try_count
        else:
            ATTACK_SUCCESS = False

        try_count+=1

    #返回鲁棒性评分最低的命令、相关实体、回溯详情
    return command,attacker,victim,agent,npc,try_count

#进行五轮命令生成 每次生成一轮 执行一轮 执行后记录鲁棒性评分最低的 然后进行下一轮
#返回值是执行五轮命令后的轨迹（应该是五个坐标吧？）
#参数：世界，攻击车，受害车，npc,观测者，代理，天气，受害车位置，攻击车位置，攻击车原始模型，受害车原始模型，npc原始模型，npc位置
def trajectory_generation(world,attacker,victim,npc,spectator,agent,weather,victim_pos,attacker_pos,original_attack_vehicle_model,original_victim_vehicle_model,npc_vheicle_model,npc_vehicle_pos):
    #获得攻击车的x，y坐标 作为列表的第一个元素
    trajectory=[get_state(attacker)]
    #获得受害车与攻击车的x，y坐标 作为列表的第一个元素
    vic_traj, att_traj = [get_state(victim)], [get_state(attacker)]
    #攻击者的命令
    attack_commands = []
    #回溯的详细信息
    rewinding_details = []
    #计数器
    counter = 0
    #指导元组初始化
    guide = [1, -1]#改了一下 试试效果

    #读取这两个全局向量的值
    global ATTACK_SUCCESS,COLLISION_OBJECT

    #只要攻击没成功且轮数小于5
    while not ATTACK_SUCCESS and  counter<5:
    # while not ATTACK_SUCCESS and  counter<2:
        #输出轮数
        print("\033[92m>>>>This is counter {}\033[0m".format(counter))
        #生成鲁棒性评分最低的指令
        command,attacker,victim,agent,npc,try_count=command_generation(counter, guide,attack_commands,world,attacker, victim,npc,spectator,agent,weather,victim_pos,attacker_pos,original_attack_vehicle_model,original_victim_vehicle_model,npc_vheicle_model,npc_vehicle_pos,vic_traj,att_traj)
        if try_count==4:
            attack_commands.pop()
            trajectory.pop()
            vic_traj.pop()
            att_traj.pop()
            counter-=1
            #RP(vv, av, t) = pos(av, t) − pos(vv, t)
            RPtbefore   =  [att_traj[counter-1][0]-vic_traj[counter-1][0],att_traj[counter-1][1]-vic_traj[counter-1][1]]
            RPtafter    =  [att_traj[counter][0]-vic_traj[counter][0],att_traj[counter][1]-vic_traj[counter][1]]
            #AGV(t) = RP(vv, av, t) − RP(vv, av, t − 1)
            guide[0] = RPtafter[0]-RPtbefore[0]
            guide[1] = RPtafter[1]-RPtbefore[1]

            print("\033[92m>>>>Command has been deleted {}\033[0m".format(counter))
            # time.sleep(1)
            continue

        #输出鲁棒性评分最低的命令
        print(">>>Exec commands:",command)
        #hyp added
        # exec_command(attacker,agent,victim,spectator,command,world,npc)#这条原来被注释掉了？
        #攻击车的新坐标添加到 trajectory 中
        trajectory.append(get_state(attacker))
        #记录受害车与攻击车的新坐标
        # vic_traj.append(get_state(victim))
        # att_traj.append(get_state(attacker))
        # print("\033[92m>>>>vic_traj {}\033[0m".format(vic_traj))
        # print("\033[92m>>>>att_traj {}\033[0m".format(att_traj))

        print("\033[92m>>>>Finish counter {}\033[0m".format(counter))
        counter+=1
        #RP(vv, av, t) = pos(av, t) − pos(vv, t)
        RPtbefore   =  [att_traj[counter-1][0]-vic_traj[counter-1][0],att_traj[counter-1][1]-vic_traj[counter-1][1]]
        RPtafter    =  [att_traj[counter][0]-vic_traj[counter][0],att_traj[counter][1]-vic_traj[counter][1]]
        #AGV(t) = RP(vv, av, t) − RP(vv, av, t − 1)
        guide[0] = RPtafter[0]-RPtbefore[0]
        guide[1] = RPtafter[1]-RPtbefore[1]
        #攻击命令添加到attack_commands中
        attack_commands.append(command)
        # guide=[trajectory[counter][0]-trajectory[counter-1][0],trajectory[counter][1]-trajectory[counter-1][1]]
        # time.sleep(1)

    print(trajectory)
    return trajectory,attack_commands,rewinding_details




#计算鲁棒性评分
#参数：攻击车，受害车，地图，ttc，dist（这俩挑一个）
def robustness_calculation(acar, vcar,map, TTC=False, DIST=False):
    #计算碰撞时间 如果无法碰撞就返回无穷大
    if TTC:
        ttc = time_to_collision(acar, vcar)
        if ttc == -1:
            return float('inf')
        
        return ttc
    #计算距离 这玩意有-1？？？ 不知道为什么会有这个if 怀疑是直接复制的之前的ttc
    if DIST:
        dist = Dist(vcar, map)
        if dist == -1:
            return float('inf')
        return dist
    
#单轮循环中判断攻击车是否碰撞
def check_collision_attacker(attacker, world):
    def on_collision(event):
        global ATTACK_COLLISION_OBJECT
        ATTACK_COLLISION_OBJECT = True
        global REMAKE
        REMAKE = True
        # print("攻击车撞了！！！！！")

    # 从carla中找到碰撞传感器的蓝图并返回为bp
    bp = world.get_blueprint_library().find('sensor.other.collision')

    sensor_offsets = [
        carla.Transform(carla.Location(x=0.0, y=0.0, z=1.0)),  # 前端
    ]

    # 为每个位置创建一个碰撞传感器并附加到攻击车辆
    collision_sensors = []
    for offset in sensor_offsets:
        sensor = world.spawn_actor(bp, offset, attach_to=attacker)
        sensor.listen(on_collision)
        collision_sensors.append(sensor)

    # 返回所有创建的碰撞传感器
    return collision_sensors

#单轮循环中判断攻击车是否碰撞
def check_collision_victim(victim, attacker, world):
    # 添加一个标志变量来跟踪是否已经输出过碰撞提示信息
    collision_handled = False

    def on_collision(event):
        nonlocal collision_handled  # 使用nonlocal关键字来修改外部函数中的变量
        if collision_handled:  # 如果已经处理过碰撞，直接返回
            return

        if event.other_actor.id == attacker.id:
            print("-------Collision with attacker-------")
        else:
            global ATTACK_SUCCESS
            ATTACK_SUCCESS = True
            # print("ATTACK_SUCCESS :",ATTACK_SUCCESS)
            print("-------Victim collision--------")
            global COLLISION_OBJECT
            COLLISION_OBJECT = event.other_actor.id
            # print("COLLISION_OBJECT :",COLLISION_OBJECT)
           

        collision_handled = True  # 设置标志变量，表示已经处理过碰撞

    # 从carla中找到碰撞传感器的蓝图并返回为bp
    bp = world.get_blueprint_library().find('sensor.other.collision')
    
    sensor_offsets = [
        carla.Transform(carla.Location(x=0.0, y=0.0, z=1.0)),  #
    ]
    
    # 为每个位置创建一个碰撞传感器并附加到受害车辆
    collision_sensors = []
    for offset in sensor_offsets:
        sensor = world.spawn_actor(bp, offset, attach_to=victim)
        sensor.listen(on_collision)
        collision_sensors.append(sensor)

    # 返回所有创建的碰撞传感器
    return collision_sensors


#受害车由代理持续运行
def agent_run_victim(agent,victim,last_time):
    #记录当前时间
    start_time=time.time()
    #打印正在执行受害者车辆的命令
    print("exec current victim")

    #开始一个持续时间为8秒的循环
    #change to 8
    while time.time()-start_time < last_time+1:
        #设置代理的速度限制
        agent.get_local_planner().set_speed(conf.speed_limit)
        #代理用run_step生成控制命令，用apply_control将命令应用在受害车上
        victim.apply_control(agent.run_step())

#执行命令 返回值为true就是执行命令后违规了
#参数：攻击车，代理，受害车，观察者，命令，世界，npc
def exec_command(attacker,agent,victim, spectator,command,world,npc,vic_traj = [],att_traj = []):
    #攻击车是否撞车:False
    global ATTACK_COLLISION_OBJECT
    ATTACK_COLLISION_OBJECT=False
    #从world中获取地图
    map=world.get_map()

    #npc run
    # npc.apply_control(carla_command([0.8,0]))
    time.sleep(0.5)
    npc.apply_control(carla_command([scene_data["npc_throttle"],scene_data["npc_direction"]]))

    # 创建1个线程
    thread1 = threading.Thread(target=agent_run_victim, args=(agent, victim,8))
    # 启动线程
    thread1.start()


    #输出执行命令前的鲁棒性评分
    print("Before Exec", robustness_calculation(victim, npc,map, TTC=True, DIST=False))

    #观察者跟随攻击车
    cam_chase_player(attacker, spectator)
    
    #检查攻击者车辆是否发生碰撞，并将结果存储在 collision_sensor 中
    attacker_collision_sensor=check_collision_attacker(attacker,world)
    #这是一个碰撞传感器 只要撞了就ATTACK_COLLISION_OBJECT=True
    victim_collision_sensor=check_collision_victim(victim,attacker,world)

    #hyp added
    #打印正在执行攻击者车辆的命令
    print("exec current attacker")

    #攻击者车辆执行命令
    attacker.apply_control(carla_command(command))
    time.sleep(0.8)
    vic_traj.append(get_state(victim))
    att_traj.append(get_state(attacker))
    attacker.apply_control(carla_command([-1,0]))    
    #hyp added


    #销毁碰撞传感器
    for sensor in attacker_collision_sensor:
        sensor.destroy()


    #调用 check_os 函数来检查攻击车是否超速
    overspeed = check_os(attacker)
    #调用 check_wd 函数来检查攻击车是否行驶在错误的方向 wd：WrongDictionary
    wrongdirection = check_wd(attacker, map)

    thread1.join()

    #输出是否攻击车超速、方向错误、碰撞
    print("Overspeed: ", overspeed)
    print("Wrong Direction: ", wrongdirection)
    print("Attacker Collision:",ATTACK_COLLISION_OBJECT)
    global ATTACK_SUCCESS, REWIND
    # global REWIND
    #输出是否攻击成功
    print("Attack Success: ", ATTACK_SUCCESS)

    for sensor in victim_collision_sensor:
        sensor.destroy()

    #如果任何一个检查（超速、错误方向、需要回溯、攻击者碰撞）为真，则返回 True
    return overspeed or wrongdirection or REWIND or ATTACK_COLLISION_OBJECT


#回溯场景 参数：世界，天气，攻击车，受害车，npc，历史命令，受害车位置，攻击车位置，攻击车原始模型，受害车原始模型，npc车辆模型，npc位置    
def rewind_scene(world,weather,attacker,victim,npc,agent,history_commands,spectator,victim_pos,attacker_pos,original_attack_vehicle_model,original_victim_vehicle_model,npc_vheicle_model,npc_vehicle_pos):
    global REWIND

    #打印 回溯
    print("rewind")#hyp added 

    #销毁代理、受害车、攻击车、npc
    agent=None
    victim.destroy()
    attacker.destroy()
    npc.destroy()
   
    #等4秒
    time.sleep(4)
    #将REWIND 设置为 False，表明回溯操作已完成
    REWIND=False
    ##生成新的受害车、攻击车、代理、npc
    victim,attacker,agent,npc=scene_init(world,weather,original_attack_vehicle_model,attacker_pos,original_victim_vehicle_model,victim_pos,npc_vheicle_model,npc_vehicle_pos)
    client = carla.Client('localhost', 2000)
    client.start_recorder(filename)
    
    #如果历史命令不为空 就执行所有历史命令 这一步保证场景回溯到执行命令前的状态
    if history_commands:
        exec_history_command(history_commands,attacker,victim,agent, spectator,world,npc)

    
    #返回攻击车、受害车、代理、npc
    return attacker, victim,agent,npc


#执行所有历史命令
#参数：历史命令列表，攻击车，受害车，代理，观察者，世界，npc
def exec_history_command(history_commands,attacker,victim,agent, spectator,world,npc):
    #轮数，有多少历史命令执行多少轮 这玩意其实没用上
    round = len(history_commands)
    print(">>>>>>>History_commands:",history_commands)

    #npc run
    # npc.apply_control(carla_command([0.8,0]))
    time.sleep(0.5)
    npc.apply_control(carla_command([scene_data["npc_throttle"],scene_data["npc_direction"]]))

    # 创建1个线程
    thread1 = threading.Thread(target=agent_run_victim, args=(agent, victim,round))
    # 启动线程
    thread1.start()

    #观察者追踪攻击车
    cam_chase_player(attacker, spectator)
    #for i in range(round):
    #    attacker.apply_control(carla_command(history_commands[i]))

    #对于每一条历史指令 攻击车执行 打印 等1秒
    for history_command in history_commands:
        attacker.apply_control(carla_command(history_command))
        #hyp added
        print("exec ",history_command)
        time.sleep(1)

    # 等待线程结束
    thread1.join()
    
    #hyp added
    # print("history command exec victim")

#判断载具是否超速（35） over speed 返回布尔值
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
    """
    Check whether the vehicle is going the wrong direction.
    """
    # 获取车辆的位置
    vehicle_location = attacker.get_location()
    # 获取车辆当前位置的路点
    waypoint = map.get_waypoint(vehicle_location, project_to_road=True,
                                lane_type=(carla.LaneType.Driving | carla.LaneType.Sidewalk))
    # 获取车辆的变换（位置和旋转）
    vehicle_transform = attacker.get_transform()
    # 获取车辆的前向向量
    vehicle_forward_vector = vehicle_transform.get_forward_vector()
    # 获取路点的前向向量
    waypoint_forward_vector = waypoint.transform.get_forward_vector()

    # 计算车辆方向和路点方向之间的点积
    dot_product = vehicle_forward_vector.x * waypoint_forward_vector.x + \
                  vehicle_forward_vector.y * waypoint_forward_vector.y

    # 如果点积为负，车辆方向与路点方向相反，即车辆逆行
    if dot_product < 0:
        logging.info("Vehicle is going the wrong direction")
        global REMAKE
        REMAKE = True
        return True

    # 如果点积为正，车辆方向与路点方向一致，即车辆没有逆行
    return False

#计算碰撞时间 这个在execute文件标过了 不知道有没有区别  最后决定返回值的if的小于号改了
def time_to_collision(object_a, object_b):
    """
    Calculate the TTC of between two objects
    (Need to consider the direction of the object)
    """

    # 1. Decide which one is the front object. Here we assume the front direction is to 'positive_x' direction for simplicity
    if object_a.get_transform().location.x > object_b.get_transform().location.x:
        front_object = object_a
        back_object = object_b
    else:
        front_object = object_b
        back_object = object_a
    
    # 2. Decide which one is the left object. Here we assume the right direction is to 'positive_y' direction for simplicity
    if object_a.get_transform().location.y < object_b.get_transform().location.y:
        left_object = object_a
        right_object = object_b
    else:
        left_object = object_b
        right_object = object_a
    
    # 3. Decide the potential collision part
    most_left_point = right_object.get_transform().location.y - right_object.bounding_box.extent.y
    most_right_point = left_object.get_transform().location.y + left_object.bounding_box.extent.y

    most_front_point = back_object.get_transform().location.x + back_object.bounding_box.extent.x
    most_back_point = front_object.get_transform().location.x - front_object.bounding_box.extent.x


    different_direction = False
    if abs(front_object.get_transform().rotation.yaw - back_object.get_transform().rotation.yaw) > 0.45:
        different_direction = True
        most_back_point = front_object.get_transform().location.x - front_object.bounding_box.extent.y
        most_front_point = back_object.get_transform().location.x + back_object.bounding_box.extent.y

    # If collision is not possible, return -1
    # 1. Check if the front object is in the potential collision area
    # 2. Check if the back object has a higher speed
    if different_direction and front_object.get_velocity().x < back_object.get_velocity().x:
        return (most_back_point-most_front_point)/(back_object.get_velocity().x - front_object.get_velocity().x)
    # elif most_left_point < most_right_point or front_object.get_velocity().x >= back_object.get_velocity().x:
    elif most_left_point > most_right_point or front_object.get_velocity().x >= back_object.get_velocity().x:    
        return -1
    else:
        return (most_back_point-most_front_point)/(back_object.get_velocity().x - front_object.get_velocity().x)


#计算距离 标过了
def Dist(obj, map):
    """
    Calculate the distance between two objects
    """

    # 1. Get the nearst way point of vehicle
    obj_waypoint = map.get_waypoint(obj.get_location(), project_to_road=True)
    
    # 2. Calculate the distance between the vehicle and the cloest lane mark
    dist = obj_waypoint.lane_width/2 - abs(obj.get_location().y - obj_waypoint.transform.location.y)

    return dist




#把载具命令转化成carla能接受的形式
def carla_command(command):
    # Convert the command to carla command
    if command[0] < 0:  # brake
        return carla.VehicleControl(throttle=0, steer= command[1], brake=abs(command[0]))
    else:   # Throttle
        return carla.VehicleControl(throttle=command[0], steer=command[1], brake=0)
    

#获得载具的位置（x,y）
def get_state(actor):
    # Get the x and y coordinates of the actor
    actor_location = actor.get_location()
    return [actor_location.x, actor_location.y]
