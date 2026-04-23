#!/usr/bin/env python3
"""Recolor ontology dashboard images from dark-blue theme to light semantic-blue theme."""

import colorsys
import os
import numpy as np
from PIL import Image

IMG_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'public', 'images', 'ontology')

# Target hue for semantic blue (#4c6ef5) ≈ 228° → 0.633 in [0,1]
TARGET_HUE = 228 / 360.0


def rgb_to_hls_array(img_arr):
    """Convert uint8 RGB array to float HLS arrays."""
    r, g, b = img_arr[:, :, 0] / 255.0, img_arr[:, :, 1] / 255.0, img_arr[:, :, 2] / 255.0
    h = np.zeros_like(r)
    l = np.zeros_like(r)
    s = np.zeros_like(r)
    for y in range(r.shape[0]):
        for x in range(r.shape[1]):
            h[y, x], l[y, x], s[y, x] = colorsys.rgb_to_hls(r[y, x], g[y, x], b[y, x])
    return h, l, s


def hls_to_rgb_array(h, l, s):
    """Convert float HLS arrays back to uint8 RGB array."""
    out = np.zeros((*h.shape, 3), dtype=np.uint8)
    for y in range(h.shape[0]):
        for x in range(h.shape[1]):
            r, g, b = colorsys.hls_to_rgb(h[y, x], l[y, x], s[y, x])
            out[y, x] = [int(r * 255), int(g * 255), int(b * 255)]
    return out


# Vectorized version using numpy for speed
def recolor_pixels(img_arr, lighten=0.0, sat_scale=1.0, force_light_bg=False):
    """
    Recolor image pixels:
    - Shift all chromatic pixels toward semantic blue hue
    - Lighten dark pixels
    - Remove reds/golds, shift to blue
    - force_light_bg: make dark areas very light (for backgrounds)
    """
    r = img_arr[:, :, 0].astype(np.float64) / 255.0
    g = img_arr[:, :, 1].astype(np.float64) / 255.0
    b = img_arr[:, :, 2].astype(np.float64) / 255.0

    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin

    # Lightness
    l = (cmax + cmin) / 2.0

    # Saturation
    s = np.where(delta == 0, 0.0,
                 np.where(l <= 0.5, delta / (cmax + cmin + 1e-10), delta / (2.0 - cmax - cmin + 1e-10)))

    # Hue
    h = np.zeros_like(r)
    mask_r = (cmax == r) & (delta > 0)
    mask_g = (cmax == g) & (delta > 0) & ~mask_r
    mask_b = (cmax == b) & (delta > 0) & ~mask_r & ~mask_g

    h[mask_r] = (((g[mask_r] - b[mask_r]) / (delta[mask_r] + 1e-10)) % 6) / 6.0
    h[mask_g] = (((b[mask_g] - r[mask_g]) / (delta[mask_g] + 1e-10)) + 2) / 6.0
    h[mask_b] = (((r[mask_b] - g[mask_b]) / (delta[mask_b] + 1e-10)) + 4) / 6.0

    chromatic = s > 0.05

    # Shift all chromatic pixels to target hue
    h[chromatic] = TARGET_HUE

    # For reds/golds that were shifted, also reduce saturation
    # (they'll already be at target hue now)

    if force_light_bg:
        # Make everything much lighter - dark areas become very light
        l = np.where(chromatic, np.clip(l * 0.3 + 0.75, 0.85, 0.98), np.clip(l * 0.2 + 0.85, 0.9, 1.0))
        s[chromatic] = s[chromatic] * 0.35
    else:
        # Normal lightening
        if lighten > 0:
            l = np.clip(l + lighten * (1.0 - l), 0, 1)
        s = s * sat_scale

    # HLS to RGB
    c = (1.0 - np.abs(2.0 * l - 1.0)) * s
    h6 = h * 6.0
    x = c * (1.0 - np.abs(h6 % 2 - 1.0))
    m = l - c / 2.0

    r_out = np.zeros_like(r)
    g_out = np.zeros_like(r)
    b_out = np.zeros_like(r)

    for lo, hi, rv, gv, bv in [
        (0, 1, 'c', 'x', '0'), (1, 2, 'x', 'c', '0'), (2, 3, '0', 'c', 'x'),
        (3, 4, '0', 'x', 'c'), (4, 5, 'x', '0', 'c'), (5, 6, 'c', '0', 'x'),
    ]:
        mask = (h6 >= lo) & (h6 < hi)
        for out, val in [(r_out, rv), (g_out, gv), (b_out, bv)]:
            if val == 'c':
                out[mask] = c[mask]
            elif val == 'x':
                out[mask] = x[mask]

    r_out = np.clip((r_out + m) * 255, 0, 255).astype(np.uint8)
    g_out = np.clip((g_out + m) * 255, 0, 255).astype(np.uint8)
    b_out = np.clip((b_out + m) * 255, 0, 255).astype(np.uint8)

    return np.stack([r_out, g_out, b_out], axis=2)


