#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    const char *root_path;
    const char *data_path;
    const char *main_path;
} host_config_t;

uint32_t host_ticks_ms(void);
void     host_yield_to_main(void);

#ifdef __cplusplus
}
#endif
