"""A basic grassland fire model with deterministic 8-neighbor spreading."""

from typing import List, Optional, Sequence, Tuple

import numpy as np


# Cell states
EMPTY = 0
GRASS = 1
BURNING = 2
BURNED = 3


def generate_grassland(
    grid_shape: Tuple[int, int] = (50, 50),
    grass_probability: float = 1.0,
    seed: Optional[int] = None,
) -> np.ndarray:
    """Create a full or randomly distributed grassland grid."""
    if len(grid_shape) != 2:
        raise ValueError("grid_shape must be provided as (rows, columns)")
    rows, columns = grid_shape
    if rows <= 0 or columns <= 0:
        raise ValueError("The number of rows and columns must be positive")
    if not 0.0 <= grass_probability <= 1.0:
        raise ValueError("grass_probability must be between 0 and 1")

    if grass_probability == 1.0:
        return np.full((rows, columns), GRASS, dtype=np.int8)

    rng = np.random.default_rng(seed)
    return np.where(
        rng.random((rows, columns)) < grass_probability,
        GRASS,
        EMPTY,
    ).astype(np.int8)


def generate_ignition_points(
    terrain: np.ndarray,
    ignition_points: Optional[Sequence[Tuple[int, int]]] = None,
) -> np.ndarray:
    """Add ignition points to a copy of the grassland grid."""
    if terrain.ndim != 2:
        raise ValueError("terrain must be a 2D array")
    if not np.all(np.isin(terrain, (EMPTY, GRASS))):
        raise ValueError("terrain may contain only EMPTY(0) and GRASS(1)")

    grass_positions = np.argwhere(terrain == GRASS)
    if len(grass_positions) == 0:
        raise ValueError("The terrain contains no grass cell that can be ignited")

    if ignition_points is None:
        center = np.array([terrain.shape[0] // 2, terrain.shape[1] // 2])
        distances = np.sum((grass_positions - center) ** 2, axis=1)
        selected_points = [tuple(grass_positions[np.argmin(distances)])]
    else:
        selected_points = list(ignition_points)
        if not selected_points:
            raise ValueError("ignition_points cannot be empty")

    initial_space = terrain.copy()
    for row, column in selected_points:
        if not (0 <= row < terrain.shape[0] and 0 <= column < terrain.shape[1]):
            raise ValueError(f"Ignition point {(row, column)} is outside the grid")
        if terrain[row, column] != GRASS:
            raise ValueError(f"Ignition point {(row, column)} must be on grass")
        initial_space[row, column] = BURNING

    return initial_space


def simulate_fire_8_neighbors(
    initial_space: np.ndarray,
    max_steps: int = 100,
) -> List[np.ndarray]:
    """Run an 8-neighbor fire simulation and return every grid state."""
    if initial_space.ndim != 2:
        raise ValueError("initial_space must be a 2D array")
    if max_steps < 0:
        raise ValueError("max_steps cannot be negative")
    if not np.all(np.isin(initial_space, (EMPTY, GRASS, BURNING, BURNED))):
        raise ValueError("initial_space contains an undefined cell state")

    current = initial_space.copy()
    results: List[np.ndarray] = [current.copy()]

    for _ in range(max_steps):
        burning = current == BURNING
        if not np.any(burning):
            break

        # Pad the grid, then use eight matrix slices to obtain Moore neighbors.
        padded = np.pad(
            burning,
            pad_width=1,
            mode="constant",
            constant_values=False,
        )
        rows, columns = current.shape
        adjacent_to_fire = np.zeros_like(burning)
        for row_offset in range(3):
            for column_offset in range(3):
                if row_offset == 1 and column_offset == 1:
                    continue
                adjacent_to_fire |= padded[
                    row_offset : row_offset + rows,
                    column_offset : column_offset + columns,
                ]

        next_space = current.copy()
        next_space[burning] = BURNED
        next_space[(current == GRASS) & adjacent_to_fire] = BURNING
        current = next_space
        results.append(current.copy())

    return results


if __name__ == "__main__":
    grassland = generate_grassland(
        grid_shape=(50, 50),
        grass_probability=1.0,
        seed=42,
    )
    fire_space = generate_ignition_points(grassland)
    simulation_results = simulate_fire_8_neighbors(fire_space, max_steps=100)

    print(f"Simulation complete. Saved states: {len(simulation_results)}")
    print(f"Grid shape: {simulation_results[0].shape}")
    print(
        "Final burned cells: "
        f"{np.count_nonzero(simulation_results[-1] == BURNED)}"
    )
