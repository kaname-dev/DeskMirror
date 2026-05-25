#include <3ds.h>
#include <arpa/inet.h>
#include <malloc.h>
#include <netinet/in.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <unistd.h>
#include <errno.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <setjmp.h>

#define SOC_ALIGN 0x1000
#define SOC_BUFFERSIZE 0x100000

#define CAST_PORT 7878
#define FRAME_MAGIC 0x33504353u /* '3PCS' */
#define FRAME_W 400
#define FRAME_H 240
#define FRAME_BYTES (FRAME_W * FRAME_H * 2)

static jmp_buf exitJmp;
static u32* socBuffer = nullptr;
static u8* frameBuf = nullptr;
static Result lastNetResult = 0;

struct __attribute__((packed)) FrameHeader {
    u32 magic;
    u16 width;
    u16 height;
};

static void cleanup(void) {
    if (frameBuf) {
        free(frameBuf);
        frameBuf = nullptr;
    }
    if (socBuffer) {
        socExit();
        free(socBuffer);
        socBuffer = nullptr;
    }
    acExit();
    gfxExit();
}

static void drawStatus(const char* line1, const char* line2, const char* line3);

static void hang(const char* message) {
    consoleClear();
    printf("\x1b[6;1H%s\n", message);
    if (lastNetResult != 0)
        printf("\x1b[12;1H  Error: 0x%08lX\n", (unsigned long)lastNetResult);
    printf("\x1b[20;1HSTART exit  Y retry\n");

    while (aptMainLoop()) {
        hidScanInput();
        u32 down = hidKeysDown();
        if (down & KEY_START)
            longjmp(exitJmp, 1);
        if (down & KEY_Y)
            return;
        gfxFlushBuffers();
        gspWaitForVBlank();
        gfxSwapBuffers();
    }
}

static bool waitForWifi(void) {
    for (int i = 0; i < 300; i++) {
        hidScanInput();
        if (hidKeysDown() & KEY_START)
            longjmp(exitJmp, 1);

        u32 wifiStatus = 0;
        if (R_SUCCEEDED(ACU_GetWifiStatus(&wifiStatus)) && wifiStatus != 0) {
            lastNetResult = acWaitInternetConnection();
            return R_SUCCEEDED(lastNetResult);
        }

        drawStatus("Connecting Wi-Fi...", "Enable wireless in", "System Settings");
        gfxFlushBuffers();
        gspWaitForVBlank();
        gfxSwapBuffers();
        svcSleepThread(200000000ULL);
    }
    lastNetResult = -2;
    return false;
}

static bool networkInit(void) {
    if (socBuffer) {
        socExit();
        free(socBuffer);
        socBuffer = nullptr;
    }

    socBuffer = (u32*)memalign(SOC_ALIGN, SOC_BUFFERSIZE);
    if (!socBuffer) {
        lastNetResult = -3;
        return false;
    }

    lastNetResult = socInit(socBuffer, SOC_BUFFERSIZE);
    return R_SUCCEEDED(lastNetResult);
}

static void formatIp(u32 addr, char* out, size_t outLen) {
    struct in_addr in;
    in.s_addr = addr;
    const char* s = inet_ntoa(in);
    if (s)
        snprintf(out, outLen, "%s", s);
    else
        snprintf(out, outLen, "?.?.?.?");
}

static void drawStatus(const char* line1, const char* line2, const char* line3) {
    consoleClear();
    printf("\x1b[1;1H  DeskMirror\n");
    printf("\x1b[3;1H  %s\n", line1);
    if (line2 && line2[0])
        printf("\x1b[5;1H  %s\n", line2);
    if (line3 && line3[0])
        printf("\x1b[7;1H  %s\n", line3);
    printf("\x1b[10;1H  Port: %d\n", CAST_PORT);
    printf("\x1b[12;1H  PC: python scripts/pc-cast.py\n");
    printf("\x1b[13;1H      --host <3DS IP>\n");
    printf("\x1b[14;1H  Top: 400x240\n");
    printf("\x1b[15;1H  START  Exit\n");
}

/* Update FPS line only (avoid consoleClear per frame). */
static void drawFpsOverlay(u32 fps) {
    printf("\x1b[7;1HStreaming  %3lu FPS    \n", (unsigned long)fps);
}

static void blitRGB565(u8* fb, const u16* src, u16 width, u16 height) {
    /* Top-screen VRAM is transposed (stride = height); same layout as the camera preview. */
    for (u16 y = 0; y < height; y++) {
        for (u16 x = 0; x < width; x++) {
            u16 px = src[y * width + x];
            u32 off = (height - y + x * height) * 3;
            fb[off] = (u8)((px & 0x1F) << 3);
            fb[off + 1] = (u8)(((px >> 5) & 0x3F) << 2);
            fb[off + 2] = (u8)(((px >> 11) & 0x1F) << 3);
        }
    }
}

static bool recvAll(int sock, void* buf, size_t len) {
    u8* p = (u8*)buf;
    size_t got = 0;
    while (got < len) {
        ssize_t n = recv(sock, p + got, len - got, 0);
        if (n <= 0)
            return false;
        got += (size_t)n;
    }
    return true;
}

