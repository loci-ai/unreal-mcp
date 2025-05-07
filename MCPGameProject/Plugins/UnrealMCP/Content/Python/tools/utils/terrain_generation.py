import logging
import numpy as np

# from noise import pnoise2, snoise2

from .constants import HEIGHTMAP_PATH


logger = logging.getLogger("UnrealMCP")


def create_heightmap(
    width: int = 1009,
    height: int = 1009,
    base_scale: float = 250.0,
    base_octaves: int = 3,
    base_persistence: float = 0.4,
    base_lacunarity: float = 2.0,
    plateau_scale: float = 120.0,
    plateau_octaves: int = 4,
    plateau_threshold: float = 0.6,
    plateau_height: float = 0.8,
    plateau_softness: float = 0.15,
    plateau_flatness: float = 3.0,
    plateau_top_variation: float = 0.05,
    terracing_steps: int = 0,
    erosion_scale: float = 60.0,
    erosion_strength: float = 0.05,
    enable_mesa: bool = False,
    seed: int = 42,
):
    data = np.zeros((height, width), dtype=np.float32)

    for y in range(height):
        for x in range(width):
            nx = x / base_scale
            ny = y / base_scale
            px = x / plateau_scale
            py = y / plateau_scale
            ex = x / erosion_scale
            ey = y / erosion_scale

            # --- Base lowland terrain ---
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
            base = max(0.0, (base + 1) / 2.0 - 0.15)  # gently undulating, above 0

            # --- Plateau mask ---
            plateau_noise = pnoise2(
                px,
                py,
                octaves=plateau_octaves,
                persistence=0.5,
                lacunarity=2.0,
                repeatx=width,
                repeaty=height,
                base=seed + 100,
            )
            plateau_mask = (plateau_noise + 1) / 2.0

            plateau = 0.0
            if plateau_mask > plateau_threshold:
                # Blend plateau strength in softly
                t = min(1.0, (plateau_mask - plateau_threshold) / plateau_softness)
                t = t * t * (3 - 2 * t)  # smoothstep

                edge_margin = 0.1  # 10% border around the terrain
                fx = min(
                    x / (width * edge_margin),
                    (width - x - 1) / (width * edge_margin),
                    1.0,
                )
                fy = min(
                    y / (height * edge_margin),
                    (height - y - 1) / (height * edge_margin),
                    1.0,
                )
                edge_fade = min(fx, fy)

                plateau = t * plateau_height * edge_fade

                # Optional flat-top style (mesa banding)
                if plateau_flatness > 0:
                    plateau = round(plateau * plateau_flatness) / plateau_flatness

                # Small variation on plateau tops
                if plateau_top_variation > 0:
                    top_variation = snoise2(px * 2, py * 2, octaves=2, base=seed + 200)
                    top_variation = (top_variation + 1) / 2.0
                    plateau += top_variation * plateau_top_variation

            # --- Combine Base + Plateau ---
            if enable_mesa:
                total_height = max(base, plateau)  # plateaus replace base
            else:
                total_height = base + plateau  # plateaus blend into base

            # --- Optional terracing ---
            if terracing_steps > 0:
                step = 1.0 / terracing_steps
                total_height = np.floor(total_height / step + 0.5) * step

            # --- Optional erosion noise ---
            erosion = snoise2(ex, ey, octaves=2, base=seed + 500)
            erosion = (erosion + 1) / 2.0
            total_height += erosion_strength * erosion

            # --- Final clamp + write ---
            total_height = np.clip(total_height, 0.0, 1.0)
            data[y, x] = total_height

    data = data - np.min(data)
    data = ((data * 32767) + 32768).astype(np.uint16)

    logger.info(f"First 10 values of heightmap data: {data.flatten()[:10]}")
    logger.info("Minimum heightmap value: %d", data.min())
    logger.info("Maximum heightmap value: %d", data.max())

    path = HEIGHTMAP_PATH.as_posix()
    data.tofile(path)
    return path
