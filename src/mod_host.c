#include <time.h>

#include "py/runtime.h"
#include "py/objstr.h"

#include "beeper.h"
#include "host.h"
#include "keys.h"
#include "lcd.h"
#include "runtime.h"

static mp_obj_t host_present(void) {
    runtime_service();
    host_yield_to_main();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(host_present_obj, host_present);

static mp_obj_t host_ticks(void) {
    return mp_obj_new_int_from_uint(host_ticks_ms());
}
static MP_DEFINE_CONST_FUN_OBJ_0(host_ticks_obj, host_ticks);

static int64_t clock_offset = 0;

static time_t device_time(void) {
    return time(NULL) + (time_t)clock_offset;
}

static mp_obj_t host_clock_offset(size_t n_args, const mp_obj_t *args) {
    if (n_args == 1) clock_offset = mp_obj_get_int(args[0]);
    return mp_obj_new_int((mp_int_t)clock_offset);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(host_clock_offset_obj, 0, 1, host_clock_offset);

static mp_obj_t host_contrast(size_t n_args, const mp_obj_t *args) {
    if (n_args == 1) lcd_set_contrast(mp_obj_get_int(args[0]));
    return MP_OBJ_NEW_SMALL_INT(lcd_get_contrast());
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(host_contrast_obj, 0, 1, host_contrast);

static mp_obj_t host_localtime(void) {
    time_t now = device_time();
    struct tm local;
    localtime_r(&now, &local);
    mp_obj_t fields[8] = {
        MP_OBJ_NEW_SMALL_INT(local.tm_year + 1900), MP_OBJ_NEW_SMALL_INT(local.tm_mon + 1),
        MP_OBJ_NEW_SMALL_INT(local.tm_mday),        MP_OBJ_NEW_SMALL_INT(local.tm_hour),
        MP_OBJ_NEW_SMALL_INT(local.tm_min),         MP_OBJ_NEW_SMALL_INT(local.tm_sec),
        MP_OBJ_NEW_SMALL_INT((local.tm_wday + 6) % 7), MP_OBJ_NEW_SMALL_INT(local.tm_yday + 1),
    };
    return mp_obj_new_tuple(8, fields);
}
static MP_DEFINE_CONST_FUN_OBJ_0(host_localtime_obj, host_localtime);

static mp_obj_t host_epoch(void) {
    return mp_obj_new_int((mp_int_t)device_time());
}
static MP_DEFINE_CONST_FUN_OBJ_0(host_epoch_obj, host_epoch);

static mp_obj_t host_utc_offset(void) {
    time_t now = device_time();
    struct tm local;
    localtime_r(&now, &local);
    return mp_obj_new_int((mp_int_t)local.tm_gmtoff);
}
static MP_DEFINE_CONST_FUN_OBJ_0(host_utc_offset_obj, host_utc_offset);

static mp_obj_t host_key(void) {
    host_key_t key;
    if (!keys_pop(&key)) return mp_const_none;
    mp_obj_t fields[2] = { MP_OBJ_NEW_SMALL_INT(key.code), MP_OBJ_NEW_SMALL_INT(key.mods) };
    return mp_obj_new_tuple(2, fields);
}
static MP_DEFINE_CONST_FUN_OBJ_0(host_key_obj, host_key);

static mp_obj_t host_held(mp_obj_t code_in) {
    return mp_obj_new_bool(keys_is_held((uint32_t)mp_obj_get_int(code_in)));
}
static MP_DEFINE_CONST_FUN_OBJ_1(host_held_obj, host_held);

static mp_obj_t host_resume(size_t n_args, const mp_obj_t *args) {
    if (n_args == 1) {
        runtime_set_resume(args[0] == mp_const_none ? "" : mp_obj_str_get_str(args[0]));
        return mp_const_none;
    }
    const char *name = runtime_get_resume();
    return name[0] ? mp_obj_new_str(name, strlen(name)) : mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(host_resume_obj, 0, 1, host_resume);

static mp_obj_t host_backlight(size_t n_args, const mp_obj_t *args) {
    if (n_args == 1) lcd_set_backlight(mp_obj_is_true(args[0]));
    return mp_obj_new_bool(lcd_get_backlight());
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(host_backlight_obj, 0, 1, host_backlight);

static mp_obj_t host_beep(size_t n_args, const mp_obj_t *args) {
    float frequency = mp_obj_get_float(args[0]);
    uint32_t duration = (uint32_t)mp_obj_get_int(args[1]);
    float second = n_args > 2 ? mp_obj_get_float(args[2]) : 0.0f;
    beeper_tone(frequency, second, duration);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(host_beep_obj, 2, 3, host_beep);

static mp_obj_t host_sound(size_t n_args, const mp_obj_t *args) {
    if (n_args == 1) beeper_set_sound(mp_obj_is_true(args[0]));
    return mp_obj_new_bool(beeper_sound());
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(host_sound_obj, 0, 1, host_sound);

static mp_obj_t host_key_click(size_t n_args, const mp_obj_t *args) {
    if (n_args == 1) beeper_set_key_click(mp_obj_is_true(args[0]));
    return mp_obj_new_bool(beeper_key_click());
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(host_key_click_obj, 0, 1, host_key_click);

static mp_obj_t host_beep_stop(void) {
    beeper_stop();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(host_beep_stop_obj, host_beep_stop);

static mp_obj_t host_beeping(void) {
    return mp_obj_new_bool(beeper_busy());
}
static MP_DEFINE_CONST_FUN_OBJ_0(host_beeping_obj, host_beeping);

void host_capture_start(void);
const char *host_capture_stop(size_t *len);

static mp_obj_t host_capture_start_fn(void) {
    host_capture_start();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(host_capture_start_obj, host_capture_start_fn);

static mp_obj_t host_capture_stop_fn(void) {
    size_t len;
    const char *text = host_capture_stop(&len);
    return mp_obj_new_str(text, len);
}
static MP_DEFINE_CONST_FUN_OBJ_0(host_capture_stop_obj, host_capture_stop_fn);

static mp_obj_t host_boots(void) {
    return MP_OBJ_NEW_SMALL_INT(runtime_boots());
}
static MP_DEFINE_CONST_FUN_OBJ_0(host_boots_obj, host_boots);

static mp_obj_t host_reload(void) {
    runtime_request_reload();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(host_reload_obj, host_reload);

static const mp_rom_map_elem_t host_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__),  MP_ROM_QSTR(MP_QSTR_host) },
    { MP_ROM_QSTR(MP_QSTR_present),   MP_ROM_PTR(&host_present_obj) },
    { MP_ROM_QSTR(MP_QSTR_ticks_ms),  MP_ROM_PTR(&host_ticks_obj) },
    { MP_ROM_QSTR(MP_QSTR_localtime), MP_ROM_PTR(&host_localtime_obj) },
    { MP_ROM_QSTR(MP_QSTR_epoch),     MP_ROM_PTR(&host_epoch_obj) },
    { MP_ROM_QSTR(MP_QSTR_clock_offset), MP_ROM_PTR(&host_clock_offset_obj) },
    { MP_ROM_QSTR(MP_QSTR_contrast),  MP_ROM_PTR(&host_contrast_obj) },
    { MP_ROM_QSTR(MP_QSTR_utc_offset), MP_ROM_PTR(&host_utc_offset_obj) },
    { MP_ROM_QSTR(MP_QSTR_key),       MP_ROM_PTR(&host_key_obj) },
    { MP_ROM_QSTR(MP_QSTR_held),      MP_ROM_PTR(&host_held_obj) },
    { MP_ROM_QSTR(MP_QSTR_resume),    MP_ROM_PTR(&host_resume_obj) },
    { MP_ROM_QSTR(MP_QSTR_backlight), MP_ROM_PTR(&host_backlight_obj) },
    { MP_ROM_QSTR(MP_QSTR_beep),      MP_ROM_PTR(&host_beep_obj) },
    { MP_ROM_QSTR(MP_QSTR_sound),     MP_ROM_PTR(&host_sound_obj) },
    { MP_ROM_QSTR(MP_QSTR_key_click), MP_ROM_PTR(&host_key_click_obj) },
    { MP_ROM_QSTR(MP_QSTR_beep_stop), MP_ROM_PTR(&host_beep_stop_obj) },
    { MP_ROM_QSTR(MP_QSTR_beeping),   MP_ROM_PTR(&host_beeping_obj) },
    { MP_ROM_QSTR(MP_QSTR_capture_start), MP_ROM_PTR(&host_capture_start_obj) },
    { MP_ROM_QSTR(MP_QSTR_capture_stop),  MP_ROM_PTR(&host_capture_stop_obj) },
    { MP_ROM_QSTR(MP_QSTR_boots),     MP_ROM_PTR(&host_boots_obj) },
    { MP_ROM_QSTR(MP_QSTR_reload),    MP_ROM_PTR(&host_reload_obj) },

    { MP_ROM_QSTR(MP_QSTR_KEY_BACKSPACE), MP_ROM_INT(HOST_KEY_BACKSPACE) },
    { MP_ROM_QSTR(MP_QSTR_KEY_TAB),       MP_ROM_INT(HOST_KEY_TAB) },
    { MP_ROM_QSTR(MP_QSTR_KEY_ENTER),     MP_ROM_INT(HOST_KEY_ENTER) },
    { MP_ROM_QSTR(MP_QSTR_KEY_ESC),       MP_ROM_INT(HOST_KEY_ESC) },
    { MP_ROM_QSTR(MP_QSTR_KEY_DELETE),    MP_ROM_INT(HOST_KEY_DELETE) },
    { MP_ROM_QSTR(MP_QSTR_KEY_UP),        MP_ROM_INT(HOST_KEY_UP) },
    { MP_ROM_QSTR(MP_QSTR_KEY_DOWN),      MP_ROM_INT(HOST_KEY_DOWN) },
    { MP_ROM_QSTR(MP_QSTR_KEY_LEFT),      MP_ROM_INT(HOST_KEY_LEFT) },
    { MP_ROM_QSTR(MP_QSTR_KEY_RIGHT),     MP_ROM_INT(HOST_KEY_RIGHT) },
    { MP_ROM_QSTR(MP_QSTR_KEY_HOME),      MP_ROM_INT(HOST_KEY_HOME) },
    { MP_ROM_QSTR(MP_QSTR_KEY_END),       MP_ROM_INT(HOST_KEY_END) },
    { MP_ROM_QSTR(MP_QSTR_KEY_PGUP),      MP_ROM_INT(HOST_KEY_PGUP) },
    { MP_ROM_QSTR(MP_QSTR_KEY_PGDN),      MP_ROM_INT(HOST_KEY_PGDN) },
    { MP_ROM_QSTR(MP_QSTR_KEY_F1),        MP_ROM_INT(HOST_KEY_F1) },
    { MP_ROM_QSTR(MP_QSTR_MOD_SHIFT),     MP_ROM_INT(HOST_MOD_SHIFT) },
    { MP_ROM_QSTR(MP_QSTR_MOD_CTRL),      MP_ROM_INT(HOST_MOD_CTRL) },
    { MP_ROM_QSTR(MP_QSTR_MOD_ALT),       MP_ROM_INT(HOST_MOD_ALT) },
    { MP_ROM_QSTR(MP_QSTR_MOD_CMD),       MP_ROM_INT(HOST_MOD_CMD) },
};
static MP_DEFINE_CONST_DICT(host_module_globals, host_module_globals_table);

const mp_obj_module_t host_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&host_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_host, host_module);
