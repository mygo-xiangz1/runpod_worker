import math

import torch
import torch.nn.functional as F


def adjust_photo(images, exposure_ev=0.0, temperature=0.0, tint=0.0,
                 highlights=0.0, shadows=0.0, grain_amount=0.0,
                 grain_size=1, grain_seed=12345, mix=1.0):
    """Adjust display-referred sRGB images; preserve alpha and the input device."""
    if images.ndim != 4 or images.shape[-1] not in (3, 4):
        raise ValueError('照片质感调节需要 [批次, 高, 宽, 3或4] 的 RGB/RGBA 图像。')
    if mix == 0 or not any((exposure_ev, temperature, tint, highlights, shadows, grain_amount)):
        return images

    gains = [2 ** (temperature * 0.0035 + tint * 0.0015),
             2 ** (-tint * 0.0030),
             2 ** (-temperature * 0.0035 + tint * 0.0015)]
    normalization = sum(g * w for g, w in zip(gains, (0.2126, 0.7152, 0.0722)))
    gain = images.new_tensor([g / normalization for g in gains], dtype=torch.float32)
    weights = images.new_tensor([0.2126, 0.7152, 0.0722], dtype=torch.float32)
    result = torch.empty_like(images)
    for index, frame in enumerate(images):
        rgb = frame[..., :3].float()
        # Exposure and white-balance gains operate in linear light, before SDR clipping.
        linear = torch.where(rgb <= 0.04045, rgb / 12.92,
                             ((rgb + 0.055) / 1.055).clamp_min(0).pow(2.4))
        linear = linear * (2 ** exposure_ev) * gain
        luminance = (linear * weights).sum(dim=-1, keepdim=True)
        pivot = 0.35
        if shadows:
            shadow_weight = (1 - luminance / pivot).clamp(0, 1).square()
            linear = linear * torch.exp2(shadow_weight * (shadows * 0.008))
            luminance = (linear * weights).sum(dim=-1, keepdim=True)
        if highlights:
            above = (luminance - pivot).clamp_min(0)
            amount = abs(highlights) * 0.012
            if highlights < 0:
                target = luminance - amount * above.square() / (1 + amount * above)
            else:
                target = luminance + amount * above.square() / (1 + above)
            linear = linear * (target / luminance.clamp_min(1e-8))
        linear = linear.clamp(0, 1)
        adjusted = torch.where(linear <= 0.0031308, linear * 12.92,
                               1.055 * linear.pow(1 / 2.4) - 0.055)

        if grain_amount:
            height, width = rgb.shape[:2]
            generator = torch.Generator(device=images.device)
            generator.manual_seed((grain_seed + index) % (2 ** 63))
            noise = torch.randn((1, 1, math.ceil(height / grain_size), math.ceil(width / grain_size)),
                                generator=generator, device=images.device, dtype=torch.float32)
            if grain_size != 1:
                noise = F.interpolate(noise, size=(height, width), mode='bicubic', align_corners=False)
            brightness = (adjusted * weights).sum(dim=-1, keepdim=True)
            envelope = 0.35 + 2.6 * brightness * (1 - brightness)
            adjusted = adjusted + noise[0, 0, :, :, None] * (grain_amount / 100) * envelope

        result[index, ..., :3] = torch.lerp(rgb, adjusted.clamp(0, 1), mix).clamp(0, 1).to(images.dtype)
        if images.shape[-1] == 4:
            result[index, ..., 3] = frame[..., 3]
    return result
