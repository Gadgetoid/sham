#include <algorithm>
#include <cfloat>
#include <cmath>

#define IMGUI_DEFINE_MATH_OPERATORS
#include "imgui.h"

#include "device.h"
#include "keys.h"
#include "lcd.h"

namespace {

const float GRID_W = LCD_WIDTH + 2 * LCD_MARGIN;
const float GRID_H = LCD_HEIGHT + 2 * LCD_MARGIN;
const float REFERENCE_LCD_H = 282.0f;
const float LEFT_EXTENT = 190.0f;
const float RIGHT_EXTENT = 195.0f;
const float TOP_EXTENT = 88.0f;
const float BOTTOM_EXTENT = 50.0f;
const float PLAIN_BEZEL = 30.0f;
const uint64_t REPEAT_DELAY_MS = 400;
const uint64_t REPEAT_RATE_MS = 80;

const ImU32 BEZEL = IM_COL32(182, 190, 194, 255);
const ImU32 BEZEL_EDGE = IM_COL32(112, 120, 126, 255);
const ImU32 BEZEL_LIGHT = IM_COL32(226, 232, 236, 255);
const ImU32 FRAME = IM_COL32(196, 204, 208, 255);
const ImU32 KEY_DARK = IM_COL32(40, 48, 58, 255);
const ImU32 KEY_DARK_SHEEN = IM_COL32(120, 132, 146, 70);
const ImU32 KEY_BLUE = IM_COL32(50, 94, 150, 255);
const ImU32 KEY_BLUE_SHEEN = IM_COL32(150, 190, 240, 80);
const ImU32 KEY_TEAL = IM_COL32(38, 118, 112, 255);
const ImU32 KEY_TEAL_SHEEN = IM_COL32(150, 220, 205, 80);
const ImU32 ICON_BLUE = IM_COL32(92, 168, 222, 255);
const ImU32 LABEL = IM_COL32(236, 240, 244, 255);
const ImU32 PRINT = IM_COL32(52, 58, 64, 255);
const ImU32 RECESS = IM_COL32(150, 158, 164, 255);
const ImU32 RECESS_FLOOR = IM_COL32(166, 174, 180, 255);

SDL_Texture *lcd_texture = nullptr;
ImFont *label_font = nullptr;

ImFont *font() {
    return label_font ? label_font : ImGui::GetFont();
}

struct KeyRepeat {
    bool active = false;
    uint64_t since = 0;
    uint64_t last = 0;
};

KeyRepeat repeats[2];

void upload_lcd(SDL_Renderer *renderer, float compose_seconds) {
    int w = lcd_compose_width(), h = lcd_compose_height();
    bool recreated = false;
    if (!lcd_texture || lcd_texture->w != w || lcd_texture->h != h) {
        if (lcd_texture) SDL_DestroyTexture(lcd_texture);
        lcd_texture = SDL_CreateTexture(renderer, SDL_PIXELFORMAT_RGBA32, SDL_TEXTUREACCESS_STREAMING, w, h);
        SDL_SetTextureScaleMode(lcd_texture, SDL_SCALEMODE_NEAREST);
        recreated = true;
    }
    bool composed = compose_seconds > 0 && lcd_compose(compose_seconds);
    if (composed || recreated) SDL_UpdateTexture(lcd_texture, nullptr, lcd_compose_pixels(), w * 4);
}

ImVec2 text_size(float size, const char *text) {
    return font()->CalcTextSizeA(size, FLT_MAX, 0.0f, text);
}

void centred_text(ImDrawList *draw, ImVec2 centre, float size, ImU32 colour, const char *text, bool bold = false) {
    ImVec2 extent = text_size(size, text);
    ImVec2 at = centre - extent * 0.5f;
    draw->AddText(font(), size, at, colour, text);
    if (bold && !label_font) draw->AddText(font(), size, at + ImVec2(0.6f, 0), colour, text);
}

void key_body(ImDrawList *draw, ImVec2 a, ImVec2 b, ImU32 base, ImU32 sheen, float rounding, bool pressed, float u,
              ImDrawFlags corners = ImDrawFlags_RoundCornersAll) {
    draw->AddRectFilled(a + ImVec2(0, 3.0f * u), b + ImVec2(0, 3.0f * u), IM_COL32(30, 36, 42, pressed ? 50 : 110), rounding, corners);
    ImVec2 dip = pressed ? ImVec2(0, 1.5f * u) : ImVec2(0, 0);
    draw->AddRectFilled(a + dip, b + dip, base, rounding, corners);
    if (!pressed) {
        ImVec2 sheen_a = a + ImVec2(2.5f * u, 1.5f * u);
        ImVec2 sheen_b = ImVec2(b.x - 2.5f * u, a.y + (b.y - a.y) * 0.48f);
        draw->AddRectFilled(sheen_a, sheen_b, sheen, rounding * 0.8f, corners & ImDrawFlags_RoundCornersTop);
    }
    draw->AddRect(a + dip, b + dip, IM_COL32(12, 16, 20, 170), rounding, corners, 1.0f);
}

void round_key(ImDrawList *draw, ImVec2 centre, float radius, ImU32 base, ImU32 sheen, bool pressed, float u) {
    draw->AddCircleFilled(centre + ImVec2(0, 3.0f * u), radius, IM_COL32(30, 36, 42, pressed ? 50 : 110));
    ImVec2 dip = pressed ? ImVec2(0, 1.5f * u) : ImVec2(0, 0);
    draw->AddCircleFilled(centre + dip, radius, base);
    if (!pressed) draw->AddCircleFilled(centre - ImVec2(0, radius * 0.35f), radius * 0.62f, sheen);
    draw->AddCircle(centre + dip, radius, IM_COL32(12, 16, 20, 170), 0, 1.0f);
}

bool hit(const char *id, ImVec2 a, ImVec2 b, bool &pressed) {
    ImGui::SetCursorScreenPos(a);
    ImGui::InvisibleButton(id, b - a);
    pressed = ImGui::IsItemActive();
    return ImGui::IsItemActivated();
}

void phone_glyph(ImDrawList *draw, ImVec2 c, float s, ImU32 colour) {
    ImVec2 body[4] = { c + ImVec2(-0.62f * s, 0.42f * s), c + ImVec2(0.62f * s, 0.42f * s),
                       c + ImVec2(0.38f * s, -0.02f * s), c + ImVec2(-0.38f * s, -0.02f * s) };
    draw->AddConvexPolyFilled(body, 4, colour);
    draw->AddCircleFilled(c + ImVec2(0, 0.2f * s), 0.12f * s, KEY_DARK);
    draw->AddBezierCubic(c + ImVec2(-0.7f * s, -0.1f * s), c + ImVec2(-0.75f * s, -0.55f * s),
                         c + ImVec2(0.75f * s, -0.55f * s), c + ImVec2(0.7f * s, -0.1f * s), colour, 0.2f * s);
}

void calendar_glyph(ImDrawList *draw, ImVec2 c, float s, ImU32 colour) {
    ImVec2 a = c + ImVec2(-0.5f * s, -0.42f * s), b = c + ImVec2(0.5f * s, 0.48f * s);
    draw->AddRect(a, b, colour, 1.5f, 0, 0.1f * s);
    draw->AddRectFilled(a, ImVec2(b.x, a.y + 0.18f * s), colour);
    draw->AddLine(c + ImVec2(-0.25f * s, -0.55f * s), c + ImVec2(-0.25f * s, -0.32f * s), colour, 0.1f * s);
    draw->AddLine(c + ImVec2(0.25f * s, -0.55f * s), c + ImVec2(0.25f * s, -0.32f * s), colour, 0.1f * s);
    centred_text(draw, c + ImVec2(0, 0.14f * s), 0.62f * s, colour, "1", true);
}

void memo_glyph(ImDrawList *draw, ImVec2 c, float s, ImU32 colour) {
    draw->AddRect(c + ImVec2(-0.62f * s, -0.38f * s), c + ImVec2(0.18f * s, 0.34f * s), colour, 1.5f, 0, 0.1f * s);
    draw->AddRectFilled(c + ImVec2(-0.45f * s, -0.52f * s), c + ImVec2(0.35f * s, 0.2f * s), KEY_DARK);
    draw->AddRect(c + ImVec2(-0.45f * s, -0.52f * s), c + ImVec2(0.35f * s, 0.2f * s), colour, 1.5f, 0, 0.1f * s);
    for (int line = 0; line < 3; line++) {
        float y = -0.36f * s + line * 0.16f * s;
        draw->AddLine(c + ImVec2(-0.32f * s, y), c + ImVec2(0.2f * s, y), colour, 0.07f * s);
    }
    draw->AddBezierQuadratic(c + ImVec2(0.55f * s, -0.2f * s), c + ImVec2(0.7f * s, 0.45f * s),
                             c + ImVec2(0.05f * s, 0.46f * s), colour, 0.12f * s);
    ImVec2 head[3] = { c + ImVec2(-0.1f * s, 0.46f * s), c + ImVec2(0.12f * s, 0.3f * s), c + ImVec2(0.12f * s, 0.62f * s) };
    draw->AddTriangleFilled(head[0], head[1], head[2], colour);
}

void lamp_glyph(ImDrawList *draw, ImVec2 c, float s, ImU32 colour) {
    ImVec2 bulb = c + ImVec2(-0.2f * s, 0);
    draw->AddCircle(bulb, 0.24f * s, colour, 0, 0.09f * s);
    draw->AddLine(bulb + ImVec2(-0.34f * s, -0.3f * s), bulb + ImVec2(-0.34f * s, 0.3f * s), colour, 0.1f * s);
    for (int ray = 0; ray < 5; ray++) {
        float angle = -1.1f + ray * 0.55f;
        ImVec2 dir(cosf(angle), sinf(angle));
        draw->AddLine(bulb + dir * (0.36f * s), bulb + dir * (0.58f * s), colour, 0.08f * s);
    }
}

void power_glyph(ImDrawList *draw, ImVec2 c, float s, ImU32 colour) {
    draw->PathArcTo(c, 0.32f * s, -M_PI * 0.5f + 0.7f, M_PI * 1.5f - 0.7f, 20);
    draw->PathStroke(colour, 0, 0.09f * s);
    draw->AddLine(c + ImVec2(0, -0.45f * s), c + ImVec2(0, -0.05f * s), colour, 0.09f * s);
}

void chevron(ImDrawList *draw, ImVec2 c, float s, bool up, ImU32 colour) {
    float dy = up ? 1.0f : -1.0f;
    ImVec2 points[3] = { c + ImVec2(-0.32f * s, 0.14f * s * dy), c + ImVec2(0, -0.16f * s * dy), c + ImVec2(0.32f * s, 0.14f * s * dy) };
    draw->AddPolyline(points, 3, colour, 0, 0.08f * s);
}

void recess(ImDrawList *draw, ImVec2 from, float from_radius, ImVec2 to, float to_radius, float u) {
    ImVec2 axis = to - from;
    float length = sqrtf(axis.x * axis.x + axis.y * axis.y);
    ImVec2 normal(-axis.y / length, axis.x / length);
    auto capsule = [&](ImVec2 offset, float grow, ImU32 colour) {
        ImVec2 quad[4] = { from + offset + normal * (from_radius + grow), to + offset + normal * (to_radius + grow),
                           to + offset - normal * (to_radius + grow), from + offset - normal * (from_radius + grow) };
        draw->AddConvexPolyFilled(quad, 4, colour);
        draw->AddCircleFilled(from + offset, from_radius + grow, colour);
        draw->AddCircleFilled(to + offset, to_radius + grow, colour);
    };
    capsule(ImVec2(1.0f * u, 1.0f * u), 1.0f * u, IM_COL32(210, 216, 220, 255));
    capsule(ImVec2(0, 0), 0, RECESS);
    capsule(ImVec2(1.2f * u, 1.2f * u), -1.6f * u, RECESS_FLOOR);
}

void repeat_key(KeyRepeat &repeat, uint32_t code, bool activated, bool pressed) {
    uint64_t now = SDL_GetTicks();
    if (activated) {
        keys_push(code, 0);
        keys_set_held(code, true);
        repeat = { true, now, now };
    } else if (pressed && repeat.active && now - repeat.since >= REPEAT_DELAY_MS && now - repeat.last >= REPEAT_RATE_MS) {
        keys_push(code, 0);
        repeat.last = now;
    } else if (!pressed && repeat.active) {
        keys_set_held(code, false);
        repeat.active = false;
    }
}

void draw_keys(ImDrawList *draw, ImVec2 lcd_min, ImVec2 lcd_max, float u, DeviceState &state) {
    auto ref = [&](float x, float y, bool from_right) {
        return ImVec2((from_right ? lcd_max.x : lcd_min.x) + x * u, lcd_min.y + y * u);
    };
    bool live = state.powered;

    struct SideKey { const char *id; uint32_t code; float y; };
    const SideKey side[] = {
        { "key-main", HOST_KEY_F1, -1 }, { "key-tel", HOST_KEY_F1 + 1, 55 }, { "key-cal", HOST_KEY_F1 + 2, 112 },
        { "key-memo", HOST_KEY_F1 + 3, 169 }, { "key-prog", HOST_KEY_F1 + 4, 225 },
    };
    for (int index = 0; index < 5; index++) {
        ImVec2 centre = ref(-125, side[index].y, false);
        ImVec2 a = centre - ImVec2(39, 18) * u, b = centre + ImVec2(39, 18) * u;
        bool pressed;
        if (hit(side[index].id, a, b, pressed) && live) keys_push(side[index].code, 0);
        key_body(draw, a, b, KEY_DARK, KEY_DARK_SHEEN, 9.0f * u, pressed, u);
        ImVec2 glyph = centre + (pressed ? ImVec2(0, 1.5f * u) : ImVec2(0, 0));
        float s = 26.0f * u;
        switch (index) {
            case 0: centred_text(draw, glyph, 17.0f * u, LABEL, "MAIN", true); break;
            case 1: phone_glyph(draw, glyph, s, ICON_BLUE); break;
            case 2: calendar_glyph(draw, glyph, s, ICON_BLUE); break;
            case 3: memo_glyph(draw, glyph, s, ICON_BLUE); break;
            default:
                centred_text(draw, glyph - ImVec2(0, 7.5f * u), 13.0f * u, LABEL, "My", true);
                centred_text(draw, glyph + ImVec2(0, 6.5f * u), 13.0f * u, LABEL, "Programs", true);
                break;
        }
    }

    {
        ImVec2 centre = ref(-125, 282, false);
        ImVec2 a = centre - ImVec2(28, 17) * u, b = centre + ImVec2(28, 17) * u;
        bool pressed;
        if (hit("key-light", a, b, pressed)) lcd_set_backlight(!lcd_get_backlight());
        key_body(draw, a, b, KEY_TEAL, KEY_TEAL_SHEEN, 17.0f * u, pressed, u);
        lamp_glyph(draw, centre + (pressed ? ImVec2(0, 1.5f * u) : ImVec2(0, 0)), 28.0f * u, LABEL);
    }

    {
        ImVec2 centre = ref(60, -2, true);
        centred_text(draw, centre - ImVec2(0, 39 * u), 15.0f * u, PRINT, "MENU");
        bool pressed;
        if (hit("key-menu", centre - ImVec2(20, 20) * u, centre + ImVec2(20, 20) * u, pressed) && live) keys_push(HOST_KEY_TAB, 0);
        round_key(draw, centre, 19.0f * u, KEY_DARK, KEY_DARK_SHEEN, pressed, u);
    }

    {
        ImVec2 centre = ref(135, -2, true);
        centred_text(draw, centre - ImVec2(0, 39 * u), 15.0f * u, PRINT, "POWER");
        ImVec2 a = centre - ImVec2(29, 15) * u, b = centre + ImVec2(29, 15) * u;
        bool pressed;
        if (hit("key-power", a, b, pressed)) {
            state.powered = !state.powered;
            lcd_set_power(state.powered);
        }
        key_body(draw, a, b, KEY_TEAL, KEY_TEAL_SHEEN, 15.0f * u, pressed, u);
        power_glyph(draw, centre + (pressed ? ImVec2(0, 1.5f * u) : ImVec2(0, 0)), 30.0f * u, LABEL);
    }

    struct ArrowKey { const char *id; uint32_t code; float top; bool up; };
    const ArrowKey arrows[] = { { "key-up", HOST_KEY_UP, 34, true }, { "key-down", HOST_KEY_DOWN, 117, false } };
    for (int index = 0; index < 2; index++) {
        ImVec2 a = ref(85, arrows[index].top, true), b = ref(167, arrows[index].top + 75, true);
        bool pressed;
        bool activated = hit(arrows[index].id, a, b, pressed);
        repeat_key(repeats[index], arrows[index].code, activated && live, pressed && live);
        ImDrawFlags corners = arrows[index].up
            ? ImDrawFlags_RoundCornersTopLeft | ImDrawFlags_RoundCornersTopRight | ImDrawFlags_RoundCornersBottomLeft
            : ImDrawFlags_RoundCornersBottomLeft | ImDrawFlags_RoundCornersBottomRight | ImDrawFlags_RoundCornersTopLeft;
        key_body(draw, a, b, KEY_BLUE, KEY_BLUE_SHEEN, 34.0f * u, pressed, u, corners);
        chevron(draw, (a + b) * 0.5f + (pressed ? ImVec2(0, 1.5f * u) : ImVec2(0, 0)), 60.0f * u, arrows[index].up, LABEL);
    }

    ImVec2 esc = ref(60, 210, true), enter = ref(130, 252, true);
    recess(draw, esc, 31.0f * u, enter, 44.0f * u, u);
    {
        bool pressed;
        if (hit("key-esc", esc - ImVec2(25, 25) * u, esc + ImVec2(25, 25) * u, pressed) && live) keys_push(HOST_KEY_ESC, 0);
        round_key(draw, esc, 25.0f * u, KEY_DARK, KEY_DARK_SHEEN, pressed, u);
        centred_text(draw, esc + (pressed ? ImVec2(0, 1.5f * u) : ImVec2(0, 0)), 15.0f * u, LABEL, "ESC", true);
    }
    {
        bool pressed;
        if (hit("key-enter", enter - ImVec2(38, 38) * u, enter + ImVec2(38, 38) * u, pressed) && live) keys_push(HOST_KEY_ENTER, 0);
        round_key(draw, enter, 38.0f * u, KEY_DARK, KEY_DARK_SHEEN, pressed, u);
        centred_text(draw, enter + (pressed ? ImVec2(0, 1.5f * u) : ImVec2(0, 0)), 16.0f * u, LABEL, "ENTER", true);
    }
}

}

