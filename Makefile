PROG      = pocket

.DEFAULT_GOAL := $(PROG)
MPY_TOP   = micropython
EMBED_DIR = micropython_embed
IMGUI     = lib/imgui
BUILD     = build

CFLAGS  += -I. -Isrc -Ilib -I$(IMGUI) -I$(IMGUI)/backends -I$(EMBED_DIR) -I$(EMBED_DIR)/port -I$(MPY_TOP)
CFLAGS  += -Wall -O2 -fno-common -MMD -MP
CFLAGS  += $(shell pkg-config --cflags sdl3)

LDFLAGS += $(shell pkg-config --libs sdl3) -framework CoreServices

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

SRC_APP_CXX = \
	src/main.cpp \
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

OBJ  = $(addprefix $(BUILD)/,$(SRC_C:.c=.o) $(SRC_CXX:.cpp=.opp))
DEPS = $(OBJ:.o=.d)
DEPS := $(DEPS:.opp=.d)

GENHDR_QSTR = $(EMBED_DIR)/genhdr/qstrdefs.generated.h

$(BUILD)/%.o: %.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c -o $@ $<

$(BUILD)/%.opp: %.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) -c -o $@ $<

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
	./$(PROG)

screenshot: $(PROG)
	./$(PROG) --screenshot=$(BUILD)/screenshot.bmp

check: $(PROG)
	python3 tools/check.py --smoke

clean:
	rm -rf $(BUILD) $(PROG)

rebuild: embed-clean embed clean $(PROG)

.PHONY: embed embed-clean run screenshot check clean rebuild
