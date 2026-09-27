#import <Cocoa/Cocoa.h>

#include "menu.h"
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

void menu_install(void) {
    target = [[PocketMenuTarget alloc] init];

    NSMenu *run = add_menu(@"Run");
    add_item(run, MENU_RELOAD, @"Reload", @"r", NSEventModifierFlagCommand);
    add_item(run, MENU_INTERRUPT, @"Interrupt (Ctrl-C)", @"", 0);

    NSMenu *install = add_menu(@"Install");
    add_item(install, MENU_INSTALL_PY, @"Install Program…", @"i", NSEventModifierFlagCommand);

    NSMenu *view = add_menu(@"View");
    NSString *layouts[] = { @"Screen Only", @"Screen & Frame", @"Screen & Buttons", @"Screen & Keyboard" };
    for (int i = 0; i < MENU_LAYOUT_END - MENU_LAYOUT_FIRST; i++) add_item(view, MENU_LAYOUT_FIRST + i, layouts[i], @"", 0);
    add_item(view, MENU_LAYOUT_NEXT, @"Next Layout", @"k", NSEventModifierFlagCommand);
    [view addItem:[NSMenuItem separatorItem]];
    add_item(view, MENU_BORDERLESS, @"Borderless", @"b", NSEventModifierFlagCommand | NSEventModifierFlagShift);
    add_item(view, MENU_COMPACT, @"Compact", @"", 0);
    add_item(view, MENU_TOUCHSCREEN, @"Touchscreen Mode", @"t", NSEventModifierFlagCommand | NSEventModifierFlagShift);
    [view addItem:[NSMenuItem separatorItem]];
    add_item(view, MENU_SHOW_REPL, @"Show REPL", @"j", NSEventModifierFlagCommand);
    add_item(view, MENU_FOCUS_REPL, @"Focus REPL", @"l", NSEventModifierFlagCommand);
    [view addItem:[NSMenuItem separatorItem]];
    NSMenu *realism = submenu(view, @"Realism");
    add_item(realism, MENU_DEAD_COLUMNS, @"Dead Columns", @"d", NSEventModifierFlagCommand);
    add_item(realism, MENU_SCRATCHES, @"Scratches", @"", 0);
    add_item(realism, MENU_WEAR, @"Wear", @"", 0);

    NSMenu *simulation = add_menu(@"Simulation");
    add_item(simulation, MENU_BACKLIGHT, @"Backlight", @"b", NSEventModifierFlagCommand);
    add_item(simulation, MENU_SOUND, @"Sound", @"", 0);
    add_item(simulation, MENU_KEY_CLICK, @"Key Click", @"", 0);
    [simulation addItem:[NSMenuItem separatorItem]];
    NSMenu *rate = submenu(simulation, @"Frame Rate");
    NSString *rates[] = { @"Unlimited", @"60 fps", @"30 fps", @"20 fps", @"15 fps", @"10 fps" };
    for (int i = 0; i < MENU_FPS_END - MENU_FPS_FIRST; i++) add_item(rate, MENU_FPS_FIRST + i, rates[i], @"", 0);
    NSMenu *response = submenu(simulation, @"Response Time");
    NSString *responses[] = { @"Instant", @"Fast", @"Normal", @"Slow", @"Very Slow" };
    for (int i = 0; i < MENU_RESPONSE_END - MENU_RESPONSE_FIRST; i++) add_item(response, MENU_RESPONSE_FIRST + i, responses[i], @"", 0);
    attach_menus();
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
