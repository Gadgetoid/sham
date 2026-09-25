#include <algorithm>
#include <cfloat>
#include <cmath>
#include <cstring>
#include <vector>

#define IMGUI_DEFINE_MATH_OPERATORS
#include "imgui.h"
#include "imgui_internal.h"

#include "device.h"
#include "key_shapes.h"
#include "keys.h"
#include "lcd.h"

namespace {

using Shape = std::vector<ImVec2>;

const float GRID_W = LCD_WIDTH + 2 * LCD_MARGIN;
const float GRID_H = LCD_HEIGHT + 2 * LCD_MARGIN;
const float REFERENCE_LCD_H = 282.0f;
const float LEFT_EXTENT = 202.0f;
const float RIGHT_EXTENT = 214.0f;
const float TOP_EXTENT = 91.0f;
const float BOTTOM_EXTENT = 48.0f;
const float PLAIN_BEZEL = 30.0f;
const float FLUTE_MARGIN = 3.5f;
const float WELL_MARGIN = 4.0f;
const float ARROW_WELL_MARGIN = 7.0f;
const uint64_t REPEAT_DELAY_MS = 400;
const uint64_t REPEAT_RATE_MS = 80;

const ImU32 BEZEL = IM_COL32(182, 190, 194, 255);
const ImU32 BEZEL_EDGE = IM_COL32(112, 120, 126, 255);
const ImU32 BEZEL_LIGHT = IM_COL32(226, 232, 236, 255);
const ImU32 FRAME = IM_COL32(196, 204, 208, 255);
const ImU32 RECESS_TOP = IM_COL32(150, 158, 164, 255);
const ImU32 RECESS_BOTTOM = IM_COL32(186, 194, 198, 255);
const ImU32 LABEL = IM_COL32(236, 240, 244, 255);
const ImU32 PRINT = IM_COL32(52, 58, 64, 255);
const ImU32 ICON_BLUE = IM_COL32(96, 172, 226, 255);

struct KeyStyle {
    ImU32 top;
    ImU32 bottom;
};

const KeyStyle DARK_KEY = { IM_COL32(70, 80, 92, 255), IM_COL32(30, 37, 46, 255) };
const KeyStyle BLUE_KEY = { IM_COL32(82, 126, 186, 255), IM_COL32(42, 80, 132, 255) };
const KeyStyle TEAL_KEY = { IM_COL32(68, 150, 140, 255), IM_COL32(30, 102, 96, 255) };

const unsigned ICON_CALL = 0xe0b0;
const unsigned ICON_CALENDAR = 0xebcc;
const unsigned ICON_NOTE = 0xf1fc;
const unsigned ICON_LIGHT = 0xe518;
const unsigned ICON_POWER = 0xe8ac;
const unsigned ICON_UP = 0xe316;
const unsigned ICON_DOWN = 0xe313;

SDL_Texture *lcd_texture = nullptr;
ImFont *label_font = nullptr;
ImFont *icon_font = nullptr;

struct KeyRepeat {
    bool active = false;
    uint64_t since = 0;
    uint64_t last = 0;
};

KeyRepeat repeats[2];

struct Frame {
    ImVec2 lcd_min;
    ImVec2 lcd_max;
    float u;

