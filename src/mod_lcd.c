#include <string.h>

#include "py/runtime.h"
#include "py/objstr.h"
#include "py/objarray.h"

#include "lcd.h"

typedef struct {
    mp_obj_base_t base;
    lcd_font_t font;
    int ink_top;
    int ink_bottom;
    char name[33];
} lcd_font_obj_t;

static uint16_t read_u16(const uint8_t *p) { return (uint16_t)(p[0] << 8 | p[1]); }
static uint32_t read_u32(const uint8_t *p) { return (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 | (uint32_t)p[2] << 8 | p[3]; }

#define PPF_HEADER_SIZE 46
#define PPF_GLYPH_SIZE  6

static mp_obj_t font_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 1, 1, false);
    mp_buffer_info_t source;
    mp_get_buffer_raise(args[0], &source, MP_BUFFER_READ);
    const uint8_t *bytes = source.buf;

    if (source.len < PPF_HEADER_SIZE || memcmp(bytes, "ppf!", 4) != 0) {
        mp_raise_ValueError(MP_ERROR_TEXT("not a ppf font"));
    }
    uint32_t count = read_u32(bytes + 6);
    uint16_t cell_width = read_u16(bytes + 10);
    uint16_t height = read_u16(bytes + 12);
    uint16_t bytes_per_row = (cell_width + 7) / 8;
    size_t data_offset = PPF_HEADER_SIZE + (size_t)count * PPF_GLYPH_SIZE;
    size_t data_size = (size_t)count * bytes_per_row * height;
    if (source.len < data_offset + data_size) {
        mp_raise_ValueError(MP_ERROR_TEXT("truncated ppf font"));
    }

    lcd_font_obj_t *self = mp_obj_malloc(lcd_font_obj_t, type);
    lcd_glyph_t *glyphs = m_new(lcd_glyph_t, count);
    for (uint32_t i = 0; i < count; i++) {
        const uint8_t *entry = bytes + PPF_HEADER_SIZE + i * PPF_GLYPH_SIZE;
        glyphs[i].codepoint = read_u32(entry);
        glyphs[i].width = read_u16(entry + 4);
        if (i > 0 && glyphs[i].codepoint <= glyphs[i - 1].codepoint) {
            mp_raise_ValueError(MP_ERROR_TEXT("ppf glyphs not sorted"));
        }
    }
    uint8_t *data = m_new(uint8_t, data_size);
    memcpy(data, bytes + data_offset, data_size);

    self->font = (lcd_font_t){
        .cell_width = cell_width,
        .height = height,
        .count = count,
        .bytes_per_row = bytes_per_row,
        .glyphs = glyphs,
        .data = data,
    };
    self->ink_top = height;
    self->ink_bottom = -1;
    bool has_ascii = false;
    for (uint32_t i = 0; i < count; i++) has_ascii |= glyphs[i].codepoint >= 0x21 && glyphs[i].codepoint <= 0x7e;
    for (size_t row_index = 0; row_index < (size_t)count * height; row_index++) {
        uint32_t codepoint = glyphs[row_index / height].codepoint;
        if (has_ascii && (codepoint < 0x21 || codepoint > 0x7e)) continue;
        const uint8_t *row = data + row_index * bytes_per_row;
        bool inked = false;
        for (int i = 0; i < bytes_per_row; i++) inked |= row[i] != 0;
        if (!inked) continue;
        int row_in_glyph = row_index % height;
        if (row_in_glyph < self->ink_top) self->ink_top = row_in_glyph;
        if (row_in_glyph > self->ink_bottom) self->ink_bottom = row_in_glyph;
    }
    if (self->ink_bottom < 0) {
        self->ink_top = 0;
        self->ink_bottom = height - 1;
    }
    memcpy(self->name, bytes + 14, 32);
    self->name[32] = '\0';
    return MP_OBJ_FROM_PTR(self);
}

static void font_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    if (dest[0] != MP_OBJ_NULL) return;
    lcd_font_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (attr == MP_QSTR_height) dest[0] = MP_OBJ_NEW_SMALL_INT(self->font.height);
    else if (attr == MP_QSTR_cell_width) dest[0] = MP_OBJ_NEW_SMALL_INT(self->font.cell_width);
    else if (attr == MP_QSTR_ink_top) dest[0] = MP_OBJ_NEW_SMALL_INT(self->ink_top);
    else if (attr == MP_QSTR_ink_bottom) dest[0] = MP_OBJ_NEW_SMALL_INT(self->ink_bottom);
    else if (attr == MP_QSTR_name) dest[0] = mp_obj_new_str(self->name, strlen(self->name));
}

static MP_DEFINE_CONST_OBJ_TYPE(
    lcd_font_type,
    MP_QSTR_Font,
    MP_TYPE_FLAG_NONE,
    make_new, font_make_new,
    attr, font_attr
);

