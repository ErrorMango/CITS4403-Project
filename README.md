# CITS4403-Project
Shared repository for our CITS4403 group project.

# A Comparison of Fuel Break Layouts for Bushfire Control

Compare one wide fuel break with two narrow breaks of the same total area.
The experiment uses M1 and M2 fuel maps, real terrain, five wind settings,
three treated areas and 15 gaps. Results describe fire spread within 100 steps.

## Project files

```text
bushfire/
├── src/
│   ├── compare_100.py           # Run the experiment
│   └── model.py                 # Fire-spread rules
├── utils/
│   ├── io.py                    # Read maps and write data
│   ├── metrics.py               # Measure each run
│   ├── repeat_stats.py          # Means, SD and paired intervals
│   ├── animation.py             # Save animation data
│   ├── animation.html           # Play two layouts together
│   ├── compare_report.py        # Build the comparison page
│   ├── compare_charts.js        # Draw browser charts
│   ├── notebook_analysis.py     # Notebook plots and saved replay
│   └── test_model.py            # Model rule checks
├── data/
│   ├── maps/                    # M1, M2 and fuel-source information
│   ├── demo/                    # Small, portable copy of saved results
│   └── results/
│       └── M1_M2_100_r10_updated/ # Latest full experiment
├── notebooks/
│   ├── bushfire_report.ipynb    # 18-cell English demo
│   ├── bushfire_report.html     # Read-only demo copy
│   └── figures/                # Five plots and one replay GIF
├── requirements.txt
└── README.md
```

`.gitignore` excludes the local `.venv/`, caches and full `data/results/` directory.
Keep `data/demo/` when sharing the project: the notebook reads this portable bundle.
Do not upload the local Python environment. Old experiment outputs have been removed.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Open the demonstration

```bash
python -m jupyterlab notebooks/bushfire_report.ipynb
```

The notebook has saved outputs. Run All rebuilds its statistics, plots and replay
from existing data; it does not run new fire simulations. The HTML copy can be
opened directly in a browser. The demo takes about nine minutes.

Export the notebook again after editing it:

```bash
python -m jupyter nbconvert --to html notebooks/bushfire_report.ipynb
```

## Run a new experiment

```bash
python src/compare_100.py --plan-only
python src/compare_100.py --repeats 10 --seed 7 --out data/results/new_run
```

Choose a new output directory; existing results are not overwritten.
The default is one repeat. Ten repeats give 4,800 simulations:
2 maps × 5 winds × 3 areas × 16 layouts × 10 repeats.

- Treated area: 2%, 4%, 6%; treatment leaves 20% of the original fuel.
- First band starts at column 33. Single widths: 2, 4, 6 cells.
- Double widths: 1+1, 2+2, 3+3 cells; untreated gaps: 1–15 cells.
- Wind points toward none/E/S/W/N, not from that direction.
- Each repeat uses one positive-fuel ignition in columns 0–32.
- All layouts in a paired repeat share the ignition and spread seed.
- Different groups use different starts and seeds.

The CA uses eight neighbours, synchronous updates, p0=0.2, wind strength=0.5,
slope strength=1 and consumption=0.2 per burning cell per step.
Heights in metres are divided by 90 to preserve source-map slopes.

## Results and checks

The latest full page is `data/results/M1_M2_100_r10_updated/comparison.html`.
It shows synchronized first-repeat animations, mean curves, heatmaps and paired
confidence intervals. JSON files retain individual runs, summaries and settings.

Rebuild that page without running simulations:

```bash
python utils/compare_report.py data/results/M1_M2_100_r10_updated
```

Run the small model checks separately:

```bash
python -m unittest utils.test_model
```

Burned cells means all cells ever ignited, including cells still burning.
The protected region is columns 55–99. Fuel consumed excludes fuel removed by treatment.
Paired differences are double minus single; negative values favour double bands.
Intervals use 2,000 bootstrap resamples and are not adjusted for multiple comparisons.
SD measures variation between repeats; it is not a confidence interval.

## Data and limits

See [map notes](data/maps/README.md) and [demo data](data/demo/README.md).
Fuel values are literature-based proxies, not local measurements. Old map metadata
includes earlier fuel assignments; the current fuel CSV is the simulation input.
Original run hashes are retained as historical records; comment-only edits can change
source-file hashes without changing model behaviour.

Results stop at step 100 and do not prove permanent blocking. Map differences mix
fuel and terrain. Wind and area groups use different starts, so their differences
are not isolated causal effects. No untreated control or flying-ember mechanism is
included in this experiment.

Add both authors' names and real contributions before submission. The course's
separate written report requires at most five A4 pages of main text, 11-point font
and 1-inch margins. The demo notebook does not replace that format requirement.

## Report
The written report is submitted separately and is not included in this repository.

LaTeX sources, the report build script, source ZIP, extracted report text,
full simulation outputs and local caches are excluded by `.gitignore`.
They are not needed to run the model or notebook. When uploading through the
GitHub website, exclude these files manually; `.gitignore` does not filter uploads.