    ImVec2 at(float x, float y, bool right) const {
        return ImVec2((right ? lcd_max.x : lcd_min.x) + x * u, lcd_min.y + y * u);
    }
};

ImFont *text_font() {
    return label_font ? label_font : ImGui::GetFont();
}

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

ImVec2 text_size(ImFont *font, float size, const char *text) {
    return font->CalcTextSizeA(size, FLT_MAX, 0.0f, text);
}

void centred_text(ImDrawList *draw, ImVec2 centre, float size, ImU32 colour, const char *text) {
    ImVec2 extent = text_size(text_font(), size, text);
    draw->AddText(text_font(), size, centre - extent * 0.5f, colour, text);
}

void icon(ImDrawList *draw, ImVec2 centre, float size, ImU32 colour, unsigned codepoint) {
    char utf8[4] = { (char)(0xe0 | (codepoint >> 12)), (char)(0x80 | ((codepoint >> 6) & 0x3f)),
                     (char)(0x80 | (codepoint & 0x3f)), 0 };
    ImFont *font = icon_font ? icon_font : ImGui::GetFont();
    ImVec2 extent = text_size(font, size, utf8);
    draw->AddText(font, size, centre - extent * 0.5f, colour, utf8);
}

void add_arc(Shape &shape, ImVec2 centre, float radius, float from, float to, int segments) {
    for (int i = 0; i <= segments; i++) {
        float angle = from + (to - from) * i / segments;
        shape.push_back(centre + ImVec2(cosf(angle), sinf(angle)) * radius);
    }
}

Shape translated(const Shape &shape, ImVec2 offset) {
    Shape result = shape;
    for (ImVec2 &point : result) point += offset;
    return result;
}

Shape circle(ImVec2 centre, float radius) {
    Shape shape;
    add_arc(shape, centre, radius, 0, 2 * IM_PI, 48);
    shape.pop_back();
    return shape;
}

Shape pill(ImVec2 a, ImVec2 b) {
    float r = (b.y - a.y) * 0.5f;
    Shape shape;
    add_arc(shape, ImVec2(a.x + r, a.y + r), r, IM_PI * 0.5f, IM_PI * 1.5f, 20);
    add_arc(shape, ImVec2(b.x - r, a.y + r), r, IM_PI * 1.5f, IM_PI * 2.5f, 20);
    return shape;
}

Shape capsule(ImVec2 from, float from_r, ImVec2 to, float to_r) {
    ImVec2 axis = to - from;
    float distance = sqrtf(axis.x * axis.x + axis.y * axis.y);
    float theta = atan2f(axis.y, axis.x);
    float phi = asinf((from_r - to_r) / distance);
    float alpha = theta + IM_PI * 0.5f + phi;
    float beta = theta - IM_PI * 0.5f - phi;
    Shape shape;
    add_arc(shape, from, from_r, alpha, beta + 2 * IM_PI, 28);
    add_arc(shape, to, to_r, beta + 2 * IM_PI, alpha + 2 * IM_PI, 28);
    return shape;
}

Shape smooth(const Shape &shape, int passes) {
    Shape result = shape;
    for (int pass = 0; pass < passes; pass++) {
        Shape next;
        size_t count = result.size();
        for (size_t i = 0; i < count; i++) {
            ImVec2 a = result[i], b = result[(i + 1) % count];
            next.push_back(a * 0.75f + b * 0.25f);
            next.push_back(a * 0.25f + b * 0.75f);
        }
        result = next;
    }
    return result;
}

float cross(ImVec2 o, ImVec2 a, ImVec2 b) {
    return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
}

Shape hull(Shape points) {
    std::sort(points.begin(), points.end(), [](ImVec2 a, ImVec2 b) { return a.x < b.x || (a.x == b.x && a.y < b.y); });
    Shape result(points.size() * 2);
    size_t k = 0;
    for (size_t i = 0; i < points.size(); i++) {
        while (k >= 2 && cross(result[k - 2], result[k - 1], points[i]) <= 0) k--;
        result[k++] = points[i];
    }
    for (size_t i = points.size() - 1, t = k + 1; i > 0; i--) {
        while (k >= t && cross(result[k - 2], result[k - 1], points[i - 1]) <= 0) k--;
        result[k++] = points[i - 1];
    }
    result.resize(k - 1);
    return result;
}

Shape grown(const Shape &shape, float margin) {
    Shape result;
    size_t count = shape.size();
    for (size_t i = 0; i < count; i++) {
        ImVec2 before = shape[(i + count - 1) % count], after = shape[(i + 1) % count];
        ImVec2 tangent = after - before;
        float length = sqrtf(tangent.x * tangent.x + tangent.y * tangent.y);
        if (length == 0) continue;
        ImVec2 normal(tangent.y / length, -tangent.x / length);
        result.push_back(shape[i] - normal * margin);
    }
    return result;
}

Shape traced(const Frame &frame, const char *name) {
    for (const TracedKey &key : traced_keys) {
        if (strcmp(key.name, name) != 0) continue;
        Shape shape;
        for (int i = 0; i < key.count; i++) shape.push_back(frame.at(key.points[i * 2], key.points[i * 2 + 1], key.right));
        return smooth(hull(shape), 2);
    }
    return Shape();
}

ImRect bounds(const Shape &shape) {
    ImRect box(shape[0], shape[0]);
    for (const ImVec2 &point : shape) box.Add(point);
    return box;
}

ImVec2 centroid(const Shape &shape) {
    ImVec2 sum(0, 0);
    for (const ImVec2 &point : shape) sum += point;
    return sum / (float)shape.size();
}

void fill(ImDrawList *draw, const Shape &shape, ImU32 top, ImU32 bottom) {
    ImRect box = bounds(shape);
    int start = draw->VtxBuffer.Size;
    draw->AddConvexPolyFilled(shape.data(), (int)shape.size(), top);
    ImGui::ShadeVertsLinearColorGradientKeepAlpha(draw, start, draw->VtxBuffer.Size, ImVec2(0, box.Min.y),
                                                  ImVec2(0, box.Max.y), top, bottom);
}

void stroke(ImDrawList *draw, const Shape &shape, ImU32 colour, float thickness) {
    draw->AddPolyline(shape.data(), (int)shape.size(), colour, ImDrawFlags_Closed, thickness);
}

void stroke_band(ImDrawList *draw, const Shape &shape, ImU32 colour, float thickness, float from, float to) {
    ImRect box = bounds(shape);
    float height = box.Max.y - box.Min.y;
    draw->PushClipRect(ImVec2(box.Min.x - 4, box.Min.y + height * from - 2), ImVec2(box.Max.x + 4, box.Min.y + height * to + 2), true);
    stroke(draw, shape, colour, thickness);
    draw->PopClipRect();
}

void recess(ImDrawList *draw, const Shape &shape, float u) {
    fill(draw, shape, RECESS_TOP, RECESS_BOTTOM);
    stroke_band(draw, shape, IM_COL32(96, 104, 110, 150), 1.4f * u, 0.0f, 0.5f);
    stroke_band(draw, translated(shape, ImVec2(0, 0.6f * u)), IM_COL32(238, 242, 246, 190), 1.2f * u, 0.55f, 1.0f);
}

void key(ImDrawList *draw, const Shape &shape, const KeyStyle &style, bool pressed, float u) {
    const int layers = 4;
    for (int layer = layers; layer >= 1; layer--) {
        int alpha = (pressed ? 10 : 18) + (layers - layer) * 4;
        fill(draw, translated(shape, ImVec2(0, layer * 0.8f * u)), IM_COL32(20, 26, 32, alpha), IM_COL32(20, 26, 32, alpha));
    }
    Shape body = translated(shape, ImVec2(0, pressed ? 1.2f * u : 0));
    fill(draw, body, pressed ? style.bottom : style.top, style.bottom);
    stroke(draw, body, IM_COL32(10, 14, 18, 110), 1.0f);
    if (!pressed) {
        stroke_band(draw, translated(body, ImVec2(0, 0.7f * u)), IM_COL32(255, 255, 255, 42), 1.6f * u, 0.0f, 0.35f);
        stroke_band(draw, translated(body, ImVec2(0, 0.4f * u)), IM_COL32(255, 255, 255, 70), 0.9f * u, 0.0f, 0.18f);
    }
    stroke_band(draw, translated(body, ImVec2(0, -0.4f * u)), IM_COL32(255, 255, 255, 28), 1.0f, 0.75f, 1.0f);
}

bool hit(const char *id, const Shape &shape, bool &pressed) {
    ImRect box = bounds(shape);
    ImGui::SetCursorScreenPos(box.Min);
    ImGui::InvisibleButton(id, box.GetSize());
    pressed = ImGui::IsItemActive();
    return ImGui::IsItemActivated();
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

void draw_keys(ImDrawList *draw, const Frame &frame, ImVec2 device_min, ImVec2 device_max, DeviceState &state) {
    float u = frame.u;
    bool live = state.powered;
    ImVec2 press(0, 1.2f * u);
    auto dip = [&](bool pressed) { return pressed ? press : ImVec2(0, 0); };

    const char *side_names[] = { "main", "tel", "cal", "memo", "prog" };
    ImVec2 menu_centre = frame.at(fit_menu[0], fit_menu[1], true);
    ImVec2 esc_centre = frame.at(fit_esc[0], fit_esc[1], true);
    ImVec2 enter_centre = frame.at(fit_enter[0], fit_enter[1], true);
    Shape power = traced(frame, "power");
    ImRect power_box = bounds(power);

    draw->PushClipRect(device_min, device_max, true);
    for (const char *name : side_names) {
        ImRect box = bounds(traced(frame, name));
        ImVec2 a(device_min.x - 20 * u, box.Min.y - FLUTE_MARGIN * u);
        ImVec2 b(box.Min.x + box.GetHeight() * 0.5f + 6 * u, box.Max.y + FLUTE_MARGIN * u);
        recess(draw, pill(a, b), u);
    }
    recess(draw, pill(power_box.Min - ImVec2(FLUTE_MARGIN, FLUTE_MARGIN) * u,
                      ImVec2(device_max.x + 20 * u, power_box.Max.y + FLUTE_MARGIN * u)), u);
    {
        Shape both = traced(frame, "up");
        Shape down = traced(frame, "down");
        both.insert(both.end(), down.begin(), down.end());
        ImRect box = bounds(both);
        both.push_back(ImVec2(device_max.x + 20 * u, box.Min.y));
        both.push_back(ImVec2(device_max.x + 20 * u, box.Max.y));
        recess(draw, smooth(grown(hull(both), ARROW_WELL_MARGIN * u), 1), u);
    }
    draw->PopClipRect();

    struct SideKey { const char *id; uint32_t code; const char *text; unsigned glyph; };
    const SideKey side[] = {
        { "key-main", HOST_KEY_F1, "MAIN", 0 }, { "key-tel", HOST_KEY_F1 + 1, nullptr, ICON_CALL },
        { "key-cal", HOST_KEY_F1 + 2, nullptr, ICON_CALENDAR }, { "key-memo", HOST_KEY_F1 + 3, nullptr, ICON_NOTE },
        { "key-prog", HOST_KEY_F1 + 4, nullptr, 0 },
    };
    for (int index = 0; index < 5; index++) {
        Shape shape = traced(frame, side_names[index]);
        bool pressed;
        if (hit(side[index].id, shape, pressed) && live) keys_push(side[index].code, 0);
        key(draw, shape, DARK_KEY, pressed, u);
        ImVec2 at = bounds(shape).GetCenter() + ImVec2(2 * u, 0) + dip(pressed);
        if (side[index].text) {
            centred_text(draw, at, 17.0f * u, LABEL, side[index].text);
        } else if (side[index].glyph) {
            icon(draw, at, 44.0f * u, ICON_BLUE, side[index].glyph);
        } else {
            centred_text(draw, at - ImVec2(0, 7.5f * u), 13.0f * u, LABEL, "My");
            centred_text(draw, at + ImVec2(0, 6.5f * u), 13.0f * u, LABEL, "Programs");
        }
    }

    {
        Shape shape = traced(frame, "light");
        ImRect box = bounds(shape);
        recess(draw, pill(box.Min - ImVec2(WELL_MARGIN, WELL_MARGIN) * u, box.Max + ImVec2(WELL_MARGIN, WELL_MARGIN) * u), u);
        bool pressed;
        if (hit("key-light", shape, pressed)) lcd_set_backlight(!lcd_get_backlight());
        key(draw, shape, TEAL_KEY, pressed, u);
        icon(draw, box.GetCenter() + dip(pressed), 34.0f * u, LABEL, ICON_LIGHT);
    }

    {
        centred_text(draw, menu_centre - ImVec2(0, 39 * u), 15.0f * u, PRINT, "MENU");
        recess(draw, circle(menu_centre, (fit_menu[2] + WELL_MARGIN) * u), u);
        Shape shape = circle(menu_centre, fit_menu[2] * u);
        bool pressed;
        if (hit("key-menu", shape, pressed) && live) keys_push(HOST_KEY_TAB, 0);
        key(draw, shape, DARK_KEY, pressed, u);
    }

    {
        centred_text(draw, ImVec2(power_box.GetCenter().x, menu_centre.y - 39 * u), 15.0f * u, PRINT, "POWER");
        bool pressed;
        if (hit("key-power", power, pressed)) {
            state.powered = !state.powered;
            lcd_set_power(state.powered);
        }
        key(draw, power, TEAL_KEY, pressed, u);
        icon(draw, power_box.GetCenter() + dip(pressed), 32.0f * u, LABEL, ICON_POWER);
    }

    struct ArrowKey { const char *id; const char *shape; uint32_t code; unsigned glyph; };
    const ArrowKey arrows[] = { { "key-up", "up", HOST_KEY_UP, ICON_UP }, { "key-down", "down", HOST_KEY_DOWN, ICON_DOWN } };
    for (int index = 0; index < 2; index++) {
        Shape shape = traced(frame, arrows[index].shape);
        bool pressed;
        bool activated = hit(arrows[index].id, shape, pressed);
        repeat_key(repeats[index], arrows[index].code, activated && live, pressed && live);
        key(draw, shape, BLUE_KEY, pressed, u);
        icon(draw, centroid(shape) + dip(pressed), 76.0f * u, LABEL, arrows[index].glyph);
    }

    recess(draw, capsule(esc_centre, (fit_esc[2] + 5) * u, enter_centre, (fit_enter[2] + 5) * u), u);
    {
        Shape shape = circle(esc_centre, fit_esc[2] * u);
        bool pressed;
        if (hit("key-esc", shape, pressed) && live) keys_push(HOST_KEY_ESC, 0);
        key(draw, shape, DARK_KEY, pressed, u);
        centred_text(draw, esc_centre + dip(pressed), 15.0f * u, LABEL, "ESC");
    }
    {
        Shape shape = circle(enter_centre, fit_enter[2] * u);
        bool pressed;
        if (hit("key-enter", shape, pressed) && live) keys_push(HOST_KEY_ENTER, 0);
        key(draw, shape, DARK_KEY, pressed, u);
        centred_text(draw, enter_centre + dip(pressed), 16.0f * u, LABEL, "ENTER");
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

    if (state.show_keys) {
        float latch_x = (image_min.x + image_max.x) * 0.5f;
        ImVec2 latch_a(latch_x - 26 * u, device_min.y - 5 * u), latch_b(latch_x + 26 * u, device_min.y + 11 * u);
        draw->AddRectFilled(latch_a, latch_b, IM_COL32(160, 168, 174, 255), 4 * u);
        draw->AddRect(latch_a, latch_b, BEZEL_EDGE, 4 * u, 0, 1.0f);
        draw->AddRectFilled(latch_a + ImVec2(8, 5) * u, latch_b - ImVec2(8, 7) * u, IM_COL32(70, 78, 84, 255), 2 * u);

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
        draw->AddText(text_font(), brand, at, PRINT, "POCKET");
        draw->AddText(ImGui::GetFont(), 17.0f * u, at + ImVec2(text_size(text_font(), brand, "POCKET").x + 18 * u, 5 * u), PRINT, "PZ-239");
        draw_keys(draw, Frame{ image_min, image_max, u }, device_min, device_max, state);
    } else {
        draw->AddText(device_min + ImVec2(PLAIN_BEZEL, 8), IM_COL32(60, 66, 72, 255), "POCKET  PZ-239");
    }

    draw->AddRect(device_min, device_max, BEZEL_EDGE, rounding, 0, 2.0f);
    draw->AddRect(device_min + ImVec2(2, 2), device_max - ImVec2(2, 2), BEZEL_LIGHT, rounding - 2, 0, 1.0f);

    ImGui::SetCursorScreenPos(origin + ImVec2(0, height));
    ImGui::Dummy(ImVec2(0, 0));
    return device_size.y;
}

void device_set_label_font(ImFont *font) {
    label_font = font;
}

void device_set_icon_font(ImFont *font) {
    icon_font = font;
}

void device_shutdown(void) {
    if (lcd_texture) SDL_DestroyTexture(lcd_texture);
    lcd_texture = nullptr;
}
