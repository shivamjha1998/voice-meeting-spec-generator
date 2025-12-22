#!/bin/bash

# 1. Start PulseAudio as a daemon (system mode for root usage in Docker)
pulseaudio -D --exit-idle-time=-1

# 2. Create a virtual audio sink (This acts as our "Speaker")
pactl load-module module-null-sink sink_name=VirtualSpeaker sink_properties=device.description="Virtual_Speaker"

# 3. Set this new sink as the default output device
pactl set-default-sink VirtualSpeaker

# 4. Set the "Monitor" of this sink as the default input device (Virtual Mic)
pactl set-default-source VirtualSpeaker.monitor

echo "🔊 Virtual Audio Environment Configured (Speaker + Mic)"

# 5. Execute the command passed to the docker container (e.g., python -m backend.api.main)
exec "$@"