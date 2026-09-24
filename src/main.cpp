#include <SDL3/SDL.h>
#include <limits.h>
#include <sys/stat.h>
#include <unistd.h>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>
#include <utility>
#include <vector>

#define IMGUI_DEFINE_MATH_OPERATORS
#include "imgui.h"
#include "imgui_impl_sdl3.h"
#include "imgui_impl_sdlrenderer3.h"

#include "beeper.h"
#include "console.h"
#include "host.h"
#include "keys.h"
#include "lcd.h"
#include "runtime.h"
#include "watch.h"

static uint64_t start_ticks = 0;
static SDL_WindowID main_window_id = 0;

extern "C" uint32_t host_ticks_ms(void) {
    return (uint32_t)(SDL_GetTicks() - start_ticks);
}

struct Options {
    std::string root = "os";
    std::string data = "data";
    std::string main = "/main.py";
    std::string screenshot;
    std::string keys;
    std::vector<std::string> exec;
    int frames = 120;
    int width = 1040;
    int height = 820;
    bool watch = true;
};

static void usage() {
    printf(
        "usage: pocket [options]\n"
        "  --root=DIR          OS directory, mounted as / (default os)\n"
        "  --data=DIR          writable directory, mounted as /data (default data)\n"
        "  --main=PATH         entry point within root (default /main.py)\n"
        "  --size=WxH          window size (default 1040x820)\n"
        "  --no-watch          do not reload when files in root change\n"
        "  --keys=SEQUENCE     type into the device after boot, {DOWN} {ENTER} {F1}, {+LEFT} holds, {-LEFT} releases\n"
        "  --exec=CODE         run a line at the REPL after boot, repeatable\n"
        "  --screenshot=FILE   save the window as BMP after --frames and exit\n"
        "  --frames=N          frames before the screenshot (default 120)\n");
}

static std::string absolute(const std::string &path) {
    if (path.empty() || path[0] == '/') return path;
    char cwd[PATH_MAX];
    if (!getcwd(cwd, sizeof cwd)) return path;
    return std::string(cwd) + "/" + path;
}

static bool parse_options(int argc, char **argv, Options &options) {
    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        auto value = [&](const char *prefix) -> const char * {
            size_t len = strlen(prefix);
            return arg.compare(0, len, prefix) == 0 ? argv[i] + len : nullptr;
        };
        if (const char *v = value("--root=")) options.root = v;
        else if (const char *v = value("--data=")) options.data = v;
        else if (const char *v = value("--main=")) options.main = v;
        else if (const char *v = value("--screenshot=")) options.screenshot = v;
        else if (const char *v = value("--frames=")) options.frames = atoi(v);
        else if (const char *v = value("--keys=")) options.keys = v;
        else if (const char *v = value("--exec=")) options.exec.push_back(v);
        else if (const char *v = value("--size=")) sscanf(v, "%dx%d", &options.width, &options.height);
        else if (arg == "--no-watch") options.watch = false;
        else {
            usage();
            return false;
        }
    }
    return true;
}

static uint32_t special_key(SDL_Keycode key) {
    switch (key) {
        case SDLK_UP:        return HOST_KEY_UP;
        case SDLK_DOWN:      return HOST_KEY_DOWN;
        case SDLK_LEFT:      return HOST_KEY_LEFT;
        case SDLK_RIGHT:     return HOST_KEY_RIGHT;
        case SDLK_HOME:      return HOST_KEY_HOME;
        case SDLK_END:       return HOST_KEY_END;
        case SDLK_PAGEUP:    return HOST_KEY_PGUP;
        case SDLK_PAGEDOWN:  return HOST_KEY_PGDN;
        case SDLK_RETURN:
        case SDLK_KP_ENTER:  return HOST_KEY_ENTER;
        case SDLK_ESCAPE:    return HOST_KEY_ESC;
        case SDLK_BACKSPACE: return HOST_KEY_BACKSPACE;
        case SDLK_DELETE:    return HOST_KEY_DELETE;
        case SDLK_TAB:       return HOST_KEY_TAB;
        default: break;
    }
    if (key >= SDLK_F1 && key <= SDLK_F12) return HOST_KEY_F1 + (key - SDLK_F1);
    return 0;
}

