#include "keys.h"

#define KEY_QUEUE_SIZE 256

static host_key_t queue[KEY_QUEUE_SIZE];
static unsigned head = 0, tail = 0;

void keys_push(uint32_t code, uint8_t mods) {
    unsigned next = (head + 1) % KEY_QUEUE_SIZE;
    if (next == tail) return;
    queue[head] = (host_key_t){ code, mods };
    head = next;
}

bool keys_pop(host_key_t *out) {
    if (tail == head) return false;
    *out = queue[tail];
    tail = (tail + 1) % KEY_QUEUE_SIZE;
    return true;
}

void keys_clear(void) {
    head = tail = 0;
}
