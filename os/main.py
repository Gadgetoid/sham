import host
import lcd
from system import gfx, icons, keys, prefs, sound, store, ui
from system.shell import Shell

shell = Shell()
print("pocket: {} apps".format(len(shell.apps)))
shell.run()
