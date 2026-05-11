# PyQtLabGraph Cleanup Roadmap

This file is the active handoff document for continuing the PyQtLabGraph
cleanup. It should describe current problems, why they matter, how to fix them,
and the recommended implementation order.

Repository source code, UI text, comments, and documentation should stay in
English. German is only used in direct conversation with the user.

## Current Project State

- `PyQtLabGraph` is an unpublished, still-evolving PySide6/PyQtGraph plotting
  library. Prefer clean current APIs over compatibility shims.
- The main package is `pyqt_lab_graph/`.
- `PyQtLabGraphWidget` owns behavior state, theme state, plot-style state,
  range behavior, and adaptive rendering. Curve data itself is delegated to the
  underlying PyQtGraph `PlotDataItem`.
- `PyQtLabGraphToolbar`, dialogs, and legend should emit user intents or edit
  widget-owned state through public widget methods. They should not duplicate
  behavior state.
- Themes and plot styles are intentionally separate:
  - Theme: PyQtLabGraph-owned plot content such as plot background and grid.
  - Plot style: curve appearance such as line color/width and marker settings.
- Axis label color, tick label color, axis lines, tick marks, plot frame chrome,
  toolbar chrome, legend chrome, dialogs, and menus follow the host Qt
  application style.
- Plot background and plot style selection now live in the modeless customize
  dialog and are previewed immediately.
- Layout persistence is implemented through `pyqt_lab_graph/layouts.py` and the
  widget-owned `load_layout(...)` / `save_layout(...)` API. Every
  `PyQtLabGraphWidget` now requires a stable code-defined `plot_identifier`.
- Layout files are explicit JSON with a schema version and a `plots` object,
  preserving entries for multiple plots in one application file.
- The plot widget stays transparent outside the pyqtgraph `ViewBox`; the
  `ViewBox` background is extended slightly to cover pyqtgraph right/bottom
  edge pixels.
- Runtime toolbar assets are explicit PNG files in `pyqt_lab_graph/assets/` and
  are listed explicitly in `pyproject.toml`.
- The standard verification command currently passes:

```bash
python3 tests/run_smoke_checks.py
```

The fresh independent review that produced this roadmap was completed on
2026-05-09 and recorded in `CLEANUP_DONE.md`.
The layout persistence implementation and session handoff were completed on
2026-05-10 and recorded in `CLEANUP_DONE.md`.

## Active Findings And Fixes

### P2: Multiple Modeless Customize Dialogs Can Race

Location:

- `pyqt_lab_graph/dialogs.py`, `show_customize_dialog(...)`.

Problem:

- The customize dialog is intentionally modeless so the main window remains
  usable while the dialog is open.
- Each open dialog stores the plot state that existed when that dialog was
  created and previews plot background/plot style changes immediately.
- If multiple customize dialogs are opened for the same plot, accepting or
  canceling them in a different order can apply or restore stale state.

Recommended fix:

- Enforce one customize dialog per `PyQtLabGraphWidget`.
- Store a single dialog reference on the widget, for example
  `_pyqt_lab_graph_customize_dialog`.
- If the dialog is already visible, raise and activate it instead of opening a
  second one. If a curve key was requested, switch to the relevant curve tab if
  present.
- Clear the reference from the dialog `finished` handler.
- Keep the existing Cancel restore behavior and live preview behavior.

### P3: Ignored Archive Artifacts Can Confuse Review

Location:

- `archive/` in the working tree.

Problem:

- `archive/` is ignored and not packaged, but it contains old icons and local
  exports that can show stale names such as the removed Pan asset.
- It is not a runtime packaging problem, but it can confuse manual review.

Recommended fix:

- Leave ignored archives alone unless cleanup is requested.
- If cleaned, move confusing artifacts to `bak/` rather than deleting them.

### P4: Performance Cleanup Should Stay Measurement-Driven

Location:

- `pyqt_lab_graph/widget.py`, `add_point(...)` and visible point counting.

Problem:

- `add_point(...)` reads current data from `PlotDataItem.getOriginalDataset()`,
  appends one point, and submits the full curve data back to PyQtGraph.
- Visible point counting reads original data from
  `PlotDataItem.getOriginalDataset()`.
- This keeps PyQtGraph as the data owner and avoids duplicate PyQtLabGraph data
  state, but it is still not optimized for high-frequency streaming.

Recommended fix:

- Do not prioritize performance rewrites now.
- If live high-frequency updates become a measured bottleneck, investigate
  batching, application-side buffering, or a dedicated streaming API before
  adding complex internal data structures.

### P4: Customize Dialog May Outgrow Manual Widget Wiring

Location:

- `pyqt_lab_graph/dialogs.py`, `show_customize_dialog(...)`.

Problem:

- The current hand-written `QFormLayout` dialog is still reasonable, but it is
  growing as more plot settings become editable.
- PyQtGraph `ParameterTree` is available and provides hierarchical parameter
  models, generated editors, and `saveState()` / `restoreState()`.
- ParameterTree state should not replace PyQtLabGraph's explicit layout file
  schema, because layout files need stable multi-plot keying, schema versioning,
  and curve-key behavior.

Recommended fix:

- Do not migrate immediately.
- If many more Customize settings are added, first introduce a small internal
  settings model/snapshot layer.
- Then evaluate rendering that model with PyQtGraph `ParameterTree` while
  keeping widget state ownership and layout persistence in PyQtLabGraph.

## Implementation Roadmap

