#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MINICORO_IMPL
#include "minicoro.h"

#include "py/runtime.h"
#include "py/compile.h"
#include "py/lexer.h"
#include "py/gc.h"
#include "py/stackctrl.h"
#include "port/micropython_embed.h"
#include "extmod/vfs.h"
#include "extmod/vfs_posix.h"

#include "beeper.h"
#include "console.h"
#include "keys.h"
#include "lcd.h"
#include "runtime.h"

#define GC_HEAP_SIZE      (8 * 1024 * 1024)
#define FIBER_STACK_SIZE  (1024 * 1024)
#define PREEMPT_MS        20
#define ABORT_GRACE_STEPS 30

#ifdef __APPLE__
#define RELOAD_SHORTCUT "Cmd-R"
#else
#define RELOAD_SHORTCUT "Alt-R"
#endif

static mco_coro *fiber = NULL;
static char *gc_heap = NULL;
static const host_config_t *config = NULL;
static char root_abs[PATH_MAX];
static char data_abs[PATH_MAX];
static char resume_name[64];
static bool reload_requested = false;
static bool running_repl = false;
static bool idle = false;
static int abort_steps = 0;
static uint32_t resumed_at = 0;
static int boots = 0;

void host_yield_to_main(void) {
    mco_yield(mco_running());
}

void host_vm_hook(void) {
    if (host_ticks_ms() - resumed_at >= PREEMPT_MS) {
        host_yield_to_main();
    }
}

const char *runtime_get_resume(void) { return resume_name; }

void runtime_set_resume(const char *name) {
    snprintf(resume_name, sizeof resume_name, "%s", name ? name : "");
}

bool runtime_idle(void) { return idle; }

bool runtime_repl_busy(void) { return running_repl; }

int runtime_boots(void) { return boots; }

static mp_vfs_mount_t *new_mount(const char *point, const char *dir) {
    mp_obj_t args[] = { mp_obj_new_str(dir, strlen(dir)) };
    mp_obj_t vfs = mp_call_function_n_kw(MP_OBJ_FROM_PTR(&mp_type_vfs_posix), 1, 0, args);
    mp_vfs_mount_t *mount = m_new_obj(mp_vfs_mount_t);
    mount->str = point;
    mount->len = strlen(point);
    mount->obj = vfs;
    mount->next = NULL;
    return mount;
}

static void mount_filesystems(void) {
    mp_vfs_mount_t *data = new_mount("/data", data_abs);
    data->next = new_mount("/", root_abs);
    MP_STATE_VM(vfs_mount_table) = data;
    MP_STATE_VM(vfs_cur) = data->next;
    mp_vfs_chdir(mp_obj_new_str("/", 1));
    mp_obj_list_append(mp_sys_path, MP_OBJ_NEW_QSTR(MP_QSTR__slash_));
    mp_obj_list_append(mp_sys_path, mp_obj_new_str("/lib", 4));
}

static void exec_main(const char *path) {
    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0) {
        mp_lexer_t *lex = mp_lexer_new_from_file(qstr_from_str(path));
        qstr source_name = lex->source_name;
        mp_parse_tree_t parse_tree = mp_parse(lex, MP_PARSE_FILE_INPUT);
        mp_obj_t module_fun = mp_compile(&parse_tree, source_name, false);
        mp_call_function_0(module_fun);
        nlr_pop();
    } else {
        mp_obj_print_exception(&mp_plat_print, MP_OBJ_FROM_PTR(nlr.ret_val));
    }
}

static void exec_repl(const char *source) {
    mp_obj_dict_t *saved_globals = mp_globals_get();
    mp_obj_dict_t *saved_locals = mp_locals_get();
    mp_globals_set(&MP_STATE_VM(dict_main));
    mp_locals_set(&MP_STATE_VM(dict_main));

    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0) {
        mp_lexer_t *lex = mp_lexer_new_from_str_len(MP_QSTR__lt_stdin_gt_, source, strlen(source), 0);
        qstr source_name = lex->source_name;
        mp_parse_tree_t parse_tree = mp_parse(lex, MP_PARSE_SINGLE_INPUT);
        mp_obj_t module_fun = mp_compile(&parse_tree, source_name, true);
        mp_call_function_0(module_fun);
        nlr_pop();
    } else {
        mp_obj_print_exception(&mp_plat_print, MP_OBJ_FROM_PTR(nlr.ret_val));
    }

    mp_globals_set(saved_globals);
    mp_locals_set(saved_locals);
}

void runtime_service(void) {
    if (running_repl) return;
    char *source;
    while ((source = console_take_input()) != NULL) {
        running_repl = true;
        exec_repl(source);
        running_repl = false;
        free(source);
    }
}

static void fiber_entry(mco_coro *co) {
    (void)co;
    int stack_marker;
    mp_embed_init(gc_heap, GC_HEAP_SIZE, &stack_marker);
    mp_stack_set_limit(FIBER_STACK_SIZE - 64 * 1024);

    nlr_buf_t abort_point;
    nlr_set_abort(&abort_point);
    if (nlr_push(&abort_point) == 0) {
        mount_filesystems();
        exec_main(config->main_path);
        idle = true;
        console_notice("main exited; REPL still live. Save a file or " RELOAD_SHORTCUT " to restart.");
        while (!reload_requested) {
            runtime_service();
            host_yield_to_main();
        }
        nlr_pop();
    } else if (abort_point.ret_val != NULL) {
        mp_obj_print_exception(&mp_plat_print, MP_OBJ_FROM_PTR(abort_point.ret_val));
    }
    nlr_set_abort(NULL);
    mp_embed_deinit();
}

static bool start_fiber(void) {
    boots++;
    reload_requested = false;
    running_repl = false;
    idle = false;
    abort_steps = 0;
    keys_clear();
    beeper_stop();
    lcd_reset_clip();
    lcd_clear(0);
    mco_desc desc = mco_desc_init(fiber_entry, FIBER_STACK_SIZE);
    return mco_create(&fiber, &desc) == MCO_SUCCESS;
}

bool runtime_init(const host_config_t *cfg) {
    config = cfg;
    if (!realpath(cfg->root_path, root_abs)) {
        fprintf(stderr, "sham: cannot resolve root %s\n", cfg->root_path);
        return false;
    }
    if (!realpath(cfg->data_path, data_abs)) {
        fprintf(stderr, "sham: cannot resolve data %s\n", cfg->data_path);
        return false;
    }
    gc_heap = malloc(GC_HEAP_SIZE);
    if (!gc_heap) return false;
    return start_fiber();
}

void runtime_request_reload(void) {
    if (reload_requested) return;
    reload_requested = true;
    if (fiber && mco_status(fiber) != MCO_DEAD) {
        mp_sched_vm_abort();
    }
}

void runtime_interrupt(void) {
    if (fiber && mco_status(fiber) != MCO_DEAD) {
        mp_sched_keyboard_interrupt();
    }
}

void runtime_step(void) {
    if (!fiber) return;
    if (mco_status(fiber) == MCO_DEAD || (reload_requested && ++abort_steps > ABORT_GRACE_STEPS)) {
        mco_destroy(fiber);
        fiber = NULL;
        if (reload_requested) {
            console_notice("reloading");
            start_fiber();
        }
        return;
    }
    resumed_at = host_ticks_ms();
    mco_resume(fiber);
}

void runtime_deinit(void) {
    if (fiber) {
        mco_destroy(fiber);
        fiber = NULL;
    }
    free(gc_heap);
    gc_heap = NULL;
}
