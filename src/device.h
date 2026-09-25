#pragma once
#include <SDL3/SDL.h>

struct ImFont;

struct DeviceState {
    bool show_keys = true;
    bool focused = true;
    bool powered = true;
};

float device_draw(SDL_Renderer *renderer, float framebuffer_scale, float height, float compose_seconds, DeviceState &state);
float device_fit_height(float width, bool show_keys);
void  device_shutdown(void);
void  device_set_label_font(ImFont *font);
void  device_set_icon_font(ImFont *font);
