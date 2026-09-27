ifeq ($(OS),Windows_NT)
EXE       = .exe
endif
PROG      = sham$(EXE)

.DEFAULT_GOAL := $(PROG)
MPY_TOP   = micropython
EMBED_DIR = micropython_embed
IMGUI     = lib/imgui
BUILD     = build

CFLAGS  += -I. -Isrc -Ilib -I$(IMGUI) -I$(IMGUI)/backends -I$(EMBED_DIR) -I$(EMBED_DIR)/port -I$(MPY_TOP)
CFLAGS  += -Wall -O2 -fno-common -MMD -MP
CFLAGS  += $(shell pkg-config --cflags sdl3)

LDFLAGS += $(shell pkg-config --libs sdl3)

UNAME := $(shell uname -s)
ifeq ($(OS),Windows_NT)
SRC_OBJC    =
SRC_MENU    = src/menu_imgui.cpp
SYSTEM_LIBS = -lpthread
else ifeq ($(UNAME),Darwin)
LDFLAGS    += -framework CoreServices -framework Cocoa
SRC_OBJC    = src/menu_macos.m
SRC_MENU    =
SYSTEM_LIBS =
else
SRC_OBJC    =
SRC_MENU    = src/menu_imgui.cpp
SYSTEM_LIBS = -lutil -lm -lpthread
endif
LDFLAGS += $(SYSTEM_LIBS)

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
ifneq ($(UNAME),Darwin)
$(error TOUCHSCREEN=1 is macOS only)
endif
BUILD   := $(BUILD)/touchscreen
CFLAGS  += -DSHAM_TOUCHSCREEN
LDFLAGS += -framework IOKit
SRC_APP += src/touch_macos.c
endif

CONFIG      = build/config
CONFIG_TEXT = TOUCHSCREEN=$(TOUCHSCREEN)
ifneq ($(CONFIG_TEXT),$(shell cat $(CONFIG) 2>/dev/null))
$(shell mkdir -p build; echo "$(CONFIG_TEXT)" > $(CONFIG); rm -f $(PROG))
endif

SRC_APP_CXX = \
	src/main.cpp \
	src/device.cpp \
	src/case_raster.cpp \
	src/console.cpp \
	$(SRC_MENU)

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

ARCH        := $(shell uname -m)
SDL_PREFIX  := $(shell pkg-config --variable=prefix sdl3)
SDL_LICENCE := $(firstword $(wildcard $(SDL_PREFIX)/share/licenses/SDL3/LICENSE.txt $(SDL_PREFIX)/share/licenses/sdl3/LICENSE.txt))
ifeq ($(OS),Windows_NT)
DIST_OS     = windows
else ifeq ($(UNAME),Darwin)
DIST_OS     = macos
else
DIST_OS     = linux
endif
DIST_NAME   = sham-$(DIST_OS)-$(ARCH)
DIST_DIR    = dist/$(DIST_NAME)

dist: $(PROG)
	rm -rf $(DIST_DIR) dist/$(DIST_NAME).zip
	mkdir -p $(DIST_DIR)/licences
	cp $(PROG) README.md $(DIST_DIR)/
	cp -R assets os $(DIST_DIR)/
	find $(DIST_DIR)/os -name __pycache__ -prune -exec rm -rf {} +
	find $(DIST_DIR)/os -name .DS_Store -exec rm -f {} +
	cp licences/* $(DIST_DIR)/licences/
	cp lib/imgui/LICENSE.txt $(DIST_DIR)/licences/imgui.txt
	cp $(MPY_TOP)/LICENSE $(DIST_DIR)/licences/micropython.txt
ifeq ($(DIST_OS),macos)
	cp $(shell pkg-config --variable=libdir sdl3)/libSDL3.0.dylib $(DIST_DIR)/
	install_name_tool -id @executable_path/libSDL3.0.dylib $(DIST_DIR)/libSDL3.0.dylib
	install_name_tool -change "$$(otool -L $(PROG) | awk '/libSDL3/ { print $$1 }')" @executable_path/libSDL3.0.dylib $(DIST_DIR)/$(PROG)
	codesign --force --sign - $(DIST_DIR)/libSDL3.0.dylib $(DIST_DIR)/$(PROG)
endif
ifeq ($(DIST_OS),windows)
	cp $$(ldd $(PROG) | awk '$$3 ~ /^\/(ucrt64|mingw64|clang64)\// { print $$3 }' | sort -u) $(DIST_DIR)/
endif
ifneq ($(DIST_OS),linux)
ifneq ($(SDL_LICENCE),)
	cp $(SDL_LICENCE) $(DIST_DIR)/licences/SDL3.txt
endif
endif
	cd dist && zip -qry $(DIST_NAME).zip $(DIST_NAME)

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
	rm -rf build dist $(PROG)

rebuild: embed-clean embed clean $(PROG)

.PHONY: embed embed-clean run screenshot screenshots keyboard scratches worldmap samples keyicons check dist clean rebuild
