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
const float ARROW_WELL_MARGIN = 4.0f;
const ImVec2 ARROW_CENTRE(181.1f, 113.5f);
const float ARROW_R = 80.5f;
const float ARROW_GAP_Y = 113.5f;
const float ARROW_HALF_GAP = 6.8f;
const float ARROW_EDGE_X = 179.2f;
const float ARROW_EDGE_R = 560.0f;
const float ARROW_CORNER = 15.0f;
const float ARROW_WELL_TUCK = 3.0f;
const float ARROW_WELL_FLAT = -91.06f;
const float ARROW_KEY_FLAT = -86.06f;
const float ARROW_SOFTNESS = 6.0f;
const float ARROW_WELL_CORNER = 12.0f;
const float FLUTE_REACH = 0.45f;
const float SIDE_KEY_CORNER = 6.0f;
const uint64_t REPEAT_DELAY_MS = 400;
const uint64_t REPEAT_RATE_MS = 80;

const ImU32 BEZEL = IM_COL32(182, 190, 194, 255);
const ImU32 BEZEL_EDGE = IM_COL32(112, 120, 126, 255);
const ImU32 BEZEL_LIGHT = IM_COL32(226, 232, 236, 255);
const ImU32 FRAME = IM_COL32(196, 204, 208, 255);
const ImU32 LABEL = IM_COL32(236, 240, 244, 255);
const ImU32 PRINT = IM_COL32(52, 58, 64, 255);
const ImU32 ICON_BLUE = IM_COL32(96, 172, 226, 255);

struct ButtonStyle {
    ImU32 top;
    ImU32 bottom;
    int rim = 42;
    float gap = 1.6f;
    float shadow = 1.0f;
    float dome = 0.0f;
};

const ButtonStyle DARK_KEY = { IM_COL32(70, 80, 92, 255), IM_COL32(30, 37, 46, 255) };
const ButtonStyle DARK_DOMED_KEY = { IM_COL32(70, 80, 92, 255), IM_COL32(30, 37, 46, 255), 42, 1.6f, 1.0f, 1.0f };
const ButtonStyle BLUE_KEY = { IM_COL32(82, 126, 186, 255), IM_COL32(42, 80, 132, 255) };
const ButtonStyle TEAL_KEY = { IM_COL32(68, 150, 140, 255), IM_COL32(30, 102, 96, 255) };

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

Shape side_key(ImVec2 a, ImVec2 b, float corner) {
    float r = (b.y - a.y) * 0.5f;
    Shape shape;
    add_arc(shape, ImVec2(a.x + r, a.y + r), r, IM_PI * 0.5f, IM_PI * 1.5f, 32);
    add_arc(shape, ImVec2(b.x - corner, a.y + corner), corner, IM_PI * 1.5f, IM_PI * 2.0f, 10);
    add_arc(shape, ImVec2(b.x - corner, b.y - corner), corner, 0, IM_PI * 0.5f, 10);
    return shape;
}