static const lcd_font_t *get_font(mp_obj_t font_in) {
    if (!mp_obj_is_type(font_in, &lcd_font_type)) {
        mp_raise_TypeError(MP_ERROR_TEXT("expected lcd.Font"));
    }
    return &((lcd_font_obj_t *)MP_OBJ_TO_PTR(font_in))->font;
}

static uint8_t level_arg(size_t n_args, const mp_obj_t *args, size_t index, uint8_t fallback) {
    return n_args > index ? (uint8_t)mp_obj_get_int(args[index]) : fallback;
}

static mp_obj_t lcd_clear_fn(size_t n_args, const mp_obj_t *args) {
    lcd_clear(level_arg(n_args, args, 0, 0));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_clear_obj, 0, 1, lcd_clear_fn);

static mp_obj_t lcd_pixel_fn(size_t n_args, const mp_obj_t *args) {
    int x = mp_obj_get_int(args[0]), y = mp_obj_get_int(args[1]);
    if (n_args == 2) return MP_OBJ_NEW_SMALL_INT(lcd_get_pixel(x, y));
    lcd_pixel(x, y, (uint8_t)mp_obj_get_int(args[2]));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_pixel_obj, 2, 3, lcd_pixel_fn);

static mp_obj_t lcd_fill_fn(size_t n_args, const mp_obj_t *args) {
    lcd_fill(mp_obj_get_int(args[0]), mp_obj_get_int(args[1]), mp_obj_get_int(args[2]), mp_obj_get_int(args[3]),
             level_arg(n_args, args, 4, 3));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_fill_obj, 4, 5, lcd_fill_fn);

static mp_obj_t lcd_rect_fn(size_t n_args, const mp_obj_t *args) {
    lcd_rect(mp_obj_get_int(args[0]), mp_obj_get_int(args[1]), mp_obj_get_int(args[2]), mp_obj_get_int(args[3]),
             level_arg(n_args, args, 4, 3));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_rect_obj, 4, 5, lcd_rect_fn);

static mp_obj_t lcd_hline_fn(size_t n_args, const mp_obj_t *args) {
    lcd_fill(mp_obj_get_int(args[0]), mp_obj_get_int(args[1]), mp_obj_get_int(args[2]), 1, level_arg(n_args, args, 3, 3));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_hline_obj, 3, 4, lcd_hline_fn);

static mp_obj_t lcd_vline_fn(size_t n_args, const mp_obj_t *args) {
    lcd_fill(mp_obj_get_int(args[0]), mp_obj_get_int(args[1]), 1, mp_obj_get_int(args[2]), level_arg(n_args, args, 3, 3));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_vline_obj, 3, 4, lcd_vline_fn);

static mp_obj_t lcd_line_fn(size_t n_args, const mp_obj_t *args) {
    lcd_line(mp_obj_get_int(args[0]), mp_obj_get_int(args[1]), mp_obj_get_int(args[2]), mp_obj_get_int(args[3]),
             level_arg(n_args, args, 4, 3));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_line_obj, 4, 5, lcd_line_fn);

static mp_obj_t lcd_invert_fn(size_t n_args, const mp_obj_t *args) {
    (void)n_args;
    lcd_invert(mp_obj_get_int(args[0]), mp_obj_get_int(args[1]), mp_obj_get_int(args[2]), mp_obj_get_int(args[3]));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_invert_obj, 4, 4, lcd_invert_fn);

static mp_obj_t lcd_text_fn(size_t n_args, const mp_obj_t *args) {
    const lcd_font_t *font = get_font(args[0]);
    size_t len;
    const char *text = mp_obj_str_get_data(args[1], &len);
    int scale = n_args > 5 ? mp_obj_get_int(args[5]) : 1;
    int width = lcd_text(font, text, len, mp_obj_get_int(args[2]), mp_obj_get_int(args[3]),
                         level_arg(n_args, args, 4, 3), scale < 1 ? 1 : scale);
    return MP_OBJ_NEW_SMALL_INT(width);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_text_obj, 4, 6, lcd_text_fn);

static mp_obj_t lcd_measure_fn(size_t n_args, const mp_obj_t *args) {
    const lcd_font_t *font = get_font(args[0]);
    size_t len;
    const char *text = mp_obj_str_get_data(args[1], &len);
    int scale = n_args > 2 ? mp_obj_get_int(args[2]) : 1;
    return MP_OBJ_NEW_SMALL_INT(lcd_measure(font, text, len, scale < 1 ? 1 : scale));
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_measure_obj, 2, 3, lcd_measure_fn);