static int acceptClient(int listenSock) {
    struct sockaddr_in clientAddr;
    socklen_t clientLen = sizeof(clientAddr);
    memset(&clientAddr, 0, sizeof(clientAddr));

    int clientSock = accept(listenSock, (struct sockaddr*)&clientAddr, &clientLen);
    if (clientSock < 0)
        return -1;
    if (SOCU_AddGlobalSocket(clientSock) != 0) {
        close(clientSock);
        return -1;
    }

    /* listen socket is non-blocking; accepted socket must block for recvAll(). */
    fcntl(clientSock, F_SETFL, fcntl(clientSock, F_GETFL, 0) & ~O_NONBLOCK);

    int rcvbuf = 256 * 1024;
    setsockopt(clientSock, SOL_SOCKET, SO_RCVBUF, &rcvbuf, sizeof(rcvbuf));

    return clientSock;
}

static int createListenSocket(void) {
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0)
        return -1;
    if (SOCU_AddGlobalSocket(sock) != 0) {
        close(sock);
        return -1;
    }

    int yes = 1;
    setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes));

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(CAST_PORT);
    addr.sin_addr.s_addr = htonl(INADDR_ANY);

    if (bind(sock, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        close(sock);
        return -1;
    }
    if (listen(sock, 1) < 0) {
        close(sock);
        return -1;
    }
    fcntl(sock, F_SETFL, fcntl(sock, F_GETFL, 0) | O_NONBLOCK);
    return sock;
}

static bool receiveFrame(int clientSock, u32* fpsCounter) {
    FrameHeader hdr;
    if (!recvAll(clientSock, &hdr, sizeof(hdr)))
        return false;
    if (hdr.magic != FRAME_MAGIC)
        return false;
    if (hdr.width != FRAME_W || hdr.height != FRAME_H)
        return false;
    if (!recvAll(clientSock, frameBuf, FRAME_BYTES))
        return false;

    u8* top = (u8*)gfxGetFramebuffer(GFX_TOP, GFX_LEFT, nullptr, nullptr);
    if (top) {
        gfxSet3D(false);
        blitRGB565(top, (const u16*)frameBuf, FRAME_W, FRAME_H);
    }
    (*fpsCounter)++;
    return true;
}

int main(int argc, char** argv) {
    (void)argc;
    (void)argv;

    acInit();
    gfxInitDefault();
    consoleInit(GFX_BOTTOM, nullptr);
    gfxSetDoubleBuffering(GFX_TOP, true);
    gfxSetDoubleBuffering(GFX_BOTTOM, false);

    if (setjmp(exitJmp)) {
        cleanup();
        return 0;
    }

    while (true) {
        if (!waitForWifi()) {
            hang("Wi-Fi not connected.\nTurn on wireless and retry.");
            continue;
        }
        if (networkInit())
            break;
        hang("Network init failed.\nEnable Wi-Fi and retry.");
    }

    char ipStr[32] = "?.?.?.?";
    struct in_addr ipInfo, mask, gw;
    if (SOCU_GetIPInfo(&ipInfo, &mask, &gw) == 0)
        formatIp(ipInfo.s_addr, ipStr, sizeof(ipStr));

    frameBuf = (u8*)malloc(FRAME_BYTES);
    if (!frameBuf)
        hang("Out of memory.");

    int listenSock = createListenSocket();
    while (listenSock < 0) {
        hang("Could not open port.\nCheck Wi-Fi connection.");
        listenSock = createListenSocket();
    }

    char status[64];
    snprintf(status, sizeof(status), "IP: %s", ipStr);
    drawStatus(status, "Waiting for PC...", nullptr);

    u32 frameCount = 0;
    u64 fpsTimer = osGetTime();
    u32 displayedFps = 0;

    drawStatus(status, "Waiting for PC...", nullptr);
    gfxFlushBuffers();
    gfxScreenSwapBuffers(GFX_BOTTOM, false);

    while (aptMainLoop()) {
        hidScanInput();
        if (hidKeysDown() & KEY_START)
            break;

        int clientSock = acceptClient(listenSock);
        if (clientSock < 0) {
            svcSleepThread(50000000ULL);
            continue;
        }

        snprintf(status, sizeof(status), "IP: %s", ipStr);
        drawStatus(status, "Connected", "Streaming...");
        frameCount = 0;
        fpsTimer = osGetTime();

        bool streaming = true;
        u32 lastFpsShown = 0;
        while (aptMainLoop() && streaming) {
            hidScanInput();
            if (hidKeysDown() & KEY_START) {
                streaming = false;
                break;
            }

            if (!receiveFrame(clientSock, &frameCount)) {
                drawStatus(status, "Connection lost", "Waiting for PC...");
                gfxFlushBuffers();
                gfxScreenSwapBuffers(GFX_BOTTOM, false);
                svcSleepThread(500000000ULL);
                break;
            }

            u64 now = osGetTime();
            if (now - fpsTimer >= 1000000000ULL) {
                displayedFps = frameCount;
                frameCount = 0;
                fpsTimer = now;
                if (displayedFps != lastFpsShown) {
                    drawFpsOverlay(displayedFps);
                    lastFpsShown = displayedFps;
                    gfxFlushBuffers();
                    gfxScreenSwapBuffers(GFX_BOTTOM, false);
                }
            }

            /* Swap top screen only — avoids bottom console flicker. */
            gfxFlushBuffers();
            gfxScreenSwapBuffers(GFX_TOP, false);
        }

        close(clientSock);
    }

    close(listenSock);
    cleanup();
    return 0;
}
