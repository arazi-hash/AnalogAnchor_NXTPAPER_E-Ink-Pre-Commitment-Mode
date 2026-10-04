#!/system/bin/sh
# Official 13.6+ native launcher, with fallback for the older start.sh method.
package=moe.shizuku.privileged.api
apk=$(pm path "$package" | sed -n 's/^package://p' | head -n 1)
if [ -z "$apk" ]; then
    echo 'Install and open the official Shizuku app first.' >&2
    exit 1
fi
apk_dir=${apk%/*}
for launcher in "$apk_dir"/lib/*/libshizuku.so; do
    if [ -x "$launcher" ]; then
        "$launcher" "--apk=$apk"
        exit $?
    fi
done
legacy=/sdcard/Android/data/moe.shizuku.privileged.api/start.sh
if [ -r "$legacy" ]; then
    sh "$legacy"
    exit $?
fi
echo 'No Shizuku launcher found. Open Shizuku, choose Start by connecting to a computer, and use its displayed command.' >&2
exit 1