float device_fit_height(float width, bool show_keys) {
    float usable = width - 16.0f;
    if (show_keys) {
        float image_h = usable / (GRID_W / GRID_H + (LEFT_EXTENT + RIGHT_EXTENT) / REFERENCE_LCD_H);
        return image_h * (1.0f + (TOP_EXTENT + BOTTOM_EXTENT) / REFERENCE_LCD_H) + 24.0f;
    }
    float lcd_w = usable - 2 * PLAIN_BEZEL;
    return lcd_w * GRID_H / GRID_W + 2 * PLAIN_BEZEL + 28.0f;
}

float device_draw(SDL_Renderer *renderer, float framebuffer_scale, float height, float compose_seconds, DeviceState &state) {
    ImVec2 origin = ImGui::GetCursorScreenPos();
    float avail_w = ImGui::GetContentRegionAvail().x;

    float image_h;
    if (state.show_keys) {
        float by_width = avail_w / (GRID_W / GRID_H + (LEFT_EXTENT + RIGHT_EXTENT) / REFERENCE_LCD_H);
        float by_height = height / (1.0f + (TOP_EXTENT + BOTTOM_EXTENT) / REFERENCE_LCD_H);
        image_h = std::min(by_width, by_height);
    } else {
        image_h = std::min((avail_w - 2 * PLAIN_BEZEL) * GRID_H / GRID_W, height - 2 * PLAIN_BEZEL);
    }
    int cell = std::max(2, (int)floorf(image_h * framebuffer_scale / GRID_H));
    lcd_compose_setup(cell);
    upload_lcd(renderer, compose_seconds);

    ImVec2 image_size(cell * GRID_W / framebuffer_scale, cell * GRID_H / framebuffer_scale);
    float u = image_size.y / REFERENCE_LCD_H;
    ImVec2 pad_min = state.show_keys ? ImVec2(LEFT_EXTENT, TOP_EXTENT) * u : ImVec2(PLAIN_BEZEL, PLAIN_BEZEL);
    ImVec2 pad_max = state.show_keys ? ImVec2(RIGHT_EXTENT, BOTTOM_EXTENT) * u : ImVec2(PLAIN_BEZEL, PLAIN_BEZEL);
    ImVec2 device_size = image_size + pad_min + pad_max;
    ImVec2 device_min = origin + ImVec2((avail_w - device_size.x) * 0.5f, (height - device_size.y) * 0.5f);
    ImVec2 device_max = device_min + device_size;
    ImVec2 image_min = device_min + pad_min;
    ImVec2 image_max = image_min + image_size;
    float rounding = state.show_keys ? 34.0f * u : 18.0f;

    ImDrawList *draw = ImGui::GetWindowDrawList();
    if (state.focused) {
        draw->AddRect(device_min - ImVec2(3, 3), device_max + ImVec2(3, 3), IM_COL32(90, 200, 180, 160), rounding + 4, 0, 2.0f);
    }
    draw->AddRectFilled(device_min + ImVec2(0, 4), device_max + ImVec2(0, 4), IM_COL32(0, 0, 0, 90), rounding);
    draw->AddRectFilled(device_min, device_max, BEZEL, rounding);
    draw->AddRectFilledMultiColor(device_min + ImVec2(rounding, 2), ImVec2(device_max.x - rounding, device_min.y + device_size.y * 0.45f),
                                  IM_COL32(255, 255, 255, 40), IM_COL32(255, 255, 255, 40), IM_COL32(255, 255, 255, 0), IM_COL32(255, 255, 255, 0));
    draw->AddRect(device_min, device_max, BEZEL_EDGE, rounding, 0, 2.0f);
    draw->AddRect(device_min + ImVec2(2, 2), device_max - ImVec2(2, 2), BEZEL_LIGHT, rounding - 2, 0, 1.0f);
    if (state.show_keys) {
        float latch_x = (image_min.x + image_max.x) * 0.5f;
        ImVec2 latch_a(latch_x - 26 * u, device_min.y - 5 * u), latch_b(latch_x + 26 * u, device_min.y + 11 * u);
        draw->AddRectFilled(latch_a, latch_b, IM_COL32(160, 168, 174, 255), 4 * u);
        draw->AddRect(latch_a, latch_b, BEZEL_EDGE, 4 * u, 0, 1.0f);
        draw->AddRectFilled(latch_a + ImVec2(8, 5) * u, latch_b - ImVec2(8, 7) * u, IM_COL32(70, 78, 84, 255), 2 * u);
    }

    if (state.show_keys) {
        ImVec2 frame_min = image_min - ImVec2(20, 18) * u, frame_max = image_max + ImVec2(20, 20) * u;
        draw->AddRectFilled(frame_min, frame_max, FRAME, 12.0f * u);
        draw->AddRect(frame_min, frame_max, BEZEL_LIGHT, 12.0f * u, 0, 1.5f);
        draw->AddRect(frame_min + ImVec2(1, 1), frame_max + ImVec2(1, 1), BEZEL_EDGE, 12.0f * u, 0, 1.0f);
    }
    draw->AddRectFilled(image_min - ImVec2(5, 5), image_max + ImVec2(5, 5), IM_COL32(58, 64, 68, 255), 5.0f);
    draw->AddRect(image_min - ImVec2(5, 5), image_max + ImVec2(5, 5), IM_COL32(210, 216, 220, 255), 5.0f, 0, 1.0f);
    if (lcd_texture) draw->AddImage((ImTextureID)(intptr_t)lcd_texture, image_min, image_max);

    ImGui::SetCursorScreenPos(image_min);
    ImGui::InvisibleButton("device", image_size);

    if (state.show_keys) {
        float brand = 24.0f * u;
        ImVec2 at = image_min + ImVec2(-4 * u, -50 * u);
        for (float nudge = 0; nudge < 1.5f; nudge += 0.5f) {
            draw->AddText(font(), brand, at + ImVec2(nudge * u, 0), PRINT, "POCKET");
            if (label_font) break;
        }
        draw->AddText(ImGui::GetFont(), 17.0f * u, at + ImVec2(text_size(brand, "POCKET").x + 18 * u, 5 * u), PRINT, "PZ-239");
        draw_keys(draw, image_min, image_max, u, state);
    } else {
        draw->AddText(device_min + ImVec2(PLAIN_BEZEL, 8), IM_COL32(60, 66, 72, 255), "POCKET  PZ-239");
    }

    ImGui::SetCursorScreenPos(origin + ImVec2(0, height));
    ImGui::Dummy(ImVec2(0, 0));
    return device_size.y;
}

void device_set_label_font(ImFont *font) {
    label_font = font;
}

void device_shutdown(void) {
    if (lcd_texture) SDL_DestroyTexture(lcd_texture);
    lcd_texture = nullptr;
}
