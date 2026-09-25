#import <Cocoa/Cocoa.h>

#include "menu.h"

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
static NSMenuItem *holders[2];
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

void menu_install(void) {
    target = [[PocketMenuTarget alloc] init];

    NSMenu *run = add_menu(@"Run");
    add_item(run, MENU_RELOAD, @"Reload", @"r", NSEventModifierFlagCommand);
    add_item(run, MENU_INTERRUPT, @"Interrupt (Ctrl-C)", @"", 0);
    [run addItem:[NSMenuItem separatorItem]];
    add_item(run, MENU_SHOW_REPL, @"Show REPL", @"j", NSEventModifierFlagCommand);
    add_item(run, MENU_FOCUS_REPL, @"Focus REPL", @"l", NSEventModifierFlagCommand);

    NSMenu *system = add_menu(@"System");
    add_item(system, MENU_SHOW_KEYS, @"Show Keys", @"k", NSEventModifierFlagCommand);
    [system addItem:[NSMenuItem separatorItem]];
    add_item(system, MENU_BACKLIGHT, @"Backlight", @"b", NSEventModifierFlagCommand);
    add_item(system, MENU_DEAD_COLUMNS, @"Dead Columns", @"d", NSEventModifierFlagCommand);
    [system addItem:[NSMenuItem separatorItem]];
    add_item(system, MENU_SOUND, @"Sound", @"", 0);
    add_item(system, MENU_KEY_CLICK, @"Key Click", @"", 0);
    [system addItem:[NSMenuItem separatorItem]];
    add_item(system, MENU_PERIOD_RATE, @"Period Frame Rate (10 fps)", @"", 0);
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
