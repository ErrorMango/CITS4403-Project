"""A compact grassland fire cellular automaton model."""

from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

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


def simulate_fire_with_environment(
    initial_space: np.ndarray,
    max_steps: int = 100,
    ignition_probability: float = 0.5,
    wind_direction: Tuple[float, float] = (0.0, 0.0),
    terrain_slope: Optional[Union[float, np.ndarray]] = None,
    fuel_load: Optional[Union[float, np.ndarray]] = None,
    seed: Optional[int] = None,
) -> List[np.ndarray]:
    """Simulate fire using probability, wind, slope, and fuel effects."""
    if initial_space.ndim != 2:
        raise ValueError("initial_space must be a 2D array")
    if max_steps < 0:
        raise ValueError("max_steps cannot be negative")
    if not 0.0 <= ignition_probability <= 1.0:
        raise ValueError("ignition_probability must be between 0 and 1")
    if not np.all(np.isin(initial_space, (EMPTY, GRASS, BURNING, BURNED))):
        raise ValueError("initial_space contains an undefined cell state")

    shape = initial_space.shape
    if terrain_slope is None:
        slope_grid = np.zeros(shape, dtype=float)
    else:
        slope_value = np.asarray(terrain_slope, dtype=float)
        if slope_value.ndim == 0:
            slope_grid = np.full(shape, float(slope_value))
        elif slope_value.shape == shape:
            slope_grid = slope_value.copy()
        else:
            raise ValueError("terrain_slope must be a scalar or match the grid")
    if not np.all(np.isfinite(slope_grid)):
        raise ValueError("terrain_slope must contain finite values")
    if np.any((slope_grid < -1.0) | (slope_grid > 1.0)):
        raise ValueError("terrain_slope must be between -1 and 1")

    if fuel_load is None:
        fuel_grid = np.ones(shape, dtype=float)
    else:
        fuel_value = np.asarray(fuel_load, dtype=float)
        if fuel_value.ndim == 0:
            fuel_grid = np.full(shape, float(fuel_value))
        elif fuel_value.shape == shape:
            fuel_grid = fuel_value.copy()
        else:
            raise ValueError("fuel_load must be a scalar or match the grid")
    if not np.all(np.isfinite(fuel_grid)):
        raise ValueError("fuel_load must contain finite values")
    if np.any((fuel_grid < 0.0) | (fuel_grid > 1.0)):
        raise ValueError("fuel_load must be between 0 and 1")

    wind = np.asarray(wind_direction, dtype=float)
    if wind.shape != (2,):
        raise ValueError("wind_direction must contain row and column components")
    if not np.all(np.isfinite(wind)):
        raise ValueError("wind_direction must contain finite values")
    wind_strength = float(np.linalg.norm(wind))
    if wind_strength > 1.0:
        raise ValueError("wind_direction length cannot exceed 1")
    wind_unit = wind / wind_strength if wind_strength > 0 else wind

    rng = np.random.default_rng(seed)
    current = initial_space.copy()
    results: List[np.ndarray] = [current.copy()]

    for _ in range(max_steps):
        burning = current == BURNING
        if not np.any(burning):
            break

        padded = np.pad(burning, 1, mode="constant", constant_values=False)
        rows, columns = current.shape
        exposure = np.zeros(shape, dtype=float)

        # Weight each burning neighbor according to its alignment with the wind.
        for row_offset in range(3):
            for column_offset in range(3):
                if row_offset == 1 and column_offset == 1:
                    continue
                neighbor_fire = padded[
                    row_offset : row_offset + rows,
                    column_offset : column_offset + columns,
                ]
                offset = np.array(
                    [row_offset - 1, column_offset - 1], dtype=float
                )
                spread_direction = -offset / np.linalg.norm(offset)
                alignment = float(np.dot(spread_direction, wind_unit))
                exposure += neighbor_fire * (
                    1.0 + 0.5 * wind_strength * alignment
                )

        fire_probability = 1.0 - np.power(
            1.0 - ignition_probability,
            exposure,
        )
        fire_probability *= (1.0 + 0.5 * slope_grid) * fuel_grid
        fire_probability = np.clip(fire_probability, 0.0, 1.0)

        newly_burning = (current == GRASS) & (
            rng.random(shape) < fire_probability
        )
        next_space = current.copy()
        next_space[burning] = BURNED
        next_space[newly_burning] = BURNING
        current = next_space
        results.append(current.copy())

    return results


def store_results(
    results: List[np.ndarray],
    output_path: Union[str, Path] = "fire_results.npy",
) -> Path:
    """Stack all simulation states and save them as a NumPy file."""
    if not results:
        raise ValueError("results cannot be empty")
    first_shape = results[0].shape
    if any(state.ndim != 2 or state.shape != first_shape for state in results):
        raise ValueError("all result states must have the same 2D shape")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, np.stack(results, axis=0))
    return output_path


if __name__ == "__main__":
    grassland = generate_grassland(
        grid_shape=(50, 50),
        grass_probability=1.0,
        seed=42,
    )
    fire_space = generate_ignition_points(grassland)
    simulation_results = simulate_fire_with_environment(
        fire_space,
        max_steps=100,
        ignition_probability=0.55,
        wind_direction=(0.0, 0.8),
        terrain_slope=0.0,
        fuel_load=1.0,
        seed=42,
    )
    saved_path = store_results(simulation_results, "fire_results.npy")

    print(f"Simulation complete. Saved states: {len(simulation_results)}")
    print(f"Grid shape: {simulation_results[0].shape}")
    print(
        "Final burned cells: "
        f"{np.count_nonzero(simulation_results[-1] == BURNED)}"
    )
    print(f"Results saved to: {saved_path.resolve()}")
