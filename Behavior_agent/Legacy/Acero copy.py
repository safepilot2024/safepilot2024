import sys
sys.path.append('/home/reasult/CARLA_0.9.13/PythonAPI/carla/dist/carla-0.9.13-py3.7-linux-x86_64.egg')
import carla
from carla import Location, Rotation, Transform
import random
import time
from math import inf,sqrt
import config
import copy
from execute  import*
from config import*
import logging
import threading

sys.path.append('/home/reasult/CARLA_0.9.13/PythonAPI/carla')
from agents.navigation.behavior_agent import BehaviorAgent  # pylint: disable=import-error
from agents.navigation.basic_agent import BasicAgent  # pylint: disable=import-error

ATTACK_SUCCESS = False

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

#生成车辆控制的候选命令 参数：计数器，指导元组
def candidate_command_generation(counter, guide):

    # Random range sets for two cars
    #方向盘的三个范围
    directions = [(0.1, 0.4), (-0.1, 0.1), (-0.4, -0.1)]
    #油门刹车的三个范围
    # thros = [(-1/2, 1/2), (1/2, 1), (-1, -1/2)] #这里我交换了顺序 我觉得这里原来有问题
    thros = [(1/2, 1), (1/2, 1), (1/2, 1)] #这里我交换了顺序 我觉得这里原来有问题
    # Candidates vehicle commands
    #候选车辆控制命令
    candidate_vehicle_commands = []

    #是否是第一次生成命令
    if counter == 0:
        #从三个方向盘范围中各自随机选个值，从三个油门/刹车范围中各自随机选个值 然后3x3组合 9种选择放到候选命令里 
        #（因为循环的嵌套顺序 方向只有三种取值 油门/刹车九种取值）
        for dir in directions:
            steer = random.uniform(dir[0], dir[1])
            throttle = random.uniform(0,1)
            candidate_vehicle_commands.append((throttle, steer)) 
    else:
        #从guide中取出方向和油门/刹车的指示
        dir_indicator = guide[0]
        thro_indicator = guide[1]
        dir_range = range(0, 0)
        thro_range = range(0, 0)
        #如果方向指示大于0 方向就从0,1中选；否则（小于等于0）方向就从1,2中选
        if dir_indicator > 0:
            dir_range = range(0, 2)
        else:
            dir_range = range(1, 3)

        #如果油门指示大于0 油门就从1，2中选；否则（小于等于0）油门就从0，1中选
        if thro_indicator > 0:
            thro_range = range(1, 3)
        else:
            thro_range = range(0, 2)

        #2x2组合 4种候选指令存储到列表中
        for i in dir_range:
            steer = random.uniform(directions[i][0], directions[i][1])
            for j in thro_range:
                throttle = random.uniform(thros[j][0], thros[j][1])
                candidate_vehicle_commands.append((throttle, steer))
    #返回候选指令列表
    return candidate_vehicle_commands

