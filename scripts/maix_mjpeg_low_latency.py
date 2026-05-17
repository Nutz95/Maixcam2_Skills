#!/usr/bin/env python3
"""Standalone MJPEG streamer for MaixCAM using MaixPy.

This version is intentionally simple and stable:
- single camera channel only
- no aggressive startup frame skipping
- direct stream.write(img)
"""

from maix import app, camera, http, image, time


# Camera settings (stable default mirrors your working example).
MAIN_WIDTH = 1280
MAIN_HEIGHT = 720
MAIN_FPS = 60
MAIN_FORMAT = image.Format.FMT_RGB888

STREAM_BUFFERS = 1

# HTTP streaming load control.
# Camera can keep running fast, while HTTP publish rate is capped to keep CPU/network stable
# when browser clients are connected.
TARGET_HTTP_FPS = 60
JPEG_QUALITY = 60

# HTTP server settings.
HTTP_HOST = "0.0.0.0"
HTTP_PORT = 8000
HTTP_CLIENTS = 4

HTML = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Maix MJPEG Stream</title>
    <style>
        :root {
            --bg: #0f1115;
            --panel: #171a21;
            --text: #e6e8ef;
            --muted: #9aa3b2;
            --accent: #39d98a;
            --accent-2: #1f6feb;
        }
        html, body {
            margin: 0;
            background: radial-gradient(circle at top, #171b24, var(--bg) 55%);
            color: var(--text);
            font-family: "Segoe UI", "Noto Sans", sans-serif;
        }
        .wrap {
            max-width: 1200px;
            margin: 0 auto;
            padding: 12px;
        }
        .bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            background: var(--panel);
            border: 1px solid #252b36;
            border-radius: 12px;
            padding: 10px 12px;
            margin-bottom: 10px;
        }
        .meta {
            color: var(--muted);
            font-size: 14px;
        }
        .controls {
            display: flex;
            gap: 8px;
        }
        button {
            border: 1px solid #2d3645;
            background: #1d2430;
            color: var(--text);
            border-radius: 8px;
            padding: 8px 12px;
            cursor: pointer;
            font-size: 14px;
        }
        button.primary {
            border-color: #2f7050;
            background: #1c3b2c;
            color: var(--accent);
        }
        .viewer {
            background: #000;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #252b36;
            min-height: 220px;
        }
        .viewer img {
            display: block;
            width: 100%;
            height: auto;
            object-fit: contain;
            max-height: calc(100vh - 110px);
        }
        .hint {
            margin-top: 8px;
            color: var(--muted);
            font-size: 13px;
        }
    </style>
</head>
<body>
  <div class="wrap">
        <div class="bar">
            <div class="meta" id="meta">Maix MJPEG stream</div>
            <div class="controls">
                <button id="fs" class="primary">Plein ecran</button>
                <button id="fit">Adapter</button>
            </div>
        </div>

        <div class="viewer" id="viewer">
            <img id="stream" src="/stream" alt="MJPEG stream">
        </div>

        <div class="hint">
            Raccourci: double-clic sur l'image pour le plein ecran.
        </div>
  </div>

    <script>
        const viewer = document.getElementById('viewer');
        const img = document.getElementById('stream');
        const fsBtn = document.getElementById('fs');
        const fitBtn = document.getElementById('fit');
        const meta = document.getElementById('meta');

        function updateFsLabel() {
            const on = !!document.fullscreenElement;
            fsBtn.textContent = on ? 'Quitter plein ecran' : 'Plein ecran';
        }

        async function toggleFullscreen() {
            try {
                if (!document.fullscreenElement) {
                    await viewer.requestFullscreen();
                } else {
                    await document.exitFullscreen();
                }
            } catch (e) {}
            updateFsLabel();
        }

        let containMode = true;
        function toggleFit() {
            containMode = !containMode;
            img.style.objectFit = containMode ? 'contain' : 'cover';
            fitBtn.textContent = containMode ? 'Adapter' : 'Remplir';
        }

        fsBtn.addEventListener('click', toggleFullscreen);
        fitBtn.addEventListener('click', toggleFit);
        img.addEventListener('dblclick', toggleFullscreen);
        document.addEventListener('fullscreenchange', updateFsLabel);

        img.addEventListener('load', () => {
            meta.textContent = `Maix MJPEG stream ${img.naturalWidth}x${img.naturalHeight}`;
        });
    </script>
</body>
</html>
"""


def close_camera(cam_obj):
    if cam_obj is None:
        return
    try:
        if cam_obj.is_opened():
            cam_obj.close()
    except Exception:
        pass


def main():
    cam = None
    streamer = None

    try:
        cam = camera.Camera(
            MAIN_WIDTH,
            MAIN_HEIGHT,
            MAIN_FORMAT,
            fps=MAIN_FPS,
            buff_num=STREAM_BUFFERS,
        )

        # Warm-up via read loop instead of skip_frames to avoid occasional startup
        # timeout paths seen on some runtime combinations.
        warmup_ok = False
        for _ in range(20):
            try:
                _ = cam.read()
                warmup_ok = True
                break
            except Exception:
                time.sleep_ms(80)
        if not warmup_ok:
            raise RuntimeError("camera warm-up failed")

        streamer = http.JpegStreamer(HTTP_HOST, HTTP_PORT, HTTP_CLIENTS)
        streamer.set_html(HTML)
        streamer.start()

        print("MJPEG stream ready:")
        print("  index : http://{}:{}".format(streamer.host(), streamer.port()))
        print("  stream: http://{}:{}/stream".format(streamer.host(), streamer.port()))
        print(
            "  camera={}x{}@{}  single_channel=true  target_http_fps={}  jpeg_q={}".format(
                MAIN_WIDTH,
                MAIN_HEIGHT,
                MAIN_FPS,
                TARGET_HTTP_FPS,
                JPEG_QUALITY,
            )
        )

        last_report_ms = time.ticks_ms()
        read_frames = 0
        sent_frames = 0
        next_send_ms = time.ticks_ms()
        send_interval_ms = max(1, int(1000 / max(1, TARGET_HTTP_FPS)))

        while not app.need_exit():
            img = cam.read()
            read_frames += 1

            now = time.ticks_ms()
            if now >= next_send_ms:
                jpg = img.to_jpeg(JPEG_QUALITY)
                streamer.write(jpg)
                sent_frames += 1
                next_send_ms = now + send_interval_ms

            if now - last_report_ms >= 1000:
                read_fps = read_frames * 1000.0 / max(1, now - last_report_ms)
                sent_fps = sent_frames * 1000.0 / max(1, now - last_report_ms)
                print("read_fps={:.1f} send_fps={:.1f}".format(read_fps, sent_fps))
                read_frames = 0
                sent_frames = 0
                last_report_ms = now

    finally:
        if streamer is not None:
            try:
                streamer.stop()
            except Exception:
                pass
        close_camera(cam)


if __name__ == "__main__":
    main()