Shape capsule(ImVec2 from, float from_r, ImVec2 to, float to_r) {
    ImVec2 axis = to - from;
    float distance = sqrtf(axis.x * axis.x + axis.y * axis.y);
    float theta = atan2f(axis.y, axis.x);
    float phi = asinf((from_r - to_r) / distance);
    float alpha = theta + IM_PI * 0.5f - phi;
    float beta = theta - IM_PI * 0.5f + phi;
    Shape shape;
    add_arc(shape, from, from_r, alpha, beta + 2 * IM_PI, 48);
    add_arc(shape, to, to_r, beta + 2 * IM_PI, alpha + 2 * IM_PI, 48);
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

float signed_area(const Shape &shape) {
    float area = 0;
    for (size_t i = 0; i < shape.size(); i++) area += cross(ImVec2(0, 0), shape[i], shape[(i + 1) % shape.size()]);
    return area;
}

Shape clip(const Shape &shape, ImVec2 point, ImVec2 outward) {
    Shape result;
    size_t count = shape.size();
    for (size_t i = 0; i < count; i++) {
        ImVec2 a = shape[i], b = shape[(i + 1) % count];
        float da = (a.x - point.x) * outward.x + (a.y - point.y) * outward.y;
        float db = (b.x - point.x) * outward.x + (b.y - point.y) * outward.y;
        if (da <= 0) result.push_back(a);
        if ((da <= 0) != (db <= 0)) result.push_back(a + (b - a) * (da / (da - db)));
    }
    return result;
}

Shape clip_convex(Shape shape, const Shape &window) {
    float orientation = signed_area(window) > 0 ? 1.0f : -1.0f;
    for (size_t i = 0; i < window.size() && !shape.empty(); i++) {
        ImVec2 a = window[i], b = window[(i + 1) % window.size()];
        ImVec2 edge = b - a;
        shape = clip(shape, a, ImVec2(edge.y, -edge.x) * orientation);
    }
    return shape;
}

Shape rounded(const Shape &shape, float radius) {
    float orientation = signed_area(shape) > 0 ? 1.0f : -1.0f;
    Shape inner = shape;
    for (size_t i = 0; i < shape.size() && !inner.empty(); i++) {
        ImVec2 a = shape[i], b = shape[(i + 1) % shape.size()];
        ImVec2 edge = b - a;
        float length = sqrtf(edge.x * edge.x + edge.y * edge.y);
        if (length < 1e-4f) continue;
        ImVec2 outward = ImVec2(edge.y, -edge.x) * (orientation / length);
        inner = clip(inner, a - outward * radius, outward);
    }
    if (inner.size() < 3) return shape;
    Shape result;
    size_t count = inner.size();
    for (size_t i = 0; i < count; i++) {
        ImVec2 before = inner[(i + count - 1) % count], at = inner[i], after = inner[(i + 1) % count];
        ImVec2 e0 = at - before, e1 = after - at;
        float from = atan2f(-e0.x * orientation, e0.y * orientation);
        float to = atan2f(-e1.x * orientation, e1.y * orientation);
        if (orientation > 0) { while (to < from) to += 2 * IM_PI; }
        else { while (to > from) to -= 2 * IM_PI; }
        int steps = std::max(1, (int)(fabsf(to - from) / 0.12f));
        for (int step = 0; step <= steps; step++) {
            float angle = from + (to - from) * step / steps;
            result.push_back(at + ImVec2(cosf(angle), sinf(angle)) * radius);
        }
    }
    return result;
}

Shape reference_circle(ImVec2 centre, float radius, int segments) {
    Shape shape;
    for (int i = 0; i < segments; i++) {
        float angle = 2 * IM_PI * i / segments;
        shape.push_back(centre + ImVec2(cosf(angle), sinf(angle)) * radius);
    }
    return shape;
}

float ease_flat(float x, float flat_x) {
    return flat_x + ARROW_SOFTNESS * logf(expf((x - flat_x) / ARROW_SOFTNESS) + 1.0f);
}

Shape arrow_region(bool up, float grow) {
    Shape shape = reference_circle(ARROW_CENTRE, ARROW_R + grow, 180);
    float near_y = up ? ARROW_GAP_Y - ARROW_HALF_GAP + grow : ARROW_GAP_Y + ARROW_HALF_GAP - grow;
    shape = clip(shape, ImVec2(0, near_y), ImVec2(0, up ? 1.0f : -1.0f));
    Shape edge = reference_circle(ImVec2(ARROW_EDGE_X + grow - ARROW_EDGE_R, ARROW_GAP_Y), ARROW_EDGE_R, 720);
    shape = clip_convex(shape, edge);
    for (ImVec2 &point : shape) point.x = ease_flat(point.x, ARROW_CENTRE.x + ARROW_KEY_FLAT);
    return shape;
}

Shape arrow_well() {
    float radius = ARROW_R + ARROW_WELL_MARGIN + 1.0f;
    float edge_x = ARROW_EDGE_X + ARROW_WELL_MARGIN + ARROW_WELL_TUCK + 10.0f;
    Shape shape;
    for (int i = 0; i <= 90; i++) {
        float angle = IM_PI * 0.5f + IM_PI * i / 90;
        ImVec2 point = ARROW_CENTRE + ImVec2(cosf(angle), sinf(angle)) * radius;
        point.x = ease_flat(point.x, ARROW_CENTRE.x + ARROW_WELL_FLAT);
        shape.push_back(point);
    }
    shape.push_back(ImVec2(edge_x, ARROW_CENTRE.y - radius));
    shape.push_back(ImVec2(edge_x, ARROW_CENTRE.y + radius));
    return rounded(shape, ARROW_WELL_CORNER);
}


Shape to_screen(const Frame &frame, const Shape &reference, bool right) {
    Shape shape;
    for (const ImVec2 &point : reference) shape.push_back(frame.at(point.x, point.y, right));
    return shape;
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


void fill(ImDrawList *draw, const Shape &shape, ImU32 top, ImU32 bottom) {
    ImRect box = bounds(shape);
    int start = draw->VtxBuffer.Size;
    draw->AddConvexPolyFilled(shape.data(), (int)shape.size(), top);
    ImGui::ShadeVertsLinearColorGradientKeepAlpha(draw, start, draw->VtxBuffer.Size, ImVec2(0, box.Min.y),
                                                  ImVec2(0, box.Max.y), top, bottom);
}



struct Span {
    float top;
    float bottom;
    bool valid;
};

Span convex_span(const Shape &shape, float x) {
    Span span = { FLT_MAX, -FLT_MAX, false };
    size_t count = shape.size();
    for (size_t i = 0; i < count; i++) {
        ImVec2 a = shape[i], b = shape[(i + 1) % count];
        if ((a.x <= x && b.x >= x) || (b.x <= x && a.x >= x)) {
            float y = fabsf(b.x - a.x) < 1e-5f ? a.y : a.y + (b.y - a.y) * (x - a.x) / (b.x - a.x);
            span.top = std::min(span.top, y);
            span.bottom = std::max(span.bottom, y);
            span.valid = true;
        }
    }
    return span;
}

ImU32 faded(ImU32 colour, float alpha) {
    int a = (int)(((colour >> IM_COL32_A_SHIFT) & 0xff) * std::max(0.0f, std::min(1.0f, alpha)));
    return (colour & ~IM_COL32_A_MASK) | ((ImU32)a << IM_COL32_A_SHIFT);
}

float smoothstep(float t) {
    t = std::max(0.0f, std::min(1.0f, t));
    return t * t * (3 - 2 * t);
}

struct RecessStyle {
    float outer;
    float inner;
    float flatness;
};

struct Mask {
    float from = 0;
    float to = 0;

    float at(float x) const {
        return from != to ? smoothstep((x - from) / (to - from)) : 1.0f;
    }
};

const RecessStyle FLUTE_RECESS = { 1.4f, 7.0f, 0.15f };
const RecessStyle KEY_WELL = { 1.1f, 5.5f, 0.3f };
const RecessStyle FLAT_WELL = { 0.9f, 4.5f, 1.0f };

const ImU32 WALL_SHADE = IM_COL32(104, 112, 118, 255);
const ImU32 WALL_LIT = IM_COL32(238, 242, 246, 255);
const ImU32 BOWL_TOP = IM_COL32(146, 154, 160, 255);
const ImU32 BOWL_BOTTOM = IM_COL32(188, 195, 199, 255);
const ImU32 FLOOR = IM_COL32(178, 186, 191, 255);

ImU32 mix(ImU32 a, ImU32 b, float t) {
    t = std::max(0.0f, std::min(1.0f, t));
    auto channel = [&](int shift) { return (int)(((a >> shift) & 0xff) * (1 - t) + ((b >> shift) & 0xff) * t); };
    return IM_COL32(channel(IM_COL32_R_SHIFT), channel(IM_COL32_G_SHIFT), channel(IM_COL32_B_SHIFT), channel(IM_COL32_A_SHIFT));
}

void draw_recess(ImDrawList *draw, const Shape &shape, const RecessStyle &style, float u, Mask mask = Mask()) {
    const int inner_rings = 6;
    size_t count = shape.size();
    ImRect box = bounds(shape);
    float outward = bounds(grown(shape, 1.0f)).GetWidth() > box.GetWidth() ? -1.0f : 1.0f;
    std::vector<ImVec2> normals(count);
    std::vector<float> facing(count);
    for (size_t i = 0; i < count; i++) {
        ImVec2 tangent = shape[(i + 1) % count] - shape[(i + count - 1) % count];
        float length = sqrtf(tangent.x * tangent.x + tangent.y * tangent.y);
        normals[i] = length > 0 ? ImVec2(tangent.y, -tangent.x) * (outward / length) : ImVec2(0, 0);
        facing[i] = smoothstep((normals[i].y + 1.0f) * 0.5f);
    }
    auto floor_colour = [&](ImVec2 point) {
        float t = box.GetHeight() > 0 ? (point.y - box.Min.y) / box.GetHeight() : 0.5f;
        return mix(mix(BOWL_TOP, BOWL_BOTTOM, t), FLOOR, style.flatness);
    };
    auto shaded = [&](ImU32 colour, ImVec2 point) { return faded(colour, mask.at(point.x)); };

    const int rings = inner_rings + 2;
    float inner = style.inner * u;
    draw->PrimReserve((int)count * (rings - 1) * 6 + ((int)count - 2) * 3, (int)count * rings + (int)count);
    ImDrawIdx base = (ImDrawIdx)draw->_VtxCurrentIdx;
    ImVec2 uv = draw->_Data->TexUvWhitePixel;
    for (size_t i = 0; i < count; i++) {
        ImU32 wall = mix(WALL_SHADE, WALL_LIT, facing[i]);
        ImVec2 edge = shape[i];
        ImVec2 outer_point = edge + normals[i] * (style.outer * u);
        draw->PrimWriteVtx(outer_point, uv, shaded(wall, outer_point) & ~IM_COL32_A_MASK);
        draw->PrimWriteVtx(edge, uv, shaded(wall, edge));
        for (int ring = 1; ring <= inner_rings; ring++) {
            float t = (float)ring / inner_rings;
            ImVec2 point = edge - normals[i] * (inner * t);
            draw->PrimWriteVtx(point, uv, shaded(mix(wall, floor_colour(point), smoothstep(t)), point));
        }
    }
    for (size_t i = 0; i < count; i++) {
        ImDrawIdx a = (ImDrawIdx)(base + i * rings), b = (ImDrawIdx)(base + ((i + 1) % count) * rings);
        for (int ring = 0; ring < rings - 1; ring++) {
            draw->PrimWriteIdx((ImDrawIdx)(a + ring)); draw->PrimWriteIdx((ImDrawIdx)(b + ring)); draw->PrimWriteIdx((ImDrawIdx)(b + ring + 1));
            draw->PrimWriteIdx((ImDrawIdx)(a + ring)); draw->PrimWriteIdx((ImDrawIdx)(b + ring + 1)); draw->PrimWriteIdx((ImDrawIdx)(a + ring + 1));
        }
    }
    ImDrawIdx centre = (ImDrawIdx)draw->_VtxCurrentIdx;
    for (size_t i = 0; i < count; i++) {
        ImVec2 point = shape[i] - normals[i] * inner;
        draw->PrimWriteVtx(point, uv, shaded(floor_colour(point), point));
    }
    for (size_t i = 1; i + 1 < count; i++) {
        draw->PrimWriteIdx(centre); draw->PrimWriteIdx((ImDrawIdx)(centre + i)); draw->PrimWriteIdx((ImDrawIdx)(centre + i + 1));
    }
}

float bezel_brightness(float x, const ImVec2 &lcd_min, const ImVec2 &lcd_max, float u) {
    static const float left_profile[][2] = { { -202, 0.80f }, { -192, 0.98f }, { -182, 1.07f }, { -150, 1.03f }, { -60, 0.97f }, { 0, 0.94f } };
    static const float right_profile[][2] = { { 0, 0.94f }, { 60, 0.97f }, { 170, 1.03f }, { 196, 1.07f }, { 206, 0.98f }, { 214, 0.80f } };
    const float (*profile)[2];
    int count = 6;
    float at;
    if (x < lcd_min.x) {
        profile = left_profile;
        at = (x - lcd_min.x) / u;
    } else if (x > lcd_max.x) {
        profile = right_profile;
        at = (x - lcd_max.x) / u;
    } else {
        return 0.94f;
    }
    if (at <= profile[0][0]) return profile[0][1];
    for (int i = 1; i < count; i++) {
        if (at <= profile[i][0]) {
            float t = (at - profile[i - 1][0]) / (profile[i][0] - profile[i - 1][0]);
            return profile[i - 1][1] + (profile[i][1] - profile[i - 1][1]) * t;
        }
    }
    return profile[count - 1][1];
}

void shade_body(ImDrawList *draw, ImVec2 device_min, ImVec2 device_max, float rounding, const ImVec2 &lcd_min,
                const ImVec2 &lcd_max, float u) {
    Shape body;
    add_arc(body, ImVec2(device_max.x - rounding, device_min.y + rounding), rounding, IM_PI * 1.5f, IM_PI * 2.0f, 16);
    add_arc(body, ImVec2(device_max.x - rounding, device_max.y - rounding), rounding, 0, IM_PI * 0.5f, 16);
    add_arc(body, ImVec2(device_min.x + rounding, device_max.y - rounding), rounding, IM_PI * 0.5f, IM_PI, 16);
    add_arc(body, ImVec2(device_min.x + rounding, device_min.y + rounding), rounding, IM_PI, IM_PI * 1.5f, 16);
    int columns = std::max(16, (int)((device_max.x - device_min.x) / 3));
    draw->PrimReserve(columns * 12, (columns + 1) * 3);
    ImDrawIdx base = (ImDrawIdx)draw->_VtxCurrentIdx;
    ImVec2 uv = draw->_Data->TexUvWhitePixel;
    int r = (BEZEL >> IM_COL32_R_SHIFT) & 0xff, g = (BEZEL >> IM_COL32_G_SHIFT) & 0xff, b = (BEZEL >> IM_COL32_B_SHIFT) & 0xff;
    for (int column = 0; column <= columns; column++) {
        float x = device_min.x + (device_max.x - device_min.x) * column / columns;
        Span span = convex_span(body, std::max(device_min.x + 0.01f, std::min(device_max.x - 0.01f, x)));
        float k = bezel_brightness(x, lcd_min, lcd_max, u);
        int cr = std::min(255, (int)(r * k)), cg = std::min(255, (int)(g * k)), cb = std::min(255, (int)(b * k));
        const float sheen = 0.16f;
        ImU32 top = IM_COL32(cr + (int)((255 - cr) * sheen), cg + (int)((255 - cg) * sheen), cb + (int)((255 - cb) * sheen), 255);
        ImU32 colour = IM_COL32(cr, cg, cb, 255);
        float middle = span.top + (device_max.y - device_min.y) * 0.45f;
        draw->PrimWriteVtx(ImVec2(x, span.top), uv, top);
        draw->PrimWriteVtx(ImVec2(x, std::min(middle, span.bottom)), uv, colour);
        draw->PrimWriteVtx(ImVec2(x, span.bottom), uv, colour);
    }
    for (int column = 0; column < columns; column++) {
        for (int row = 0; row < 2; row++) {
            ImDrawIdx i = (ImDrawIdx)(base + column * 3 + row);
            draw->PrimWriteIdx(i); draw->PrimWriteIdx((ImDrawIdx)(i + 3)); draw->PrimWriteIdx((ImDrawIdx)(i + 4));
            draw->PrimWriteIdx(i); draw->PrimWriteIdx((ImDrawIdx)(i + 4)); draw->PrimWriteIdx((ImDrawIdx)(i + 1));
        }
    }
}

ImU32 lighten(ImU32 colour, int amount) {
    int r = std::min(255, (int)((colour >> IM_COL32_R_SHIFT) & 0xff) + amount);
    int g = std::min(255, (int)((colour >> IM_COL32_G_SHIFT) & 0xff) + amount);
    int b = std::min(255, (int)((colour >> IM_COL32_B_SHIFT) & 0xff) + amount);
    return IM_COL32(r, g, b, 255);
}

Shape inset(const Shape &shape, float distance) {
    Shape result = grown(shape, distance);
    if (bounds(result).GetWidth() > bounds(shape).GetWidth()) result = grown(shape, -distance);
    return result;
}

Shape outset(const Shape &shape, float distance) {
    Shape result = grown(shape, distance);
    if (bounds(result).GetWidth() < bounds(shape).GetWidth()) result = grown(shape, -distance);
    return result;
}


void draw_key(ImDrawList *draw, const Shape &shape, const ButtonStyle &style, bool pressed, float u) {
    const int layers = 4;
    for (int layer = layers; layer >= 1; layer--) {
        int alpha = (int)(((pressed ? 10 : 18) + (layers - layer) * 4) * style.shadow);
        fill(draw, translated(shape, ImVec2(0, layer * 0.8f * u)), IM_COL32(20, 26, 32, alpha), IM_COL32(20, 26, 32, alpha));
    }
    if (style.gap > 0) fill(draw, outset(shape, style.gap * u), IM_COL32(16, 20, 24, 215), IM_COL32(16, 20, 24, 170));
    Shape body = translated(shape, ImVec2(0, pressed ? 1.2f * u : 0));
    ImU32 face_top = pressed ? style.bottom : style.top;
    fill(draw, body, lighten(face_top, pressed ? style.rim / 3 : style.rim), lighten(style.bottom, 16));
    fill(draw, inset(body, 1.3f * u), face_top, style.bottom);
    if (style.dome > 0) {
        ImRect box = bounds(body);
        float depth = std::min(box.GetWidth(), box.GetHeight()) * 0.5f;
        ImVec2 offset = ImVec2(-0.08f, -0.14f) * depth;
        const int rings = 14;
        for (int ring = 0; ring < rings; ring++) {
            float t = (float)ring / rings;
            Shape layer = translated(inset(body, depth * (0.2f + 0.75f * t)), offset * t);
            fill(draw, layer, IM_COL32(255, 255, 255, (int)(4 * style.dome)), IM_COL32(255, 255, 255, (int)(2 * style.dome)));
        }
    }
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
    Shape power = pill(frame.at(fit_power[0] - fit_power[2], fit_power[1] - fit_power[3], true),
                       frame.at(fit_power[0] + fit_power[2], fit_power[1] + fit_power[3], true));
    ImRect power_box = bounds(power);
    Shape up_key = to_screen(frame, rounded(arrow_region(true, 0), ARROW_CORNER), true);
    Shape down_key = to_screen(frame, rounded(arrow_region(false, 0), ARROW_CORNER), true);

    draw->PushClipRect(device_min, device_max, true);
    for (const char *name : side_names) {
        ImRect box = bounds(traced(frame, name));
        float reach = box.GetHeight() * FLUTE_REACH;
        Shape scoop = side_key(ImVec2(box.Min.x - reach, box.Min.y - FLUTE_MARGIN * u),
                               ImVec2(box.Max.x + FLUTE_MARGIN * u, box.Max.y + FLUTE_MARGIN * u),
                               (SIDE_KEY_CORNER + FLUTE_MARGIN) * u);
        draw_recess(draw, scoop, FLUTE_RECESS, u, Mask{ box.Min.x - reach, box.Min.x + box.GetHeight() * 0.2f });
    }
    {
        float reach = power_box.GetHeight() * FLUTE_REACH;
        Shape scoop = pill(power_box.Min - ImVec2(FLUTE_MARGIN, FLUTE_MARGIN) * u,
                           ImVec2(power_box.Max.x + reach, power_box.Max.y + FLUTE_MARGIN * u));
        draw_recess(draw, scoop, FLUTE_RECESS, u, Mask{ power_box.Max.x + reach, power_box.Max.x - power_box.GetHeight() * 0.2f });
    }
    {
        Shape well = to_screen(frame, arrow_well(), true);
        draw_recess(draw, well, KEY_WELL, u, Mask{ bounds(well).Max.x, frame.at(ARROW_EDGE_X - 4.0f, 0, true).x });
    }
    draw->PopClipRect();

    struct SideKey { const char *id; uint32_t code; const char *text; unsigned glyph; };
    const SideKey side[] = {
        { "key-main", HOST_KEY_F1, "MAIN", 0 }, { "key-tel", HOST_KEY_F1 + 1, nullptr, ICON_CALL },
        { "key-cal", HOST_KEY_F1 + 2, nullptr, ICON_CALENDAR }, { "key-memo", HOST_KEY_F1 + 3, nullptr, ICON_NOTE },
        { "key-prog", HOST_KEY_F1 + 4, nullptr, 0 },
    };
    for (int index = 0; index < 5; index++) {
        ImRect box = bounds(traced(frame, side_names[index]));
        Shape shape = side_key(box.Min, box.Max, SIDE_KEY_CORNER * u);
        bool pressed;
        if (hit(side[index].id, shape, pressed) && live) keys_push(side[index].code, 0);
        draw_key(draw, shape, DARK_KEY, pressed, u);
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
        ImRect box = bounds(traced(frame, "light"));
        Shape shape = pill(box.Min, box.Max);
        draw_recess(draw, pill(box.Min - ImVec2(WELL_MARGIN, WELL_MARGIN) * u, box.Max + ImVec2(WELL_MARGIN, WELL_MARGIN) * u), KEY_WELL, u);
        bool pressed;
        if (hit("key-light", shape, pressed)) lcd_set_backlight(!lcd_get_backlight());
        draw_key(draw, shape, TEAL_KEY, pressed, u);
        icon(draw, box.GetCenter() + dip(pressed), 34.0f * u, LABEL, ICON_LIGHT);
    }

    {
        centred_text(draw, menu_centre - ImVec2(0, 39 * u), 15.0f * u, PRINT, "MENU");
        draw_recess(draw, circle(menu_centre, (fit_menu[2] + WELL_MARGIN + 2.5f) * u), KEY_WELL, u);
        Shape shape = circle(menu_centre, fit_menu[2] * u);
        bool pressed;
        if (hit("key-menu", shape, pressed) && live) keys_push(HOST_KEY_TAB, 0);
        draw_key(draw, shape, DARK_DOMED_KEY, pressed, u);
    }

    {
        centred_text(draw, ImVec2(power_box.GetCenter().x, menu_centre.y - 39 * u), 15.0f * u, PRINT, "POWER");
        bool pressed;
        if (hit("key-power", power, pressed)) {
            state.powered = !state.powered;
            lcd_set_power(state.powered);
        }
        draw_key(draw, power, TEAL_KEY, pressed, u);
        icon(draw, power_box.GetCenter() + dip(pressed), 32.0f * u, LABEL, ICON_POWER);
    }

    struct ArrowKey { const char *id; const char *shape; uint32_t code; unsigned glyph; };
    const ArrowKey arrows[] = { { "key-up", "up", HOST_KEY_UP, ICON_UP }, { "key-down", "down", HOST_KEY_DOWN, ICON_DOWN } };
    for (int index = 0; index < 2; index++) {
        const Shape &shape = index == 0 ? up_key : down_key;
        bool pressed;
        bool activated = hit(arrows[index].id, shape, pressed);
        repeat_key(repeats[index], arrows[index].code, activated && live, pressed && live);
        draw_key(draw, shape, BLUE_KEY, pressed, u);
        ImRect box = bounds(shape);
        ImVec2 centre = ImVec2(box.GetCenter().x + 3.0f * u, box.GetCenter().y + (index == 0 ? 4.0f : -4.0f) * u) + dip(pressed);
        float dy = index == 0 ? 1.0f : -1.0f;
        ImVec2 chevron[3] = { centre + ImVec2(-19.0f * u, 8.0f * u * dy), centre + ImVec2(0, -8.0f * u * dy),
                              centre + ImVec2(19.0f * u, 8.0f * u * dy) };
        draw->AddPolyline(chevron, 3, IM_COL32(222, 228, 234, 235), 0, 2.6f * u);
    }

    draw_recess(draw, capsule(esc_centre, (fit_esc[2] + 6) * u, enter_centre, (fit_enter[2] + 6) * u), FLAT_WELL, u);
    {
        Shape shape = circle(esc_centre, fit_esc[2] * u);
        bool pressed;
        if (hit("key-esc", shape, pressed) && live) keys_push(HOST_KEY_ESC, 0);
        draw_key(draw, shape, DARK_KEY, pressed, u);
        centred_text(draw, esc_centre + dip(pressed), 15.0f * u, LABEL, "ESC");
    }
    {
        Shape shape = circle(enter_centre, fit_enter[2] * u);
        bool pressed;
        if (hit("key-enter", shape, pressed) && live) keys_push(HOST_KEY_ENTER, 0);
        draw_key(draw, shape, DARK_KEY, pressed, u);
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
    if (state.show_keys) shade_body(draw, device_min, device_max, rounding, image_min, image_max, u);
    else draw->AddRectFilled(device_min, device_max, BEZEL, rounding);
    if (!state.show_keys) draw->AddRectFilledMultiColor(device_min + ImVec2(rounding, 2), ImVec2(device_max.x - rounding, device_min.y + device_size.y * 0.45f),
                                  IM_COL32(255, 255, 255, 40), IM_COL32(255, 255, 255, 40), IM_COL32(255, 255, 255, 0), IM_COL32(255, 255, 255, 0));
    draw->AddRect(device_min, device_max, BEZEL_EDGE, rounding, 0, 2.0f);
    draw->AddRect(device_min + ImVec2(2, 2), device_max - ImVec2(2, 2), BEZEL_LIGHT, rounding - 2, 0, 1.0f);

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
