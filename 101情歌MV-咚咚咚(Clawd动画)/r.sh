#!/bin/sh
# Render without a GPU (cloud container): software WebGL at 2/3 pixel density. On a machine with a GPU, use plain `node render.mjs ...`.
exec node render.mjs --soft-gl --pd=0.6667 --chrome=${CHROME_PATH:-/opt/pw-browsers/chromium-1194/chrome-linux/chrome} "$@"
