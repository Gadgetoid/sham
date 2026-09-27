#!/bin/sh
set -e

zip_path=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
work=$(mktemp -d)
package="$work/$(basename "$zip_path" .zip)"

silent_data() {
    mkdir -p "$1"
    printf '{"sound": false, "click": false}' > "$1/prefs.json"
}

run_sham() {
    SDL_VIDEO_DRIVER=dummy SDL_AUDIO_DRIVER=dummy XDG_DATA_HOME="$1" "$package/sham" --no-watch --data="$2" \
        --exec="host.sound(False); host.key_click(False)" --screenshot="$2/screen.bmp" --frames=5
    test -s "$2/screen.bmp"
    test -d "$1/sham/os/apps"
}

cd "$work"
unzip -q "$zip_path"

cd "$package"
silent_data smoke
run_sham "$work/home-inside" smoke

mkdir -p "$work/elsewhere"
cd "$work/elsewhere"
silent_data smoke
run_sham "$work/home-elsewhere" "$work/elsewhere/smoke"

rm -rf "$work"
echo "packaged smoke test passed"
