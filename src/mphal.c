#include <stdio.h>
#include <stdlib.h>

#include "py/mphal.h"
#include "console.h"
#include "host.h"

void mp_hal_stdout_tx_strn_cooked(const char *str, size_t len) {
    console_write(str, len);
    fwrite(str, 1, len, stdout);
}

mp_uint_t mp_hal_ticks_ms(void) {
    return host_ticks_ms();
}

void mp_hal_set_interrupt_char(int c) {
    (void)c;
}

uint32_t host_random_seed(void) {
    return arc4random();
}
