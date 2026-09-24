#include <stddef.h>
#include <stdint.h>
#include <port/mpconfigport_common.h>

#define MICROPY_CONFIG_ROM_LEVEL        (MICROPY_CONFIG_ROM_LEVEL_EXTRA_FEATURES)

#define MICROPY_ENABLE_COMPILER         (1)
#define MICROPY_ENABLE_GC               (1)
#define MICROPY_PY_GC                   (1)
#define MICROPY_PY_SYS                  (1)
#define MICROPY_PY_SYS_PLATFORM         "pocket"
#define MICROPY_PY_TIME                 (0)
#define MICROPY_FLOAT_IMPL              (MICROPY_FLOAT_IMPL_DOUBLE)
#define MICROPY_ERROR_REPORTING         (MICROPY_ERROR_REPORTING_NORMAL)
#define MICROPY_ENABLE_SOURCE_LINE      (1)
#define MICROPY_ENABLE_EXTERNAL_IMPORT  (1)
#define MICROPY_HELPER_REPL             (1)
#define MICROPY_PY_IO                   (1)
#define MICROPY_VFS                     (1)
#define MICROPY_VFS_POSIX               (1)
#define MICROPY_READER_VFS              (1)
#define MICROPY_ENABLE_FINALISER        (1)
#define MICROPY_PY_OS                   (1)

uint32_t host_random_seed(void);
#define MICROPY_PY_RANDOM               (1)
#define MICROPY_PY_RANDOM_SEED_INIT_FUNC (host_random_seed())
#define MICROPY_PY_UCTYPES              (0)
#define MICROPY_PY_BUILTINS_INPUT       (0)
#define MICROPY_PY_SYS_STDFILES         (0)

#define MICROPY_KBD_EXCEPTION           (1)
#define MICROPY_ENABLE_SCHEDULER        (1)
#define MICROPY_ENABLE_VM_ABORT         (1)
void mp_hal_set_interrupt_char(int c);
extern void host_vm_hook(void);
#define MICROPY_VM_HOOK_COUNT (256)
#define MICROPY_VM_HOOK_INIT  static uint32_t vm_hook_divisor = MICROPY_VM_HOOK_COUNT;
#define MICROPY_VM_HOOK_POLL  if (--vm_hook_divisor == 0) { \
                                  vm_hook_divisor = MICROPY_VM_HOOK_COUNT; \
                                  host_vm_hook(); \
                              }
#define MICROPY_VM_HOOK_LOOP  MICROPY_VM_HOOK_POLL
#define MICROPY_VM_HOOK_RETURN MICROPY_VM_HOOK_POLL
#define MP_HAL_RETRY_SYSCALL(ret, syscall, raise) { \
        for (;;) { \
            ret = syscall; \
            if (ret == -1) { \
                int err = errno; \
                if (err == EINTR) { \
                    mp_handle_pending(MP_HANDLE_PENDING_CALLBACKS_AND_EXCEPTIONS); \
                    continue; \
                } \
                raise; \
            } \
            break; \
        } \
}

#define RAISE_ERRNO(err_flag, error_val) \
    { if (err_flag == -1) { mp_raise_OSError(error_val); } }
