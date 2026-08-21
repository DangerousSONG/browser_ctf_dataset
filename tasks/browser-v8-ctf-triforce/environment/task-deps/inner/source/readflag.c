#include <unistd.h>
#include <string.h>
#include <stdio.h>
#include <fcntl.h>

int main(int argc, char **argv){
    char flag[128];
    memset(flag, 0, sizeof(flag));
    int fd = open("/flag", 0);
    ssize_t sz = read(fd, flag, sizeof(flag));
    if(sz>0) write(1, flag, sz);
    else puts("Error! Please open a ticket.");
    return 0;
}