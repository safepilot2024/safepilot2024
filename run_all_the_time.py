import time
import subprocess

def run_script():
    script_path = "/home/test/carla-autoware-universe/op_carla_049_temp05/test/random_test_behavior_agent.py"
    subprocess.run(["python3", script_path], check=True)
    print(f"Script {script_path} executed")

def main():
    while True:
        run_script()
        time.sleep(1)  # 每分钟执行一次

if __name__ == "__main__":
    main()
