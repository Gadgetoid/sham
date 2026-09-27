#include <SDL3/SDL.h>

#include <string>

#include "imgui.h"
#include "menu_layout.h"
#include "touch.h"

namespace {

const int MENU_QUEUE = 32;

int queue[MENU_QUEUE];
int queued = 0;
bool checked[MENU_COUNT];

void push(int item) {
    if (queued < MENU_QUEUE) queue[queued++] = item;
}

ImGuiKeyChord key_chord(const menu_entry_t &entry) {
    if (entry.key < 'a' || entry.key > 'z') return ImGuiKey_None;
    ImGuiKeyChord chord = (ImGuiKey)(ImGuiKey_A + (entry.key - 'a'));
    if (entry.modifiers & MENU_KEY_PRIMARY) chord |= ImGuiMod_Alt;
    if (entry.modifiers & MENU_KEY_SHIFT) chord |= ImGuiMod_Shift;
    if (entry.modifiers & MENU_KEY_CONTROL) chord |= ImGuiMod_Ctrl;
    return chord;
}

std::string shortcut_label(const menu_entry_t &entry) {
    if (!entry.key) return "";
    std::string label;
    if (entry.modifiers & MENU_KEY_CONTROL) label += "Ctrl+";
    if (entry.modifiers & MENU_KEY_PRIMARY) label += "Alt+";
    if (entry.modifiers & MENU_KEY_SHIFT) label += "Shift+";
    label += (char)(entry.key - 'a' + 'A');
    return label;
}

int skip_menu(int index) {
    for (int depth = 1; ++index < MENU_ENTRY_COUNT;) {
        menu_entry_kind_t kind = MENU_ENTRIES[index].kind;
        if (kind == MENU_ENTRY_MENU || kind == MENU_ENTRY_SUBMENU) depth++;
        if (kind == MENU_ENTRY_END && --depth == 0) break;
    }
    return index;
}

int draw_entries(int index) {
    for (; index < MENU_ENTRY_COUNT; index++) {
        const menu_entry_t &entry = MENU_ENTRIES[index];
        switch (entry.kind) {
            case MENU_ENTRY_END: return index;
            case MENU_ENTRY_SEPARATOR: ImGui::Separator(); break;
            case MENU_ENTRY_MENU:
            case MENU_ENTRY_SUBMENU:
                if (ImGui::BeginMenu(entry.title)) {
                    index = draw_entries(index + 1);
                    ImGui::EndMenu();
                } else {
                    index = skip_menu(index);
                }
                break;
            case MENU_ENTRY_ITEM:
                if (ImGui::MenuItem(entry.title, shortcut_label(entry).c_str(), checked[entry.tag])) push(entry.tag);
                break;
        }
    }
    return index;
}

}

void menu_install(void) {
}

void menu_ensure(void) {
}

void menu_draw(void) {
    for (int i = 0; i < MENU_ENTRY_COUNT; i++) {
        const menu_entry_t &entry = MENU_ENTRIES[i];
        if (entry.kind == MENU_ENTRY_ITEM && entry.key && ImGui::IsKeyChordPressed(key_chord(entry))) push(entry.tag);
    }
    bool open = ImGui::IsMouseClicked(ImGuiMouseButton_Right) || ImGui::IsKeyPressed(ImGuiKey_Menu, false);
    if (open && !ImGui::IsPopupOpen("menu")) ImGui::OpenPopup("menu");
    if (!ImGui::BeginPopup("menu")) return;
    draw_entries(0);
    ImGui::Separator();
    if (ImGui::MenuItem("Quit")) {
        SDL_Event quit = {};
        quit.type = SDL_EVENT_QUIT;
        SDL_PushEvent(&quit);
    }
    ImGui::EndPopup();
}

void menu_perform(int item) {
    if (item >= 0 && item < MENU_COUNT) push(item);
}

int menu_poll(void) {
    if (queued == 0) return -1;
    int item = queue[0];
    for (int i = 1; i < queued; i++) queue[i - 1] = queue[i];
    queued--;
    return item;
}

void menu_set_checked(int item, bool state) {
    if (item >= 0 && item < MENU_COUNT) checked[item] = state;
}

void window_set_transparent(void *nswindow, void *layer, bool transparent) {
    (void)nswindow;
    (void)layer;
    (void)transparent;
}

void window_set_aspect(void *nswindow, float width, float height) {
    (void)nswindow;
    (void)width;
    (void)height;
}
