MICROPYTHON_TOP = micropython

SRC_QSTR += src/mod_host.c src/mod_lcd.c

SRC_QSTR += $(addprefix $(MICROPYTHON_TOP)/extmod/, \
	vfs.c vfs_reader.c vfs_posix.c vfs_posix_file.c vfs_blockdev.c modos.c modjson.c modrandom.c)

CFLAGS += -I$(CURDIR) -I$(CURDIR)/src -I$(CURDIR)/$(MICROPYTHON_TOP)

include $(MICROPYTHON_TOP)/ports/embed/embed.mk
