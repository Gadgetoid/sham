#import <Cocoa/Cocoa.h>

#include "menu_layout.h"
#include "touch.h"

#define MENU_QUEUE 32

static int queue[MENU_QUEUE];
static int queued = 0;
static NSMenuItem *items[MENU_COUNT];

@interface PocketMenuTarget : NSObject
@end

@implementation PocketMenuTarget
- (void)fire:(NSMenuItem *)item {
    if (queued < MENU_QUEUE) queue[queued++] = (int)item.tag;
}
@end

static PocketMenuTarget *target = nil;
static NSMenuItem *holders[5];
static int holder_count = 0;

static void add_item(NSMenu *menu, int tag, NSString *title, NSString *key, NSEventModifierFlags modifiers) {
    NSMenuItem *item = [[NSMenuItem alloc] initWithTitle:title action:@selector(fire:) keyEquivalent:key];
    item.keyEquivalentModifierMask = modifiers;
    item.target = target;
    item.tag = tag;
    [menu addItem:item];
    items[tag] = item;
}

static NSMenu *add_menu(NSString *title) {
    NSMenu *menu = [[NSMenu alloc] initWithTitle:title];
    NSMenuItem *holder = [[NSMenuItem alloc] initWithTitle:title action:nil keyEquivalent:@""];
    holder.submenu = menu;
    holders[holder_count++] = holder;
    return menu;
}

static void attach_menus(void) {
    NSMenu *bar = [NSApp mainMenu];
    if (!bar) {
        bar = [[NSMenu alloc] init];
        [NSApp setMainMenu:bar];
    }
    for (int i = 0; i < holder_count; i++) {
        if (holders[i].menu == bar) continue;
        if (holders[i].menu) [holders[i].menu removeItem:holders[i]];
        NSInteger window_menu = [bar indexOfItemWithTitle:@"Window"];
        NSInteger position = window_menu >= 0 ? window_menu : bar.numberOfItems;
        [bar insertItem:holders[i] atIndex:position];
    }
}


static NSMenu *submenu(NSMenu *parent, NSString *title) {
    NSMenu *menu = [[NSMenu alloc] initWithTitle:title];
    NSMenuItem *holder = [[NSMenuItem alloc] initWithTitle:title action:nil keyEquivalent:@""];
    holder.submenu = menu;
    [parent addItem:holder];
    return menu;
}

static NSEventModifierFlags cocoa_modifiers(int modifiers) {
    NSEventModifierFlags flags = 0;
    if (modifiers & MENU_KEY_PRIMARY) flags |= NSEventModifierFlagCommand;
    if (modifiers & MENU_KEY_SHIFT) flags |= NSEventModifierFlagShift;
    if (modifiers & MENU_KEY_CONTROL) flags |= NSEventModifierFlagControl;
    return flags;
}

void menu_install(void) {
    target = [[PocketMenuTarget alloc] init];
    NSMenu *stack[4];
    int depth = 0;
    for (int i = 0; i < MENU_ENTRY_COUNT; i++) {
        const menu_entry_t *entry = &MENU_ENTRIES[i];
        NSString *title = entry->title ? [NSString stringWithUTF8String:entry->title] : nil;
        NSMenu *menu = depth ? stack[depth - 1] : nil;
        switch (entry->kind) {
            case MENU_ENTRY_MENU: stack[depth++] = add_menu(title); break;
            case MENU_ENTRY_SUBMENU: stack[depth++] = submenu(menu, title); break;
            case MENU_ENTRY_END: depth--; break;
            case MENU_ENTRY_SEPARATOR: [menu addItem:[NSMenuItem separatorItem]]; break;
            case MENU_ENTRY_ITEM: {
                NSString *key = entry->key ? [NSString stringWithFormat:@"%c", entry->key] : @"";
                add_item(menu, entry->tag, title, key, cocoa_modifiers(entry->modifiers));
                break;
            }
        }
    }
    attach_menus();
}

void menu_draw(void) {
}

void menu_ensure(void) {
    if (holder_count) attach_menus();
}

void menu_perform(int item) {
    if (item < 0 || item >= MENU_COUNT || !items[item]) return;
    NSMenu *menu = items[item].menu;
    [menu performActionForItemAtIndex:[menu indexOfItem:items[item]]];
}

int menu_poll(void) {
    if (queued == 0) return -1;
    int item = queue[0];
    for (int i = 1; i < queued; i++) queue[i - 1] = queue[i];
    queued--;
    return item;
}

void menu_set_checked(int item, bool checked) {
    if (item < 0 || item >= MENU_COUNT || !items[item]) return;
    NSControlStateValue state = checked ? NSControlStateValueOn : NSControlStateValueOff;
    if (items[item].state != state) items[item].state = state;
}

void window_set_transparent(void *handle, void *layer_handle, bool transparent) {
    NSWindow *window = (__bridge NSWindow *)handle;
    CALayer *layer = (__bridge CALayer *)layer_handle;
    if (!window) return;
    window.opaque = !transparent;
    window.backgroundColor = transparent ? NSColor.clearColor : NSColor.windowBackgroundColor;
    window.hasShadow = !transparent;
    layer.opaque = !transparent;
}

void window_set_aspect(void *handle, float width, float height) {
    NSWindow *window = (__bridge NSWindow *)handle;
    if (!window) return;
    if (width > 0 && height > 0) window.contentAspectRatio = NSMakeSize(width, height);
    else window.contentResizeIncrements = NSMakeSize(1, 1);
}

#ifdef SHAM_TOUCHSCREEN
bool window_cover_display(void *handle, bool cover) {
    NSWindow *window = (__bridge NSWindow *)handle;
    if (!window) return false;
    if (cover) {
        window.level = NSMainMenuWindowLevel + 1;
        window.collectionBehavior = NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorStationary |
                                    NSWindowCollectionBehaviorFullScreenNone;
    } else {
        window.level = NSNormalWindowLevel;
        window.collectionBehavior = NSWindowCollectionBehaviorDefault;
    }
    return true;
}
#endif
