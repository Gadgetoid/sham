PROG      = sham

.DEFAULT_GOAL := $(PROG)
MPY_TOP   = micropython
EMBED_DIR = micropython_embed
IMGUI     = lib/imgui
BUILD     = build

CFLAGS  += -I. -Isrc -Ilib -I$(IMGUI) -I$(IMGUI)/backends -I$(EMBED_DIR) -I$(EMBED_DIR)/port -I$(MPY_TOP)
CFLAGS  += -Wall -O2 -fno-common -MMD -MP
CFLAGS  += $(shell pkg-config --cflags sdl3)

LDFLAGS += $(shell pkg-config --libs sdl3) -framework CoreServices -framework Cocoa

CXXFLAGS = $(filter-out -std=c99,$(CFLAGS)) -std=c++17

SRC_APP = \
	src/runtime.c \
	src/mphal.c \
	src/keys.c \
	src/lcd.c \
	src/watch.c \
	src/beeper.c \
	src/mod_host.c \
	src/mod_lcd.c

TOUCHSCREEN ?= 0
ifeq ($(TOUCHSCREEN),1)
ifneq ($(shell uname -s),Darwin)
$(error TOUCHSCREEN=1 is macOS only)
endif
BUILD   := $(BUILD)/touchscreen
CFLAGS  += -DSHAM_TOUCHSCREEN
LDFLAGS += -framework IOKit
SRC_APP += src/touch_macos.c
endif

CONFIG = build/config
$(shell mkdir -p build; echo "TOUCHSCREEN=$(TOUCHSCREEN)" | cmp -s - $(CONFIG) || { echo "TOUCHSCREEN=$(TOUCHSCREEN)" > $(CONFIG); rm -f $(PROG); })

SRC_OBJC = src/menu_macos.m

SRC_APP_CXX = \
	src/main.cpp \
	src/device.cpp \
	src/case_raster.cpp \
	src/console.cpp

SRC_IMGUI = $(addprefix $(IMGUI)/, \
	imgui.cpp imgui_draw.cpp imgui_tables.cpp imgui_widgets.cpp \
	backends/imgui_impl_sdl3.cpp backends/imgui_impl_sdlrenderer3.cpp)

SRC_EXTMOD = $(addprefix $(MPY_TOP)/extmod/, \
	vfs.c vfs_reader.c vfs_posix.c vfs_posix_file.c vfs_blockdev.c modos.c modjson.c modrandom.c)

SRC_EMBED = $(filter-out $(EMBED_DIR)/port/mphalport.c, \
	$(wildcard $(EMBED_DIR)/*/*.c) $(wildcard $(EMBED_DIR)/*/*/*.c))

SRC_C   = $(SRC_APP) $(SRC_EXTMOD) $(SRC_EMBED)
SRC_CXX = $(SRC_APP_CXX) $(SRC_IMGUI)

OBJ  = $(addprefix $(BUILD)/,$(SRC_C:.c=.o) $(SRC_CXX:.cpp=.opp) $(SRC_OBJC:.m=.om))
DEPS = $(OBJ:.o=.d)
DEPS := $(DEPS:.opp=.d)
DEPS := $(DEPS:.om=.d)

GENHDR_QSTR = $(EMBED_DIR)/genhdr/qstrdefs.generated.h

$(BUILD)/%.o: %.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c -o $@ $<

$(BUILD)/%.opp: %.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) -c -o $@ $<

$(BUILD)/%.om: %.m
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -fobjc-arc -c -o $@ $<

$(OBJ): $(GENHDR_QSTR)

$(GENHDR_QSTR):
	$(MAKE) -f micropython_embed.mk

$(PROG): $(OBJ)
	$(CXX) -o $@ $^ $(LDFLAGS)

-include $(DEPS)

embed:
	$(MAKE) -f micropython_embed.mk

embed-clean:
	rm -rf build-embed $(EMBED_DIR)

run: $(PROG)
	./$(PROG) --root=os --data=data

screenshot: $(PROG)
	./$(PROG) --root=os --data=data --screenshot=$(BUILD)/screenshot.bmp

WORLD_GEOJSON ?= ../../badgeware/tufty2350/firmware/assets/world.geo.json
MATERIAL_SYMBOLS ?= ../tetra-command/py/fonts/MaterialSymbolsOutlined.ttf

keyboard:
	python3 tools/make_keyboard.py tools/keyboard_layout.json src/keyboard_layout.h tools/sham_layout.svg
	python3 tools/make_lid.py tools/sham_layout.svg src/lid_layout.h

scratches:
	python3 tools/make_surface_scratches.py assets/lcd_scratches.bin

worldmap:
	python3 tools/make_worldmap.py $(WORLD_GEOJSON) os/assets/worldmap.bin

samples:
	python3 tools/make_wzd.py tools/basic/sierpinski.bas os/samples/wzd/Sierpinski.wzd Sierpinski "Chaos game: plots the Sierpinski triangle one point at a time. Press any key to finish."

keyicons:
	python3 tools/make_key_icons.py $(MATERIAL_SYMBOLS) assets/MaterialSymbolsKeys.ttf

screenshots: $(PROG)
	python3 tools/readme_screenshots.py

check: $(PROG)
	python3 tools/check.py --smoke

clean:
	rm -rf $(BUILD) $(PROG)

rebuild: embed-clean embed clean $(PROG)

.PHONY: embed embed-clean run screenshot screenshots keyboard scratches worldmap samples keyicons check clean rebuild
