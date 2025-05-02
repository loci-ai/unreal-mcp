import unreal
import numpy as np
from noise import pnoise2, snoise2

from .constants import HEIGHTMAP_PATH


def create_heightmap(
    width: int = 1009,
    height: int = 1009,
    base_scale: float = 250.0,
    base_octaves: int = 3,
    base_persistence: float = 0.4,
    base_lacunarity: float = 2.0,
    erosion_scale: float = 60.0,
    erosion_strength: float = 0.05,
    mountain_height_multiplier: float = 1.0,
    seed: int = 42,
):
    data = np.zeros((height, width), dtype=np.float32)

    for y in range(height):
        for x in range(width):
            nx = x / base_scale
            ny = y / base_scale
            ex = x / erosion_scale
            ey = y / erosion_scale

            # --- Base terrain ---
            base = pnoise2(
                nx,
                ny,
                octaves=base_octaves,
                persistence=base_persistence,
                lacunarity=base_lacunarity,
                repeatx=width,
                repeaty=height,
                base=seed,
            )
            base = max(0.0, (base + 1) / 2.0 - 0.15)

            # --- Amplify elevation ---
            base *= mountain_height_multiplier

            # --- Erosion noise ---
            erosion = snoise2(ex, ey, octaves=2, base=seed + 500)
            erosion = (erosion + 1) / 2.0
            total_height = base + erosion_strength * erosion

            # --- Final clamp ---
            data[y, x] = np.clip(total_height, 0.0, 1.0)

    data = data - np.min(data)
    data = ((data * 32767) + 32768).astype(np.uint16)

    unreal.log(f"First 10 values of heightmap data: {data.flatten()[:10]}")
    unreal.log("Minimum heightmap value: %d", data.min())
    unreal.log("Maximum heightmap value: %d", data.max())

    path = HEIGHTMAP_PATH.as_posix()
    data.tofile(path)
    return path