static SDL_Keycode sdl_key(uint32_t code) {
    static const std::pair<uint32_t, SDL_Keycode> table[] = {
        { HOST_KEY_UP, SDLK_UP }, { HOST_KEY_DOWN, SDLK_DOWN }, { HOST_KEY_LEFT, SDLK_LEFT }, { HOST_KEY_RIGHT, SDLK_RIGHT },
        { HOST_KEY_HOME, SDLK_HOME }, { HOST_KEY_END, SDLK_END }, { HOST_KEY_PGUP, SDLK_PAGEUP },
        { HOST_KEY_PGDN, SDLK_PAGEDOWN }, { HOST_KEY_ENTER, SDLK_RETURN }, { HOST_KEY_ESC, SDLK_ESCAPE },
        { HOST_KEY_BACKSPACE, SDLK_BACKSPACE }, { HOST_KEY_DELETE, SDLK_DELETE }, { HOST_KEY_TAB, SDLK_TAB },
    };
    for (auto &entry : table) {
        if (entry.first == code) return entry.second;
    }
    if (code >= HOST_KEY_F1 && code < HOST_KEY_F1 + 12) return SDLK_F1 + (code - HOST_KEY_F1);
    return 0;
}

static void push_sdl_key(SDL_Keycode key, bool down) {
    SDL_Event event = {};
    event.type = down ? SDL_EVENT_KEY_DOWN : SDL_EVENT_KEY_UP;
    event.key.key = key;
    event.key.scancode = SDL_GetScancodeFromKey(key, nullptr);
    event.key.down = down;
    event.key.windowID = main_window_id;
    SDL_PushEvent(&event);
}

static void push_click(float x, float y) {
    SDL_Event event = {};
    event.type = SDL_EVENT_MOUSE_MOTION;
    event.motion.x = x;
    event.motion.y = y;
    event.motion.windowID = main_window_id;
    SDL_PushEvent(&event);
    event = {};
    event.type = SDL_EVENT_MOUSE_BUTTON_DOWN;
    event.button.button = SDL_BUTTON_LEFT;
    event.button.down = true;
    event.button.clicks = 1;
    event.button.x = x;
    event.button.y = y;
    event.button.windowID = main_window_id;
    SDL_PushEvent(&event);
    event.type = SDL_EVENT_MOUSE_BUTTON_UP;
    event.button.down = false;
    SDL_PushEvent(&event);
}

static uint32_t held_code(SDL_Keycode key) {
    if (uint32_t code = special_key(key)) return code;
    if (key >= SDLK_SPACE && key <= SDLK_Z) return (uint32_t)key;
    return 0;
}

static uint8_t modifiers(SDL_Keymod mod) {
    uint8_t mods = 0;
    if (mod & SDL_KMOD_SHIFT) mods |= HOST_MOD_SHIFT;
    if (mod & SDL_KMOD_CTRL)  mods |= HOST_MOD_CTRL;
    if (mod & SDL_KMOD_ALT)   mods |= HOST_MOD_ALT;
    if (mod & SDL_KMOD_GUI)   mods |= HOST_MOD_CMD;
    return mods;
}

static void push_text(const char *text) {
    const unsigned char *p = (const unsigned char *)text;
    while (*p) {
        uint32_t codepoint = *p++;
        int extra = codepoint >= 0xf0 ? 3 : codepoint >= 0xe0 ? 2 : codepoint >= 0xc0 ? 1 : 0;
        if (extra) codepoint &= 0x3f >> extra;
        while (extra-- > 0 && *p) codepoint = (codepoint << 6) | (*p++ & 0x3f);
        keys_push(codepoint, 0);
    }
}

enum KeyAction { PRESS, HOLD, RELEASE, CLICK };

struct KeyScript {
    struct Step {
        uint32_t code;
        KeyAction action;
    };
    std::vector<Step> steps;
    size_t next = 0;
    int start_frame = 60;
    int interval = 4;
    float click_x = 0;
    float click_y = 0;

