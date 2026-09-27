#ifdef _WIN32
#define _CRT_RAND_S
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "py/mphal.h"
#include "console.h"
#include "host.h"

static char *capture = NULL;
static size_t capture_len = 0, capture_size = 0;
static bool capturing = false;

void mp_hal_stdout_tx_strn_cooked(const char *str, size_t len) {
    if (capturing) {
        if (capture_len + len + 1 > capture_size) {
            capture_size = (capture_len + len + 1) * 2;
            capture = realloc(capture, capture_size);
        }
        memcpy(capture + capture_len, str, len);
        capture_len += len;
        capture[capture_len] = '\0';
        return;
    }
    console_write(str, len);
    fwrite(str, 1, len, stdout);
}

void host_capture_start(void) {
    capturing = true;
    capture_len = 0;
    if (capture) capture[0] = '\0';
}

const char *host_capture_stop(size_t *len) {
    capturing = false;
    *len = capture_len;
    return capture ? capture : "";
}

mp_uint_t mp_hal_ticks_ms(void) {
    return host_ticks_ms();
}

void mp_hal_set_interrupt_char(int c) {
    (void)c;
}

uint32_t host_random_seed(void) {
#ifdef _WIN32
    unsigned int seed = 0;
    rand_s(&seed);
    return seed;
#else
    return arc4random();
#endif
}