### Phase 1: Stabilize Modeless Customize Dialog Ownership

Goal:

- Preserve the non-blocking dialog UX while avoiding stale preview/apply state.

Steps:

1. Add single-dialog ownership to `PyQtLabGraphWidget`/`show_customize_dialog`.
2. Reuse the existing open dialog on repeated toolbar or legend requests.
3. Keep live preview for plot background and plot style.
4. Add or extend smoke coverage for repeated dialog opens, Cancel, and Accept.

Expected result:

- The main window stays usable while Customize is open, and repeated Customize
  requests cannot restore or apply stale state.

### Phase 2: Optional Review-Only Cleanup

Goal:

- Reduce future reviewer confusion without touching runtime behavior.

Steps:

1. Inspect ignored `archive/` only if there is a specific cleanup goal.
2. Move confusing generated/export artifacts to `bak/` if requested.
3. Avoid destructive deletion unless explicitly requested.

Expected result:

- Active review surface is smaller, while backups remain available.

## Deferred Or Intentionally Not Planned

### Additional Smoke Tests

- No additional smoke tests are currently planned after the layout persistence
  smoke coverage added on 2026-05-10.
- The existing standalone smoke coverage is considered sufficient for the
  current cleanup stage:
  - syntax coverage for package, demos, and smoke scripts
  - adaptive performance behavior
  - axis formatting
  - customize dialog behavior
  - legend interaction
  - layout persistence, multi-plot file preservation, malformed file handling,
    and Customize `Apply + Save`
  - public API side effects and theme/plot-style separation
  - toolbar assets
  - toolbar interaction ownership
  - version metadata drift
- A package-build content test was considered but not added:
  - `python3 -m build` is not installed locally
  - adding build tooling or network installation is not needed for the current
    unpublished cleanup phase
  - `tests/smoke_toolbar_assets.py` already verifies explicit runtime PNG asset
    metadata in `pyproject.toml`

## Verification Commands

Run this after each cleanup step:

```bash
python3 tests/run_smoke_checks.py
```

Individual checks remain directly executable when isolating a failure:

```bash
python3 -m py_compile pyqt_lab_graph/*.py demo_thermostat.py demo_thermostat_qdarktheme.py demo_minimal.py tests/smoke_adaptive_performance.py tests/smoke_axis_formatting.py tests/smoke_customize_dialog.py tests/smoke_legend_interaction.py tests/smoke_layout_persistence.py tests/smoke_public_api_cleanup.py tests/smoke_toolbar_assets.py tests/smoke_toolbar_interaction.py tests/smoke_version_metadata.py tests/run_smoke_checks.py
QT_QPA_PLATFORM=offscreen python3 tests/smoke_adaptive_performance.py
QT_QPA_PLATFORM=offscreen python3 tests/smoke_axis_formatting.py
QT_QPA_PLATFORM=offscreen python3 tests/smoke_customize_dialog.py
QT_QPA_PLATFORM=offscreen python3 tests/smoke_legend_interaction.py
QT_QPA_PLATFORM=offscreen python3 tests/smoke_layout_persistence.py
QT_QPA_PLATFORM=offscreen python3 tests/smoke_public_api_cleanup.py
python3 tests/smoke_toolbar_assets.py
QT_QPA_PLATFORM=offscreen python3 tests/smoke_toolbar_interaction.py
python3 tests/smoke_version_metadata.py
```

Useful searches:

```bash
rg -n "demo\\.py|pyqt_lab_graph\\.theme|pyqt_lab_graph/theme\\.py|Pan|pan toolbar|rolling_window_seconds|get_current_x_window_seconds|set_rolling_window_seconds" -g '!bak/**' -g '!CLEANUP_DONE.md' -g '!CLEANUP_ROADMAP.md' .
rg -n "dict\\[str, object\\]|style\\[|style\\.get" pyqt_lab_graph
rg -n "using_theme_color|AutoPlotterWindow|setConfigOptions" pyqt_lab_graph demo_*.py
rg -n "PyQtLabGraphWidget\\(" README.md demo_*.py tests
rg -n "CLEANUP_ROADMAP|CLEANUP_DONE" README.md pyproject.toml pyqt_lab_graph demo_*.py tests
```

Expected current direction:

- No rolling-window seconds compatibility symbols.
- No dict-style curve style access in the library.
- No active `pyqt_lab_graph.theme` compatibility module.
- No Pan toolbar button.
- No host-application dark-mode detection.
- No theme-owned curve color behavior unless it is deliberately redesigned and
  tested.
- Every current `PyQtLabGraphWidget(...)` call should pass `plot_identifier`.
- Demo layout JSON files should remain ignored local runtime artifacts.

## Current Workspace Notes

- The repository may be in a dirty development state with many related changes
  pending. Do not revert unrelated changes.
- `AGENTS.md` is ignored by git in this repository, but local instructions may
  still matter.
- `demo.py` is deleted and replaced by `demo_thermostat.py`.
- `demo_minimal.py`, `themes.py`, `qt_styles.py`, and tests may be untracked
  depending on the current git index.
- `pyqt_lab_graph/layouts.py` and `tests/smoke_layout_persistence.py` were added
  for layout persistence.
- `AGENTS.md` and `bak/` are ignored by git, but both are used for local
  handoff and backups.
- Backups for major edits are written to `bak/`.
- Do not use destructive cleanup commands such as `rm` or destructive git
  commands without explicit user consent.