    static uint32_t named(const std::string &name) {
        static const std::pair<const char *, uint32_t> names[] = {
            { "UP", HOST_KEY_UP }, { "DOWN", HOST_KEY_DOWN }, { "LEFT", HOST_KEY_LEFT }, { "RIGHT", HOST_KEY_RIGHT },
            { "ENTER", HOST_KEY_ENTER }, { "ESC", HOST_KEY_ESC }, { "BS", HOST_KEY_BACKSPACE },
            { "DEL", HOST_KEY_DELETE }, { "TAB", HOST_KEY_TAB }, { "HOME", HOST_KEY_HOME }, { "END", HOST_KEY_END },
            { "PGUP", HOST_KEY_PGUP }, { "PGDN", HOST_KEY_PGDN }, { "SPACE", ' ' },
        };
        if (name.size() > 1 && name[0] == 'F' && isdigit((unsigned char)name[1])) {
            return HOST_KEY_F1 + atoi(name.c_str() + 1) - 1;
        }
        for (auto &entry : names) {
            if (name == entry.first) return entry.second;
        }
        return name.size() == 1 ? (uint32_t)(unsigned char)name[0] : 0;
    }

    void parse(const std::string &script) {
        for (size_t i = 0; i < script.size(); i++) {
            if (script[i] != '{') {
                steps.push_back({ (uint8_t)script[i], PRESS });
                continue;
            }
            size_t close = script.find('}', i);
            if (close == std::string::npos) break;
            std::string name = script.substr(i + 1, close - i - 1);
            i = close;
            KeyAction action = PRESS;
            if (!name.empty() && (name[0] == '+' || name[0] == '-')) {
                action = name[0] == '+' ? HOLD : RELEASE;
                name = name.substr(1);
            }
            if (name == "CLICK") {
                steps.push_back({ 1, CLICK });
                continue;
            }
            steps.push_back({ name == "WAIT" ? 0 : named(name), action });
        }
    }

    void step(int frame) {
        if (next >= steps.size() || frame < start_frame || (frame - start_frame) % interval) return;
        Step current = steps[next++];
        if (!current.code) return;
        if (current.action == CLICK) {
            push_click(click_x, click_y);
            return;
        }
        SDL_Keycode key = sdl_key(current.code);
        if (key && current.action == PRESS) {
            push_sdl_key(key, true);
            push_sdl_key(key, false);
            return;
        }
        if (current.action == PRESS) keys_push(current.code, 0);
        else if (current.action == HOLD) { keys_set_held(current.code, true); keys_push(current.code, 0); }
        else keys_set_held(current.code, false);
    }
};

static SDL_Texture *lcd_texture = nullptr;

static void upload_lcd(SDL_Renderer *renderer) {
    int w = lcd_compose_width(), h = lcd_compose_height();
    bool recreated = false;
    if (!lcd_texture || lcd_texture->w != w || lcd_texture->h != h) {
        if (lcd_texture) SDL_DestroyTexture(lcd_texture);
        lcd_texture = SDL_CreateTexture(renderer, SDL_PIXELFORMAT_RGBA32, SDL_TEXTUREACCESS_STREAMING, w, h);
        SDL_SetTextureScaleMode(lcd_texture, SDL_SCALEMODE_NEAREST);
        recreated = true;
    }
    if (lcd_compose() || recreated) {
        SDL_UpdateTexture(lcd_texture, nullptr, lcd_compose_pixels(), w * 4);
    }
}

static void draw_device(SDL_Renderer *renderer, float framebuffer_scale, bool device_focused, float height) {
    const float grid_w = LCD_WIDTH + 2 * LCD_MARGIN;
    const float grid_h = LCD_HEIGHT + 2 * LCD_MARGIN;
    const float bezel = 30.0f;

    ImVec2 origin = ImGui::GetCursorScreenPos();
    float avail_w = ImGui::GetContentRegionAvail().x;
    float lcd_w = std::min(avail_w - 2 * bezel, (height - 2 * bezel) * grid_w / grid_h);
    int cell = std::max(2, (int)floorf(lcd_w * framebuffer_scale / grid_w));
    lcd_compose_setup(cell);
    upload_lcd(renderer);

    ImVec2 image_size(cell * grid_w / framebuffer_scale, cell * grid_h / framebuffer_scale);
    ImVec2 device_size = image_size + ImVec2(2 * bezel, 2 * bezel);
    ImVec2 device_min = origin + ImVec2((avail_w - device_size.x) * 0.5f, (height - device_size.y) * 0.5f);
    ImVec2 device_max = device_min + device_size;
    ImVec2 image_min = device_min + ImVec2(bezel, bezel);
    ImVec2 image_max = image_min + image_size;

    ImDrawList *draw = ImGui::GetWindowDrawList();
    if (device_focused) {
        draw->AddRect(device_min - ImVec2(3, 3), device_max + ImVec2(3, 3), IM_COL32(90, 200, 180, 160), 22.0f, 0, 2.0f);
    }
    draw->AddRectFilled(device_min, device_max, IM_COL32(178, 184, 188, 255), 18.0f);
    draw->AddRect(device_min, device_max, IM_COL32(110, 116, 120, 255), 18.0f, 0, 2.0f);
    draw->AddRectFilled(image_min - ImVec2(5, 5), image_max + ImVec2(5, 5), IM_COL32(58, 64, 68, 255), 5.0f);
    draw->AddRect(image_min - ImVec2(5, 5), image_max + ImVec2(5, 5), IM_COL32(210, 216, 220, 255), 5.0f, 0, 1.0f);
    if (lcd_texture) draw->AddImage((ImTextureID)(intptr_t)lcd_texture, image_min, image_max);
    draw->AddText(device_min + ImVec2(bezel, 8), IM_COL32(60, 66, 72, 255), "POCKET  PZ-239");

    ImGui::SetCursorScreenPos(origin);
    ImGui::InvisibleButton("device", ImVec2(avail_w, height));
}

