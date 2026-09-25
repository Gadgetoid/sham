#include <stdatomic.h>
#include <stdio.h>
#include <string.h>

#define DMON_IMPL
#include "dmon.h"

#include "host.h"
#include "watch.h"

#define SETTLE_MS 150

static atomic_uint last_change_ms = 0;
static atomic_bool pending = false;
static bool running = false;
static atomic_uint mute_until = 0;

static bool ignored(const char *path) {
    if (strstr(path, "__pycache__")) return true;
    const char *name = strrchr(path, '/');
    name = name ? name + 1 : path;
    if (name[0] == '.') return true;
    size_t len = strlen(name);
    return len > 0 && name[len - 1] == '~';
}

static void on_change(dmon_watch_id id, dmon_action action, const char *root,
                      const char *path, const char *old_path, void *user) {
    (void)id; (void)action; (void)root; (void)old_path; (void)user;
    if (ignored(path)) return;
    if ((int)(atomic_load(&mute_until) - host_ticks_ms()) > 0) return;
    atomic_store(&last_change_ms, host_ticks_ms());
    atomic_store(&pending, true);
}

bool watch_start(const char *root) {
    dmon_init();
    running = true;
    dmon_watch_id id = dmon_watch(root, on_change, DMON_WATCHFLAGS_RECURSIVE, NULL);
    if (id.id == 0) {
        fprintf(stderr, "pocket: cannot watch %s\n", root);
        return false;
    }
    return true;
}

bool watch_add(const char *root) {
    if (!running) {
        dmon_init();
        running = true;
    }
    dmon_watch_id id = dmon_watch(root, on_change, DMON_WATCHFLAGS_RECURSIVE, NULL);
    return id.id != 0;
}

void watch_mute(unsigned ms) {
    atomic_store(&mute_until, host_ticks_ms() + ms);
    atomic_store(&pending, false);
}

bool watch_poll(void) {
    if (!atomic_load(&pending)) return false;
    if (host_ticks_ms() - atomic_load(&last_change_ms) < SETTLE_MS) return false;
    atomic_store(&pending, false);
    return true;
}

void watch_stop(void) {
    if (running) dmon_deinit();
    running = false;
}
