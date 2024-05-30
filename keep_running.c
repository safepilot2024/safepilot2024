#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/stat.h>

// 使用/proc目录检查进程是否存在
int process_exists(pid_t pid) {
    struct stat statbuf;
    char procpath[256];

    sprintf(procpath, "/proc/%d", pid);
    // 尝试获取目录的状态，如果成功，进程存在
    if (stat(procpath, &statbuf) == 0 && S_ISDIR(statbuf.st_mode)) {
        return 1;
    } else {
        return 0;
    }
}

// 删除文件
void delete_file(const char *filepath) {
    if (remove(filepath) != 0) {
        perror("Failed to delete file");
    } else {
        printf("File successfully deleted\n");
    }
}

int main() {
    pid_t pid;
    char filepath[] = "/home/test/carla-autoware-universe/op_carla_048_temp05/test/process_id.txt";
    FILE *file;

    while (1) {
        file = fopen(filepath, "r");
        if (file == NULL) {
            perror("Failed to open file");
            exit(EXIT_FAILURE);
        }
        fscanf(file, "%d", &pid);
        fclose(file);

        if (process_exists(pid)) {
            printf("Process %d is running...\n", pid);
        } else {
            printf("Process %d has stopped.\n", pid);
            delete_file(filepath);
            // sleep(60);
            sleep(10);
            printf("Maybe python stopped,wait a min!\n");

            // 终止特定的进程
            system("pkill -f CarlaUE4");
            system("pkill -SIGKILL -f ros");

            // 等待10秒
            sleep(10);

            // 启动新的进程
            system("gnome-terminal -- bash -c 'python3 random_test.py'");

            // 一次循环结束后等待60秒
        }
        // sleep(300);
        sleep(10);
    }

    return 0;
}