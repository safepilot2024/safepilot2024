import random

ATTACK_SUCCESS = False
COLLISION_OBJECT = None
ATTACK_COLLISION_OBJECT = None
REWIND=False

#天气
weather_dict = {"cloud":random.randint(0, 100),
                    "rain":random.randint(0, 20),
                    "puddle":random.randint(0, 100),
                    "wetness":random.randint(0, 20),
                    "wind":random.randint(0, 100),
                    "fog":random.randint(0, 20),
                    "angle":random.randint(0, 100),
                    "altitude":random.randint(0, 100)}

#初始化速度 帧率 速度限制
class Config():
    def __init__(self) :
        self.speed=8
        self.FRAME_RATE=30
        self.speed_limit=5