static void save_screenshot(SDL_Renderer *renderer, const std::string &path) {
    SDL_Surface *surface = SDL_RenderReadPixels(renderer, nullptr);
    if (!surface) {
        SDL_Log("screenshot failed: %s", SDL_GetError());
        return;
    }
    if (SDL_SaveBMP(surface, path.c_str())) SDL_Log("screenshot: %s", path.c_str());
    else SDL_Log("screenshot failed: %s", SDL_GetError());
    SDL_DestroySurface(surface);
}

int main(int argc, char **argv) {
    Options options;
    if (!parse_options(argc, argv, options)) return 1;

    options.root = absolute(options.root);
    options.data = absolute(options.data);
    options.screenshot = absolute(options.screenshot);
    mkdir(options.data.c_str(), 0755);
    setvbuf(stdout, nullptr, _IONBF, 0);

    if (!SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO)) {
        SDL_Log("SDL_Init failed: %s", SDL_GetError());
        return 1;
    }
    start_ticks = SDL_GetTicks();

    SDL_Window *window = SDL_CreateWindow("Pocket", options.width, options.height,
                                          SDL_WINDOW_RESIZABLE | SDL_WINDOW_HIGH_PIXEL_DENSITY);
    SDL_Renderer *renderer = window ? SDL_CreateRenderer(window, nullptr) : nullptr;
    if (!renderer) {
        SDL_Log("window/renderer failed: %s", SDL_GetError());
        return 1;
    }
    SDL_SetRenderVSync(renderer, 1);
    main_window_id = SDL_GetWindowID(window);
    beeper_init();

    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGuiIO &io = ImGui::GetIO();
    io.IniFilename = nullptr;
    ImGui::StyleColorsDark();
    ImGuiStyle &style = ImGui::GetStyle();
    style.FontSizeBase = 14.0f;
    style.Colors[ImGuiCol_WindowBg] = ImVec4(0.10f, 0.11f, 0.12f, 1.0f);
    ImGui_ImplSDL3_InitForSDLRenderer(window, renderer);
    ImGui_ImplSDLRenderer3_Init(renderer);

    host_config_t config = { options.root.c_str(), options.data.c_str(), options.main.c_str() };
    if (!runtime_init(&config)) return 1;
    if (options.watch) watch_start(options.root.c_str());

    for (auto &line : options.exec) console_submit(line.c_str());
    KeyScript script;
    script.parse(options.keys);

    bool running = true;
    bool device_focused = true;
    int frame = 0;

    while (running) {
        SDL_Event event;
        while (SDL_PollEvent(&event)) {
            bool device_tab = device_focused && (event.type == SDL_EVENT_KEY_DOWN || event.type == SDL_EVENT_KEY_UP) &&
                              event.key.key == SDLK_TAB;
            if (!device_tab) ImGui_ImplSDL3_ProcessEvent(&event);
            if (event.type == SDL_EVENT_QUIT) running = false;
            if (event.type == SDL_EVENT_KEY_DOWN) {
                SDL_Keycode key = event.key.key;
                SDL_Keymod mod = event.key.mod;
                if ((mod & SDL_KMOD_GUI) && key == SDLK_R) { runtime_request_reload(); continue; }
                if ((mod & SDL_KMOD_GUI) && key == SDLK_L) { console_focus(); continue; }
                if ((mod & SDL_KMOD_GUI) && key == SDLK_B) { lcd_set_backlight(!lcd_get_backlight()); continue; }
                if ((mod & SDL_KMOD_CTRL) && key == SDLK_C) {
                    if (device_focused || runtime_repl_busy()) runtime_interrupt();
                    else console_cancel();
                    continue;
                }
                if (!device_focused || (mod & SDL_KMOD_GUI)) continue;
                if (uint32_t code = held_code(key)) keys_set_held(code, true);
                if (uint32_t code = special_key(key)) {
                    keys_push(code, modifiers(mod));
                } else if ((mod & SDL_KMOD_CTRL) && key >= SDLK_A && key <= SDLK_Z) {
                    keys_push('a' + (key - SDLK_A), modifiers(mod));
                }
            }
            if (event.type == SDL_EVENT_KEY_UP) {
                if (uint32_t code = held_code(event.key.key)) keys_set_held(code, false);
            }
            if (event.type == SDL_EVENT_WINDOW_FOCUS_LOST) keys_release_all();
            if (event.type == SDL_EVENT_TEXT_INPUT && device_focused) {
                if (!(SDL_GetModState() & (SDL_KMOD_CTRL | SDL_KMOD_GUI))) push_text(event.text.text);
            }
        }

        if (options.watch && watch_poll()) {
            console_notice("change detected");
            runtime_request_reload();
        }
        script.click_x = io.DisplaySize.x * 0.5f;
        script.click_y = io.DisplaySize.y * 0.25f;
        script.step(frame);
        runtime_step();

        ImGui_ImplSDLRenderer3_NewFrame();
        ImGui_ImplSDL3_NewFrame();
        ImGui::NewFrame();

        ImGui::SetNextWindowPos(ImVec2(0, 0));
        ImGui::SetNextWindowSize(io.DisplaySize);
        ImGui::Begin("root", nullptr, ImGuiWindowFlags_NoDecoration | ImGuiWindowFlags_NoMove |
                                      ImGuiWindowFlags_NoSavedSettings | ImGuiWindowFlags_NoBringToFrontOnFocus);

        float total_height = ImGui::GetContentRegionAvail().y;
        draw_device(renderer, io.DisplayFramebufferScale.x, device_focused, std::max(220.0f, total_height * 0.52f));

        if (ImGui::Button("Reload")) runtime_request_reload();
        ImGui::SameLine();
        if (ImGui::Button("Interrupt")) runtime_interrupt();
        ImGui::SameLine();
        bool backlight = lcd_get_backlight();
        if (ImGui::Checkbox("Backlight", &backlight)) lcd_set_backlight(backlight);
        ImGui::SameLine();
        ImGui::TextDisabled("%s", device_focused ? "keys -> device  (Cmd-L: REPL)" : "keys -> REPL  (Esc: device)");
        ImGui::SameLine(ImGui::GetContentRegionMax().x - 150);
        ImGui::TextDisabled("%s  %.0f fps", runtime_idle() ? "idle" : "running", io.Framerate);
        ImGui::Separator();
        console_draw();
        ImGui::End();

        ImGui::Render();
        if (device_focused && io.WantTextInput) keys_release_all();
        device_focused = !io.WantTextInput;
        if (device_focused && !SDL_TextInputActive(window)) SDL_StartTextInput(window);

        SDL_SetRenderScale(renderer, io.DisplayFramebufferScale.x, io.DisplayFramebufferScale.y);
        SDL_SetRenderDrawColor(renderer, 26, 28, 31, 255);
        SDL_RenderClear(renderer);
        ImGui_ImplSDLRenderer3_RenderDrawData(ImGui::GetDrawData(), renderer);

        frame++;
        if (!options.screenshot.empty() && frame >= options.frames) {
            save_screenshot(renderer, options.screenshot);
            running = false;
        }
        SDL_RenderPresent(renderer);
    }

    watch_stop();
    runtime_deinit();
    beeper_deinit();
    ImGui_ImplSDLRenderer3_Shutdown();
    ImGui_ImplSDL3_Shutdown();
    ImGui::DestroyContext();
    if (lcd_texture) SDL_DestroyTexture(lcd_texture);
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}
