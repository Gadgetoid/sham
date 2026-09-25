#pragma once
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

bool watch_start(const char *root);
bool watch_add(const char *root);
void watch_mute(unsigned ms);
bool watch_poll(void);
void watch_stop(void);

#ifdef __cplusplus
}
#endif
