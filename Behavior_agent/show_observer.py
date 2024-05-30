
import carla
from carla import Location, Rotation, Transform
import random
import time
import math





# 连接到Carla服务器，默认端口是2000
client = carla.Client('172.17.0.1', 2000)
client.set_timeout(2.0)

# 获取世界
world = client.get_world()

# 获取观察者的位置
# 假设观察者是一个相机或玩家控制的角色
# 你可能需要根据你的设置调整这里的代码
observer = world.get_spectator()
transform = observer.get_transform()
location = transform.location

# 打印坐标
print("Observer Location (x, y, z): ({}, {}, {})".format(location.x, location.y, location.z))


#npc:Observer Location (x, y, z): (8.78046703338623, -20.63582420349121, 0.6667398810386658)
#victim:Observer Location (x, y, z): (15.369643211364746, 17.452754974365234, 1.6791503429412842)
#attacker:Observer Location (x, y, z): (19.76729965209961, 1.8037668466567993, 0.8603221774101257)
#destination:Observer Location (x, y, z): (-24.083608627319336, -3.0226635932922363, 0.9171912670135498)
