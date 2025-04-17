import logging
import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.spatial import KDTree

from .constants import HEIGHTMAP_PATH

logger = logging.getLogger("UnrealMCP")


def generate_rock_locations(num_assets):
    return generate_asset_locations(
        num_assets=num_assets,
        min_distance=5.0,
        gradient_threshold=20.0,
        cluster_strength=20.0,
        height_influence=0.0,
    )


def generate_tree_locations(num_assets):
    return generate_asset_locations(
        num_assets=num_assets,
        min_distance=5.0,
        gradient_threshold=20.0,
        cluster_strength=10.0,
        height_influence=0.15,
    )


def generate_asset_locations(
    num_assets: int = 30,
    min_distance: float = 5.0,
    gradient_threshold: float = 10.0,
    cluster_strength: float = 2.0,
    height_influence: float = 1.0,
    max_z_jitter: float = 1.0,
) -> list:
    """
    Given a heightmap, returns (xy, z) tuples representing asset locations.

    Args:
        heightmap (np.ndarray): 2D array representing terrain heights.
        num_assets (int): Number of asset positions to generate.
        min_distance (float): Minimum allowed distance between assets.
        gradient_threshold (float): Max gradient allowed for asset placement.
        cluster_strength (float): Higher values create tighter clusters.
        height_influence (float): Controls how strongly height affects placement.
                                  0 = no height influence, 1 = strong preference for low areas.
        max_z_jitter (float): Maximum random amount to subtract from z (in height units).

    Returns:
        list of (x, y, z) tuples representing asset positions.
    """

    # Load heightmap
    heightmap = np.fromfile(HEIGHTMAP_PATH, dtype=np.uint16)
    heightmap = heightmap.reshape(1009, 1009)

    size_y, size_x = heightmap.shape
    assert size_y == size_x, "Heightmap must be square."
    size = size_y

    # Calculate gradient magnitude (steepness)
    gx, gy = np.gradient(heightmap)

    gradient_mag_scaling = 50
    grad_mag = np.clip(np.hypot(gx, gy) * gradient_mag_scaling, 0, 1)

    # Normalize height to [0, 1]
    norm_height = (heightmap - np.min(heightmap)) / (np.ptp(heightmap))

    # Height score: low areas score higher, based on influence
    height_score = (1 - norm_height) ** height_influence

    # Mask out high-gradient areas
    mask = grad_mag < gradient_threshold
    score = height_score * mask

    # Apply clustering
    smoothed = gaussian_filter(score, sigma=cluster_strength)

    # Flatten and normalize for sampling
    flat_scores = smoothed.ravel()
    if flat_scores.sum() == 0:
        raise ValueError(
            "All locations are masked out. Try increasing the gradient_threshold."
        )
    flat_scores /= flat_scores.sum()

    # Sample candidate positions with min-distance filtering
    candidates = []
    tree = KDTree(np.empty((0, 2)))

    for _ in range(num_assets * 10):  # oversample for better coverage
        idx = np.random.choice(len(flat_scores), p=flat_scores)
        y, x = divmod(idx, size)
        point = np.array([x, y])

        if len(candidates) == 0 or tree.query(point, k=1)[0] >= min_distance:
            candidates.append(point)
            tree = KDTree(np.array(candidates))
            if len(candidates) >= num_assets:
                break

    # Convert to (x, y, z) with negative jitter
    result = []
    for p in candidates:
        x, y = int(p[0]), int(p[1])
        z = heightmap[y, x]
        jitter = np.random.uniform(0, max_z_jitter)
        result.append([float(x), float(y), z - jitter])

    logger.info(f"Generated {len(result)} asset locations.")
    return result
