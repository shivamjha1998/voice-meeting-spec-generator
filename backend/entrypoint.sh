#!/bin/bash

# 1. Clean up previous locks
rm -rf /var/run/pulse /var/lib/pulse /root/.config/pulse
mkdir -p /var/run/pulse
mkdir -p /var/lib/pulse
mkdir -p /root/.config/pulse

# 2. Start Virtual Display (Xvfb)
Xvfb :99 -screen 0 1280x1024x24 > /dev/null 2>&1 &
export DISPLAY=:99.0

# 3. Start DBus (often needed by PulseAudio)
rm -f /var/run/dbus/pid
if [ ! -d /var/run/dbus ]; then
    mkdir -p /var/run/dbus
fi
dbus-uuidgen > /var/lib/dbus/machine-id
dbus-daemon --config-file=/usr/share/dbus-1/system.conf --print-address > /dev/null &

# 4. Start PulseAudio in System Mode
# --disallow-module-loading prevents the warning you saw
# -vvvv helps us debug if it crashes
pulseaudio -D --system --disallow-exit --disallow-module-loading=false --exit-idle-time=-1 -vvvv --log-target=file:/var/log/pulse.log

# 5. WAIT for the socket to appear
echo "⏳ Waiting for PulseAudio socket..."
for i in {1..10}; do
    if [ -S /var/run/pulse/native ]; then
        echo "✅ Socket found."
        break
    fi
    sleep 1
done

# 6. FORCE PERMISSIONS
# PulseAudio drops privileges to 'pulse' user, so root cannot write to the socket by default in some setups.
# We explicitly open it up for this container.
chmod -R 777 /var/run/pulse
chown -R root:root /var/run/pulse

# 7. Configure Virtual Devices
# Wait for the server to be responsive
for i in {1..5}; do
    if pactl info >/dev/null 2>&1; then
        echo "✅ PulseAudio server reachable."
        break
    fi
    echo "⏳ Connecting to PulseAudio..."
    sleep 1
done

# Load Null Sink (Virtual Speaker)
pactl load-module module-null-sink sink_name=VirtualSpeaker sink_properties=device.description="Virtual_Speaker"

# Set Defaults
pactl set-default-sink VirtualSpeaker
pactl set-default-source VirtualSpeaker.monitor

echo "🖥️  Virtual Display & 🔊 Audio Environment Configured"

# 8. Run Application
exec "$@"