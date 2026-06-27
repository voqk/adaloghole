#pragma once
// OV2640 camera: init and grab a single JPEG frame.  [STUB → capture sketch]
#include "esp_camera.h"

// Configure pins, PSRAM JPEG framebuffer, and lock the exposure/white-balance
// so a bright TV in a dark room doesn't make the sensor hunt frame-to-frame.
// Returns false if the camera failed to probe (bad cable/seating).
bool camera_init();

// Grab the freshest JPEG frame. Returns a framebuffer you MUST hand back with
// camera_return() once you've POSTed it — otherwise the pool starves and the
// next capture returns nullptr.
camera_fb_t *camera_capture();
void camera_return(camera_fb_t *fb);