static mp_obj_t lcd_clip_fn(size_t n_args, const mp_obj_t *args) {
    int x, y, w, h;
    lcd_get_clip(&x, &y, &w, &h);
    mp_obj_t previous[4] = { MP_OBJ_NEW_SMALL_INT(x), MP_OBJ_NEW_SMALL_INT(y), MP_OBJ_NEW_SMALL_INT(w), MP_OBJ_NEW_SMALL_INT(h) };
    if (n_args == 0) {
        lcd_reset_clip();
    } else if (n_args == 1) {
        mp_obj_t *rect;
        mp_obj_get_array_fixed_n(args[0], 4, &rect);
        lcd_set_clip(mp_obj_get_int(rect[0]), mp_obj_get_int(rect[1]), mp_obj_get_int(rect[2]), mp_obj_get_int(rect[3]));
    } else {
        lcd_set_clip(mp_obj_get_int(args[0]), mp_obj_get_int(args[1]), mp_obj_get_int(args[2]), mp_obj_get_int(args[3]));
    }
    return mp_obj_new_tuple(4, previous);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_clip_obj, 0, 4, lcd_clip_fn);

static mp_obj_t lcd_grab_fn(size_t n_args, const mp_obj_t *args) {
    (void)n_args;
    int x = mp_obj_get_int(args[0]), y = mp_obj_get_int(args[1]);
    int w = mp_obj_get_int(args[2]), h = mp_obj_get_int(args[3]);
    if (w < 0 || h < 0) mp_raise_ValueError(MP_ERROR_TEXT("negative size"));
    byte *pixels = m_new(byte, (size_t)w * h);
    for (int row = 0; row < h; row++) {
        for (int col = 0; col < w; col++) {
            pixels[row * w + col] = (byte)lcd_get_pixel(x + col, y + row);
        }
    }
    return mp_obj_new_bytearray_by_ref((size_t)w * h, pixels);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_grab_obj, 4, 4, lcd_grab_fn);

static mp_obj_t lcd_blit_fn(size_t n_args, const mp_obj_t *args) {
    (void)n_args;
    mp_buffer_info_t source;
    mp_get_buffer_raise(args[0], &source, MP_BUFFER_READ);
    int x = mp_obj_get_int(args[1]), y = mp_obj_get_int(args[2]);
    int w = mp_obj_get_int(args[3]), h = mp_obj_get_int(args[4]);
    if (w < 0 || h < 0 || source.len < (size_t)w * h) mp_raise_ValueError(MP_ERROR_TEXT("buffer too small"));
    const byte *pixels = source.buf;
    for (int row = 0; row < h; row++) {
        for (int col = 0; col < w; col++) {
            lcd_pixel(x + col, y + row, pixels[row * w + col]);
        }
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lcd_blit_obj, 5, 5, lcd_blit_fn);

static mp_obj_t lcd_buffer_fn(void) {
    return mp_obj_new_bytearray_by_ref(sizeof lcd_framebuffer, lcd_framebuffer);
}
static MP_DEFINE_CONST_FUN_OBJ_0(lcd_buffer_obj, lcd_buffer_fn);

static const mp_rom_map_elem_t lcd_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_lcd) },
    { MP_ROM_QSTR(MP_QSTR_Font),     MP_ROM_PTR(&lcd_font_type) },
    { MP_ROM_QSTR(MP_QSTR_clear),    MP_ROM_PTR(&lcd_clear_obj) },
    { MP_ROM_QSTR(MP_QSTR_pixel),    MP_ROM_PTR(&lcd_pixel_obj) },
    { MP_ROM_QSTR(MP_QSTR_fill),     MP_ROM_PTR(&lcd_fill_obj) },
    { MP_ROM_QSTR(MP_QSTR_rect),     MP_ROM_PTR(&lcd_rect_obj) },
    { MP_ROM_QSTR(MP_QSTR_hline),    MP_ROM_PTR(&lcd_hline_obj) },
    { MP_ROM_QSTR(MP_QSTR_vline),    MP_ROM_PTR(&lcd_vline_obj) },
    { MP_ROM_QSTR(MP_QSTR_line),     MP_ROM_PTR(&lcd_line_obj) },
    { MP_ROM_QSTR(MP_QSTR_invert),   MP_ROM_PTR(&lcd_invert_obj) },
    { MP_ROM_QSTR(MP_QSTR_text),     MP_ROM_PTR(&lcd_text_obj) },
    { MP_ROM_QSTR(MP_QSTR_measure),  MP_ROM_PTR(&lcd_measure_obj) },
    { MP_ROM_QSTR(MP_QSTR_clip),     MP_ROM_PTR(&lcd_clip_obj) },
    { MP_ROM_QSTR(MP_QSTR_grab),     MP_ROM_PTR(&lcd_grab_obj) },
    { MP_ROM_QSTR(MP_QSTR_blit),     MP_ROM_PTR(&lcd_blit_obj) },
    { MP_ROM_QSTR(MP_QSTR_buffer),   MP_ROM_PTR(&lcd_buffer_obj) },
    { MP_ROM_QSTR(MP_QSTR_WIDTH),    MP_ROM_INT(LCD_WIDTH) },
    { MP_ROM_QSTR(MP_QSTR_HEIGHT),   MP_ROM_INT(LCD_HEIGHT) },
};
static MP_DEFINE_CONST_DICT(lcd_module_globals, lcd_module_globals_table);

const mp_obj_module_t lcd_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&lcd_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_lcd, lcd_module);