def process_rgba(img, **kwargs):
    """Process an RGBA image, preserving alpha."""
    arr = np.array(img)
    rgb = recolor_pixels(arr[:, :, :3], **kwargs)
    result = np.dstack([rgb, arr[:, :, 3]])
    return Image.fromarray(result, 'RGBA')


def process_rgb(img, **kwargs):
    """Process an RGB image."""
    arr = np.array(img)
    rgb = recolor_pixels(arr, **kwargs)
    return Image.fromarray(rgb, 'RGB')


def make_gradient_bg(size):
    """Generate a white-to-very-light-blue vertical gradient."""
    w, h = size
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        t = y / (h - 1)
        # #ffffff → #f0f3ff
        arr[y, :, 0] = int(255 * (1 - t) + 240 * t)
        arr[y, :, 1] = int(255 * (1 - t) + 243 * t)
        arr[y, :, 2] = int(255 * (1 - t) + 255 * t)
    return Image.fromarray(arr, 'RGB')


def main():
    os.chdir(IMG_DIR)

    print("=== Processing bg.png (gradient background) ===")
    bg = Image.open('bg.png')
    new_bg = make_gradient_bg(bg.size)
    new_bg.save('bg.png')
    print(f"  Done: {bg.size}")

    # Large backgrounds - make very light
    light_bg_files = [
        'bg-本体层.png',
        'bg-DATA SOURCES.png',
        'bg-LOGIC SOURCES.png',
        'bg-AUTOMATIONS.png',
        'bg-ANALYTICS &WORKFLOWS.png',
        'bg-SYSTEMS OF ACTION.png',
        'bg-PRODUCTS & SDKs.png',
    ]
    for f in light_bg_files:
        if not os.path.exists(f):
            print(f"  SKIP (not found): {f}")
            continue
        print(f"=== Processing {f} (light bg) ===")
        img = Image.open(f)
        result = process_rgba(img, force_light_bg=True)
        result.save(f)
        print(f"  Done: {img.size}")

    # Decorative elements - lighten significantly, keep some structure
    deco_files = ['dh.png', 'left.png', 'right.png', 'bottom.png', 'label-bg.png', 'btn-重置视角.png']
    for f in deco_files:
        if not os.path.exists(f):
            print(f"  SKIP (not found): {f}")
            continue
        print(f"=== Processing {f} (decorative) ===")
        img = Image.open(f)
        result = process_rgba(img, lighten=0.55, sat_scale=0.5)
        result.save(f)
        print(f"  Done: {img.size}")

    # Icons - moderate recolor, keep recognizable
    icon_files = [
        'icon-核心本体.png', 'icon-域本体.png',
        'icon-客户.png', 'icon-产品.png', 'icon-组织.png',
        'icon-订单.png', 'icon-员工.png', 'icon-地址.png',
        'icon-DATA SOURCES.png', 'icon-LOGIC SOURCES.png', 'icon-SYSTEMS OF ACTION.png',
    ]
    for f in icon_files:
        if not os.path.exists(f):
            print(f"  SKIP (not found): {f}")
            continue
        print(f"=== Processing {f} (icon) ===")
        img = Image.open(f)
        result = process_rgba(img, lighten=0.25, sat_scale=0.7)
        result.save(f)
        print(f"  Done: {img.size}")

    print("\n=== All done! ===")


if __name__ == '__main__':
    main()