#参数：计数器，指导元组，历史命令，世界，攻击车，受害车，npc，地图，观察者，代理，天气，受害车位置，攻击车位置，攻击车原始模型，受害车原始模型，npc原始模型，npc位置
def command_generation(counter, guide,history_commands,world,attacker, victim,npc,map,spectator,agent,weather,victim_pos,attacker_pos,original_attack_vehicle_model,original_victim_vehicle_model,npc_vheicle_model,npc_vehicle_pos):
    #generate candidate command
    #生成候选命令 
    candidate_attacker_commands = candidate_command_generation(counter, guide)
    #鲁棒性评分列表
    command_robustness = []
    attacker_state = []#没用上???
    #回溯细节信息列表
    rewind_details=[]
    global ATTACK_SUCCESS#这个原来没有 我加的
    global REWIND
    
    #从候选指令中选出鲁棒评分最低的（选择最好的指令）
    #对于候选列表中的每一条指令
    for command in candidate_attacker_commands:
        
        #打印当前正在评估的命令，使用特定的颜色代码来高亮显示。
        print("\033[93m{Command:", command, "}\033[0m\n")
        #把攻击车，受害车，npc，代理的状态回溯到特定的状态
        attacker, victim,agent,npc=rewind_scene(world,weather,attacker,victim,npc,agent,history_commands,spectator,victim_pos,attacker_pos,original_attack_vehicle_model,original_victim_vehicle_model,npc_vheicle_model,npc_vehicle_pos)
        #执行当前的命令，返回一个标志，指示是否需要回溯
        rewind_flag=exec_command(attacker,agent,victim,spectator,command,world,npc)
        print("\033[94m>>>Weather attacker break law:\033[0m",rewind_flag)

        #如果不需要回溯（攻击者的行为是合法的）
        if not rewind_flag:
            #计算攻击者和npc的碰撞时间作为鲁棒性评分 加入到列表中
            command_robustness.append(robustness_calculation(victim, npc, map,TTC = True,DIST=False))
        #如果需要回溯
        else:
           #从候选指令列表中移除这个命令
           candidate_attacker_commands.remove(command)
        #如果攻击成功
        if ATTACK_SUCCESS:
            #返回当前命令，相关实体和回溯详情
            return command,attacker,victim,agent,rewind_details,npc
        #如果需要回溯
        #这有两种回溯 一种是小写的局部的 一种是大写的全局的 
        #小写的局部回溯置true是因为执行命令后攻击车违法了 大写的全局回溯置true是因为?
        if REWIND:
            #rewind_details 加一条消息，说明回溯原因是攻击车违法了。
            rewind_details.append("round: " + str(len(history_commands)) + "\n Reason: attacker break the law!")
            #重置 REWIND 。
            REWIND = False
        #不需要回溯
        else:
             #rewind_details 加一条消息，说明回溯的原因是违反了物理约束
             rewind_details.append("round: " + str(len(history_commands)) + "\n Reason: violate physical constraints")

    #没有任何命令的稳健性评分
    if len(command_robustness)==0:
        print("Didn't find legal command!\n")
        #返回第一个候选命令、相关实体、回溯详情
        return  candidate_attacker_commands[0],attacker, victim,agent,rewind_details,npc
    #返回鲁棒性评分最低的命令、相关实体、回溯详情
    return candidate_attacker_commands[command_robustness.index(min(command_robustness))],attacker, victim,agent,rewind_details,npc

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
    guide = (1, -1)#改了一下 试试效果
    # guide = (-1, 1)#改了一下 试试效果

    #读取这两个全局向量的值
    global ATTACK_SUCCESS,COLLISION_OBJECT

    # victim_collision_sensor=check_collision_victim(victim,world)

    #只要攻击没成功且轮数小于5
    while not ATTACK_SUCCESS and  counter<5:
    # while not ATTACK_SUCCESS and  counter<2:
        #输出轮数
        print("\033[92m>>>>This is counter {}\033[0m".format(counter))
        #生成鲁棒性评分最低的指令
        command,attacker,victim,agent,rewind_details,npc=command_generation(counter, guide,attack_commands,world,attacker, victim,npc,map,spectator,agent,weather,victim_pos,attacker_pos,original_attack_vehicle_model,original_victim_vehicle_model,npc_vheicle_model,npc_vehicle_pos)
        #回溯细节加入到列表中
        rewinding_details.append(rewind_details) 
        
        #输出鲁棒性评分最低的命令
        print(">>>Exec commands with lowest robustness:",command)
        #hyp added
        exec_command(attacker,agent,victim,spectator,command,world,npc)#这条原来被注释掉了？
        #攻击车的新坐标添加到 trajectory 中
        trajectory.append(get_state(attacker))
        #攻击命令添加到attack_commands中
        attack_commands.append(command)

        #如果不是第一轮
        if counter > 0:
            #guide基于攻击者两轮之间位置变化更新
            guide=[trajectory[counter][0]-trajectory[counter-1][0],trajectory[counter][1]-trajectory[counter-1][1]]

            #我加的 观察一下
            print(guide)
        
        
        print("\033[92m>>>>Finish counter {}\033[0m".format(counter))
        #计数器+1
        counter+=1
        time.sleep(1)

    print(trajectory)
    return trajectory,attack_commands,rewinding_details


#计算鲁棒性评分
#参数：攻击车，受害车，地图，ttc，dist（这俩挑一个）
def robustness_calculation(acar, vcar,map, TTC=False, DIST=False):
    #计算碰撞时间 如果无法碰撞就返回无穷大
    if TTC:
        ttc = time_to_collision(acar, vcar)
        if ttc == -1:
            return inf
        return ttc
    #计算距离 这玩意有-1？？？ 不知道为什么会有这个if 怀疑是直接复制的之前的ttc
    if DIST:
        dist = Dist(vcar, map)
        if dist == -1:
            return inf
        return dist
    
