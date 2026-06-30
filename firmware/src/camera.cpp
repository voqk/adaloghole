// OV2640 camera implementation.  [STUB → capture sketch]
//
// The classifier is coarse (program vs. commercial), so resolution is not the
// constraint — the Anthropic vision API downscales to ~1568px on the long edge
// anyway. The real enemy is the sensor's auto-exposure/auto-white-balance:
// pointed at a bright TV in a dark room it will hunt, blow out the screen, and
// pump brightness between frames. We lock those down so every frame looks the
// same and the classifier sees a stable image.
#include "camera.h"
#include "config.h"
#include <Arduino.h>

// --- Seeed XIAO ESP32-S3 Sense pin map (OV2640 on the camera expansion board) ---
#define PWDN_GPIO_NUM  -1
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM  10
#define SIOD_GPIO_NUM  40
#define SIOC_GPIO_NUM  39
#define Y9_GPIO_NUM    48
#define Y8_GPIO_NUM    11
#define Y7_GPIO_NUM    12
#define Y6_GPIO_NUM    14
#define Y5_GPIO_NUM    16
#define Y4_GPIO_NUM    18
#define Y3_GPIO_NUM    17
#define Y2_GPIO_NUM    15
#define VSYNC_GPIO_NUM 38
#define HREF_GPIO_NUM  47
#define PCLK_GPIO_NUM  13

bool camera_init() {
  camera_config_t config = {};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;        // we want a ready-to-POST JPEG

  // UXGA (1600x1200) is the OV2640's max — captures the most real detail the
  // vision API can use (it downscales to ~1568px long edge). SVGA (800x600) is
  // smaller/cheaper but sits below that, so the model only ever sees 800px of
  // detail. Requires PSRAM (we have it: -DBOARD_HAS_PSRAM).
  config.frame_size   = FRAMESIZE_UXGA;
  config.jpeg_quality = 10;                    // 10..12 = good; lower = bigger/better
  config.fb_count     = 2;                     // double-buffer in PSRAM
  config.fb_location  = CAMERA_FB_IN_PSRAM;
  config.grab_mode    = CAMERA_GRAB_LATEST;    // always hand back the newest frame

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[cam] init failed: 0x%x (check the camera ribbon)\n", err);
    return false;
  }

  // --- The actual capture-settings block: stop the sensor from hunting ---
  sensor_t *s = esp_camera_sensor_get();
  if (!s) return false;

#if CAM_AEC_MANUAL
  s->set_exposure_ctrl(s, 0);            // OFF: no auto-exposure
  s->set_aec2(s, 0);                     // OFF: no DSP auto-exposure either
  s->set_aec_value(s, CAM_AEC_VALUE);    // fixed exposure (0..1200), tuned per room
  s->set_gain_ctrl(s, 0);                // OFF: no auto-gain (gain = noise)
  s->set_agc_gain(s, CAM_AGC_VALUE);     // fixed gain (0..30), keep low
  s->set_gainceiling(s, GAINCEILING_2X); // cap gain so dark scenes don't get noisy
#endif

  s->set_whitebal(s, 0);                 // OFF: lock white balance...
  s->set_awb_gain(s, 0);                 // ...so colors don't drift on scene cuts
  s->set_wb_mode(s, 0);

  s->set_brightness(s, 0);               // -2..2, neutral
  s->set_contrast(s, 0);                 // -2..2
  s->set_saturation(s, 0);               // -2..2

  s->set_bpc(s, 1);                      // bad-pixel correction
  s->set_wpc(s, 1);                      // white-pixel correction
  s->set_lenc(s, 1);                     // lens shading correction (evens vignetting)
  s->set_dcw(s, 1);

  s->set_vflip(s, CAM_VFLIP);            // match how the board is mounted
  s->set_hmirror(s, CAM_HMIRROR);

  // Settings take a frame or two to land — flush a couple so the first real
  // capture already reflects the locked exposure.
  for (int i = 0; i < 2; i++) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (fb) esp_camera_fb_return(fb);
  }

  Serial.println("[cam] init ok (exposure + white balance locked)");
  return true;
}

camera_fb_t *camera_capture() {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("[cam] capture failed (nullptr)");
    return nullptr;
  }
  return fb;  // caller POSTs fb->buf / fb->len, then calls camera_return(fb)
}

void camera_return(camera_fb_t *fb) {
  if (fb) esp_camera_fb_return(fb);
}
