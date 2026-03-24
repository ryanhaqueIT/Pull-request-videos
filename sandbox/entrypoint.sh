#!/bin/bash
# sandbox/entrypoint.sh
# Starts Xvfb, ffmpeg recording, then runs the agent.

set -euo pipefail

DISPLAY=":99"
VIDEO_DIR="/artifacts"
RESOLUTION="1280x720"
FPS=15

echo "[sandbox] Starting Xvfb on display ${DISPLAY}..."
Xvfb ${DISPLAY} -screen 0 ${RESOLUTION}x24 -ac &
XVFB_PID=$!
sleep 1

echo "[sandbox] Starting screen recording..."
ffmpeg -y -f x11grab -video_size ${RESOLUTION} -framerate ${FPS} \
  -i ${DISPLAY} -c:v libx264 -preset ultrafast -crf 28 \
  -pix_fmt yuv420p -movflags +faststart \
  ${VIDEO_DIR}/session-recording.mp4 &
FFMPEG_PID=$!
sleep 0.5

echo "[sandbox] Running agent..."
python /app/agent_runner.py
AGENT_EXIT=$?

echo "[sandbox] Stopping recording..."
kill -SIGINT ${FFMPEG_PID} 2>/dev/null || true
wait ${FFMPEG_PID} 2>/dev/null || true

echo "[sandbox] Stopping Xvfb..."
kill ${XVFB_PID} 2>/dev/null || true

echo "[sandbox] Agent exited with code ${AGENT_EXIT}"
echo "[sandbox] Artifacts in ${VIDEO_DIR}:"
ls -la ${VIDEO_DIR}/

exit ${AGENT_EXIT}