#单轮循环中判断攻击车是否碰撞
def check_collision_attacker(attacker, world):
    def on_collision(event):
        global ATTACK_COLLISION_OBJECT
        ATTACK_COLLISION_OBJECT = True
        # print("攻击车撞了！！！！！")

    # 从carla中找到碰撞传感器的蓝图并返回为bp
    bp = world.get_blueprint_library().find('sensor.other.collision')

    # 定义车辆的四个角的位置
    # sensor_offsets = [
    #     carla.Transform(carla.Location(x=2.5, y=0.0, z=1.0)),  # 前端
    #     carla.Transform(carla.Location(x=-2.5, y=0.0, z=1.0)), # 后端
    #     carla.Transform(carla.Location(x=0.0, y=2.5, z=1.0)),  # 左侧
    #     carla.Transform(carla.Location(x=0.0, y=-2.5, z=1.0))  # 右侧
    # ]

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

    # 定义车辆的四个角的位置
    # sensor_offsets = [
    #     carla.Transform(carla.Location(x=2.5, y=0.0, z=1.0)),  # 前端
    #     carla.Transform(carla.Location(x=-2.5, y=0.0, z=1.0)), # 后端
    #     carla.Transform(carla.Location(x=0.0, y=2.5, z=1.0)),  # 左侧
    #     carla.Transform(carla.Location(x=0.0, y=-2.5, z=1.0))  # 右侧
    # ]
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
def agent_run_victim(agent,victim):
    #记录当前时间
    start_time=time.time()
    #打印正在执行受害者车辆的命令
    print("exec current victim")

    #开始一个持续时间为8秒的循环
    #change to 8
    while time.time()-start_time < 8:
        #设置代理的速度限制
        agent.get_local_planner().set_speed(conf.speed_limit)
        #代理用run_step生成控制命令，用apply_control将命令应用在受害车上
        victim.apply_control(agent.run_step())

#执行命令 返回值为true就是执行命令后违规了
#参数：攻击车，代理，受害车，观察者，命令，世界，npc
def exec_command(attacker,agent,victim, spectator,command,world,npc):
    #攻击车是否撞车:False
    global ATTACK_COLLISION_OBJECT
    ATTACK_COLLISION_OBJECT=False
    #从world中获取地图
    map=world.get_map()

    # 创建1个线程
    thread1 = threading.Thread(target=agent_run_victim, args=(agent, victim))
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
    #hyp added
    
    #销毁碰撞传感器
    for sensor in attacker_collision_sensor:
        sensor.destroy()

    for sensor in victim_collision_sensor:
        sensor.destroy()



    # 等待线程结束
    thread1.join()    

    #调用 check_os 函数来检查攻击车是否超速
    overspeed = check_os(attacker)
    #调用 check_wd 函数来检查攻击车是否行驶在错误的方向 wd：WrongDictionary
    wrongdirection = check_wd(attacker, map)    
    #输出是否攻击车超速、方向错误、碰撞
    print("Overspeed: ", overspeed)
    print("Wrong Direction: ", wrongdirection)
    print("Attacker Collision:",ATTACK_COLLISION_OBJECT)
    global ATTACK_SUCCESS, REWIND
    # global REWIND
    #输出是否攻击成功
    print("Attack Success: ", ATTACK_SUCCESS)

    #程序暂停10秒
    #change to 5
    time.sleep(5)
    

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
    #vic_traj = []
    #att_traj = []

    # 创建1个线程
    thread1 = threading.Thread(target=agent_run_victim, args=(agent, victim))
    # 启动线程
    thread1.start()


    #观察者追踪攻击车
    cam_chase_player(attacker, spectator)
    #for i in range(round):
    #    attacker.apply_control(carla_command(history_commands[i]))

    #对于每一条历史指令 攻击车执行 打印 等2秒
    for history_command in history_commands:
        attacker.apply_control(carla_command(history_command))
        #hyp added
        print("exec ",history_command)
        time.sleep(2)

    # 等待线程结束
    thread1.join()
    
    #hyp added
    print("history command exec victim")


        #exec_command(attacker, agent, victim,spectator,history_commands[i],world,npc)
        #if recordtraj:
            #vic_traj.append(get_state(victim))
            #att_traj.append(get_state(attacker))

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
        return True
    return False

#检查载具是否逆行 Wrong direction 返回布尔值
def check_wd(attacker, map):
    """
    Check weather the vehicle is going the wrong direction
    """
    waypoint = map.get_waypoint(attacker.get_location(),project_to_road=True, lane_type=(carla.LaneType.Driving | carla.LaneType.Sidewalk))
    if waypoint.lane_id < 0:
        logging.info("Vehicle is going the wrong direction")
        return True
    
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


#观察者位置跟随指定载具
def cam_chase_player(player, spectator):
    location = player.get_location()
    rotation = player.get_transform().rotation
    fwd_vec = rotation.get_forward_vector()

    # chase from behind
    constant = 4
    location.x -= constant * fwd_vec.x
    location.y -= constant * fwd_vec.y
    # and above
    location.z += 3
    rotation.pitch -= 5
    spectator.set_transform(
        carla.Transform(location, rotation)
    )


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
