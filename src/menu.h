#pragma once
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

enum {
    MENU_RELOAD,
    MENU_INTERRUPT,
    MENU_SHOW_REPL,
    MENU_FOCUS_REPL,
    MENU_BACKLIGHT,
    MENU_DEAD_COLUMNS,
    MENU_PERIOD_RATE,
    MENU_COUNT,
};

void menu_install(void);
void menu_ensure(void);
void menu_perform(int item);
int  menu_poll(void);
void menu_set_checked(int item, bool checked);

#ifdef __cplusplus
}
#endif
