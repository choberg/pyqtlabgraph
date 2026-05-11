# PyQtLabGraph Completed Cleanup History

This file contains completed cleanup history moved out of `CLEANUP_ROADMAP.md`
so the roadmap can stay focused on current work. It is historical context, not a
fresh review checklist.

Repository source code, UI text, comments, and documentation should stay in
English. German is only used in direct conversation with the user.

## Completed Cleanup

### Layout Persistence And Session Handoff

- Added layout persistence on 2026-05-10.
- Public behavior:
  - every `PyQtLabGraphWidget` now requires a stable code-defined
    `plot_identifier`
  - layout persistence is opt-in through `layout_path` or explicit paths passed
    to `load_layout(...)` / `save_layout(...)`
  - host applications should create curves before calling `load_layout()` so
    curve visibility and styles can be mapped by curve key
- Added `pyqt_lab_graph/layouts.py` with an explicit JSON layout file schema:
  - top-level `version`
  - top-level `plots`
  - one preserved layout entry per plot identifier
- The Customize dialog now has an `Apply + Save` button. It applies current
  dialog values first, then saves this plot's layout without touching other plot
  entries in the same file.
- Layout smoke coverage verifies:
  - required plot identifiers
  - missing files and missing plot entries
  - malformed JSON errors
  - multi-plot file preservation
  - curve-key style/visibility loading
  - ignored unknown saved curve keys
  - Customize `Apply + Save`
- Updated demos and README usage examples with stable identifiers and explicit
  layout paths.
- Reviewed PyQtGraph `ParameterTree` for future Customize growth:
  - it is available and potentially useful as an internal editor/view layer
  - it should not replace PyQtLabGraph's stable layout file schema
- Session handoff cleanup on 2026-05-10:
  - updated `AGENTS.md`, `CLEANUP_ROADMAP.md`, and `.gitignore`
  - ignored generated `*.layout.json` demo artifacts
  - moved `demo_thermostat_qdarktheme.layout.json` to
    `bak/session_handoff_20260510/`
- Verification:
  - `python3 tests/run_smoke_checks.py`
- Backups made before handoff documentation edits:
  - `bak/session_handoff_20260510/AGENTS.md`
  - `bak/session_handoff_20260510/README.md`
  - `bak/session_handoff_20260510/CLEANUP_ROADMAP.md`
  - `bak/session_handoff_20260510/CLEANUP_DONE.md`
  - `bak/session_handoff_20260510/.gitignore`

### Documentation Refresh After Host-Styling And Customize Changes

- Refreshed `AGENTS.md`, `README.md`, and `CLEANUP_ROADMAP.md` on
  2026-05-09 so they match the current implementation.
- Updated documentation to describe:
  - modeless customize dialog behavior
  - live-preview plot background and plot style selection in the Global tab
  - host-styled customize dialog, plot frame chrome, toolbar chrome, legend
    chrome, menus, axes, ticks, and axis labels
  - transparent plot-widget chrome with a `ViewBox` background overdraw for the
    pyqtgraph right/bottom edge pixel issue
  - `demo_thermostat_qdarktheme.py` as an optional host-styling comparison demo
  - current smoke-check coverage and direct verification commands
- Added the remaining active roadmap item for single-dialog ownership now that
  Customize is modeless.
- Verification:
  - `python3 tests/run_smoke_checks.py`
- Backups made before implementation:
  - `bak/AGENTS.md.pre_docs_refresh_20260509`
  - `bak/README.md.pre_docs_refresh_20260509`
  - `bak/CLEANUP_ROADMAP.md.pre_docs_refresh_20260509`
  - `bak/CLEANUP_DONE.md.pre_docs_refresh_20260509`

### Modeless Customize Dialog

- Changed the customize dialog from modal `exec()` behavior to a modeless
  `show()` lifecycle on 2026-05-09.
- Rationale:
  - users should be able to keep the dialog open while interacting with the main
    plot window
  - plot background and plot style previews are more useful when the underlying
    plot remains visible and interactive
- The dialog now keeps itself alive through a widget-owned open-dialog list and
  removes itself from that list when finished.
- Accept applies the current form values. Reject/Cancel restores the plot theme,
  plot style, and curve styles that were active when the dialog opened.
- Smoke coverage verifies that the dialog is non-modal and that dialog
  references are cleaned up after close.
- Known follow-up:
  - multiple modeless customize dialogs for the same plot can still race through
    stale preview state; this is tracked in `CLEANUP_ROADMAP.md`.
- Verification:
  - `python3 tests/run_smoke_checks.py`
- Backups made before implementation:
  - `bak/dialogs.py.pre_modeless_customize_20260509`
  - `bak/smoke_customize_dialog.py.pre_modeless_customize_20260509`

### Plot Background And Plot Style In Customize Dialog

- Moved plot background and plot style selection into the customize dialog
  Global tab on 2026-05-09.
- Rationale:
  - the thermostat demos should not own special main-window controls for library
    plot configuration
  - users should find plot content styling together with axes, ranges, grid, and
    rendering settings
  - plot background and plot style changes should be visible immediately instead
    of requiring an extra Apply button
- Added Global-tab controls:
  - `Plot background:` for `light`, `dark`, `light-solarized`, and
    `dark-solarized`
  - `Plot style:` for `light`, `dark`, and `solarized`
- Removed the thermostat demo main-window theme combo and related code from
  both `demo_thermostat.py` and `demo_thermostat_qdarktheme.py`.
- Removed the old `Apply plot style` button from the dialog.
- Cancel restores previewed theme/style changes; OK keeps the selected values.
- Verification:
  - `python3 tests/run_smoke_checks.py`
- Backups made before implementation:
  - `bak/dialogs.py.pre_customize_theme_plot_style_20260509`
  - `bak/demo_thermostat.py.pre_customize_theme_plot_style_20260509`
  - `bak/demo_thermostat_qdarktheme.py.pre_customize_theme_plot_style_20260509`
  - `bak/maingui.ui.pre_customize_theme_plot_style_20260509`

### ViewBox Background Edge Fix

- Fixed the one-pixel dark line at the bottom/right edge of the plot data area
  on 2026-05-09.
- Root cause:
  - the plot widget chrome correctly stays transparent so the host application
    can style the outer frame
  - pyqtgraph's `ViewBox` background rectangle can leave a one-pixel uncovered
    strip at the right and bottom edge
  - data items can overpaint that strip, which made the issue appear
    intermittent during visual testing
- Fix:
  - kept `PlotWidget` background transparent
  - continued applying the selected PyQtLabGraph theme only to the `ViewBox`
    data area
  - extended the `ViewBox` background rectangle by a small named amount on
    resize and theme changes
- Verification:
  - offscreen pixel probe against the qdarktheme demo
  - `python3 tests/run_smoke_checks.py`
- Backups made before implementation:
  - `bak/widget.py.pre_viewbox_background_overdraw_20260509`
  - `bak/smoke_public_api_cleanup.py.pre_viewbox_background_overdraw_20260509`

### Solarized Theme Split And Host-Owned Axes

- Split the old single `solarized` plot-content theme into `light-solarized`
  and `dark-solarized` on 2026-05-09.
- Rationale:
  - Solarized has distinct light and dark backgrounds
  - the plot background and grid should follow the selected plot-content theme
    while axes, ticks, labels, and outer chrome follow the host Qt palette
- The `solarized` plot style remains as a curve-style palette.
- Axis label color, tick label color, axis lines, and tick marks now follow the
  host Qt palette instead of PyQtLabGraph plot themes.
- Verification:
  - `python3 tests/run_smoke_checks.py`

### Toolbar Host-Style Background Fix

- Made host stylesheet background painting explicit for toolbar chrome on
  2026-05-09.
- Rationale:
  - the toolbar and rolling menu no longer have PyQtLabGraph-owned colors, but
    custom Qt subclasses and embedded widgets may not always paint stylesheet
    backgrounds unless `WA_StyledBackground` is set
  - qdarktheme should control the actual colors for `QToolBar`, `QToolButton`,
    `QMenu`, and wrapper frames
- Set `WA_StyledBackground` on:
  - `PyQtLabGraphToolbar`
  - toolbar action buttons created through `QToolBar.widgetForAction(...)`
  - the rolling `QToolButton`
  - the rolling `QMenu`
- Did not set `WA_StyledBackground` on PyQtLabGraph wrapper frames, because
  qdarktheme's `QFrame` rule defines borders but not an explicit background.
- Offscreen qdarktheme probe after the change:
  - toolbar frame center pixel: `#333333`
  - toolbar center pixel: `#333333`
  - rolling menu center pixel: `#292a2d`
- Verification:
  - `python3 tests/run_smoke_checks.py`
- Backups made before implementation:
  - `bak/widget.py.pre_toolbar_styled_background_20260509`
  - `bak/toolbar.py.pre_toolbar_styled_background_20260509`
  - `bak/CLEANUP_DONE.md.pre_toolbar_styled_background_20260509`

### Transparent Embedded Toolbar Background

- Made the embedded toolbar background transparent on 2026-05-09.
- Rationale:
  - qdarktheme 0.1.7 styles `QToolBar` with `#333333`, which is visibly lighter
    than the normal widget background
  - PyQtLabGraph's toolbar is embedded inside a framed plot component, so the
    toolbar should let the host/frame background show through instead of
    painting its own bar color
- This is intentionally not a color theme. The toolbar still delegates button
  styling, menu styling, text, and icon palette colors to Qt/qdarktheme.
- Verification:
  - `python3 tests/run_smoke_checks.py`
- Backups made before implementation:
  - `bak/toolbar.py.pre_transparent_toolbar_bg_20260509`
  - `bak/CLEANUP_DONE.md.pre_transparent_toolbar_bg_20260509`

### Host-Styled Toolbar And Legend Chrome

- Moved toolbar chrome, toolbar menus, and legend chrome to host-application
  styling on 2026-05-09.
- Rationale:
  - host applications may use qdarktheme, qt-material, or their own Qt
    stylesheets
  - PyQtLabGraph should not force toolbar and legend widget chrome to follow the
    plot theme
  - plot themes should stay focused on plot-owned surfaces such as plot
    background and grid
- Removed PyQtLabGraph-owned toolbar/legend stylesheet rules from
  `pyqt_lab_graph/qt_styles.py`; later cleanup reduced it further to fallback
  frame styling and transparent plot-widget chrome.
- Removed chrome-only fields from `PyQtLabGraphTheme`, including toolbar icon
  color and legend disabled text.
- Toolbar icons remain packaged PNG masks, but they are recolored from the
  toolbar's current Qt palette and refreshed on palette/style changes.
- Legend text colors now come from the host Qt palette. Curve samples remain
  PyQtLabGraph-owned because they visualize curve styles.
- Updated README, AGENTS.md, the active roadmap, and toolbar interaction smoke
  coverage.
- Verification:
  - `python3 tests/run_smoke_checks.py`
- Backups made before implementation:
  - `bak/widget.py.pre_host_chrome_20260509`
  - `bak/toolbar.py.pre_host_chrome_20260509`
  - `bak/legend.py.pre_host_chrome_20260509`
  - `bak/qt_styles.py.pre_host_chrome_20260509`
  - `bak/themes.py.pre_host_chrome_20260509`
  - `bak/smoke_toolbar_interaction.py.pre_host_chrome_20260509`
  - `bak/README.md.pre_host_chrome_20260509`
  - `bak/AGENTS.md.pre_host_chrome_20260509`
  - `bak/CLEANUP_DONE.md.pre_host_chrome_20260509`
  - `bak/CLEANUP_ROADMAP.md.pre_host_chrome_20260509`

### Host-Styled Customize Dialog

- Removed PyQtLabGraph's dedicated customize-dialog stylesheet on 2026-05-09.
- Rationale:
  - host applications often use their own Qt styling, qdarktheme, or
    qt-material
  - the customize dialog should blend into the host application instead of
    forcing a PyQtLabGraph look
  - PyQtLabGraph themes should stay focused on plot-related surfaces
- Removed the unused `dialog_style(...)` helper from `pyqt_lab_graph/qt_styles.py`.
- Kept inline styling for curve color buttons, because those buttons need to
  show the selected color.
- Updated README, AGENTS.md, and the active roadmap to describe the new
  ownership boundary.
- Verification:
  - `python3 tests/run_smoke_checks.py`
- Backups made before implementation:
  - `bak/dialogs.py.pre_host_style_dialog_20260509`
  - `bak/qt_styles.py.pre_host_style_dialog_20260509`
  - `bak/README.md.pre_host_style_dialog_20260509`
  - `bak/CLEANUP_DONE.md.pre_host_style_dialog_20260509`
  - `bak/AGENTS.md.pre_host_style_dialog_20260509`

### Explicit pyqtgraph Escape-Hatches

- Added explicit pyqtgraph escape hatches on 2026-05-09.
- Public advanced-access API:
  - `PyQtLabGraphWidget.native_plot_widget`
  - `PyQtLabGraphWidget.native_plot_item`
  - `PyQtLabGraphWidget.native_view_box`
  - `PyQtLabGraphWidget.curve_item(key)`
- Rationale:
  - pyqtgraph users should be able to reach the underlying pyqtgraph objects
    when PyQtLabGraph does not wrap a specific configuration
  - direct access should be intentional and documented instead of relying on
    incidental attributes such as `.curves`
  - PyQtLabGraph still owns theme, plot-style, range, axis, grid, and adaptive
    rendering state
- Updated README and the public API smoke check.
- Verification:
  - `python3 tests/run_smoke_checks.py`
- Backups made before implementation:
  - `bak/widget.py.pre_pyqtgraph_escape_hatches_20260509`
  - `bak/README.md.pre_pyqtgraph_escape_hatches_20260509`
  - `bak/smoke_public_api_cleanup.py.pre_pyqtgraph_escape_hatches_20260509`
  - `bak/CLEANUP_DONE.md.pre_pyqtgraph_escape_hatches_20260509`
  - `bak/CLEANUP_ROADMAP.md.pre_pyqtgraph_escape_hatches_20260509`

### Show All Toolbar Rename

- Renamed the toolbar's former `Home` command to `Show All` on 2026-05-09.
- Rationale:
  - the action fits all visible curves on both axes
  - `Show All` describes the behavior better than `Home`
- Updated current code names from `home` to `show_all`:
  - toolbar action: `show_all_action`
  - toolbar callback: `on_show_all_requested`
  - widget method: `request_show_all()`
- Updated README, AGENTS.md, and smoke checks to use the new name.
- Verification:
  - `python3 tests/run_smoke_checks.py`
- Backups made before implementation:
  - `bak/toolbar.py.pre_show_all_rename_20260509`
  - `bak/widget.py.pre_show_all_rename_20260509`
  - `bak/README.md.pre_show_all_rename_20260509`
  - `bak/AGENTS.md.pre_show_all_rename_20260509`
  - `bak/smoke_toolbar_interaction.py.pre_show_all_rename_20260509`
  - `bak/smoke_public_api_cleanup.py.pre_show_all_rename_20260509`
  - `bak/CLEANUP_DONE.md.pre_show_all_rename_20260509`

### Original Dataset Autoscale Fix

- Fixed an autoscale/Show All regression after adding dense data while
  clip-to-view/downsampling is enabled.
- Root cause:
  - the pyqtgraph-native data ownership cleanup used `PlotDataItem.getData()`
    for PyQtLabGraph's internal reads
  - pyqtgraph documents `getData()` as the data displayed on screen after
    mapping and data reduction
  - with a narrow current X range, autoscale and Show All could therefore see only
    the currently displayed subset until the user manually zoomed out
- Fix:
  - internal curve reads now use `PlotDataItem.getOriginalDataset()`
  - `curve_data(...)`, autoscale, rolling ranges, and adaptive rendering now use
    the full original dataset while still avoiding duplicate PyQtLabGraph X/Y
    storage
  - README wording now says `curve_data(...)` reads original curve data
- Verification:
  - extended the existing public API smoke check so a clipped 10,000-point curve
    still returns the full original dataset and `request_show_all()` shows
    `0..10000`
  - `python3 tests/run_smoke_checks.py`
- Backups made before implementation:
  - `bak/widget.py.pre_original_dataset_fix_20260509`
  - `bak/README.md.pre_original_dataset_fix_20260509`
  - `bak/smoke_public_api_cleanup.py.pre_original_dataset_fix_20260509`
  - `bak/CLEANUP_DONE.md.pre_original_dataset_fix_20260509`

### Thermostat Bulk Insert Gap Fix

- Fixed a demo-specific gap that could appear when clicking `+10000 points`
  repeatedly in `demo_thermostat.py`.
- Root cause:
  - bulk insertion started from `get_current_elapsed_seconds()`, which follows
    the demo clock rather than the last plotted X value
  - when rendering or queued UI work delayed the next click, the clock could
    advance beyond the last plotted point and create an empty X-range before
    the next generated block
- Fix:
  - bulk insertion now starts from the latest plotted X value read through
    `PyQtLabGraphWidget.curve_data(...)`
  - the new arrays are appended with NumPy and passed through `set_data(...)`
  - live acquisition state is still advanced to the end of the inserted block
- Verification:
  - `python3 tests/run_smoke_checks.py`
- Backups made before implementation:
  - `bak/demo_thermostat.py.pre_bulk_gap_fix_20260509`
  - `bak/CLEANUP_DONE.md.pre_bulk_gap_fix_20260509`

### PyQtGraph-Native Data Ownership

- Completed the pyqtgraph-style data API cleanup on 2026-05-09.
- Removed duplicate X/Y data storage from `CurveState`; PyQtLabGraph now treats
  the underlying `pyqtgraph.PlotDataItem` as the curve data owner.
- Added `PyQtLabGraphWidget.set_data(key, *args, **kwargs)` as the main data
  replacement API. It forwards pyqtgraph-compatible data arguments to
  `PlotDataItem.setData(...)`.
- Added `PyQtLabGraphWidget.plot(key, *args, label=None, color=None, style=None, **kwargs)`
  as a convenience wrapper that creates a named curve and sets its data.
- `curve_data(...)` now reads arrays from PyQtGraph-owned curve data.
- `add_point(...)`, autoscale, rolling X range, visible Y extraction, and
  adaptive rendering now read data from PyQtGraph instead of from PyQtLabGraph
  side lists.
- Updated README, demos, and smoke checks to use `plot(...)` / `set_data(...)`
  instead of the removed `set_curve_data(...)` API.
- Rationale:
  - the project is unreleased, so no compatibility shim was needed
  - pyqtgraph users should recognize the accepted data forms
  - NumPy arrays can pass through without forced list conversion
  - PyQtLabGraph should wrap behavior and styling, not duplicate pyqtgraph's
    data ownership
- Verification:
  - `python3 tests/run_smoke_checks.py`
  - Result: all smoke checks passed.
- Backups made before implementation:
  - `bak/models.py.pre_pyqtgraph_data_api_20260509`
  - `bak/widget.py.pre_pyqtgraph_data_api_20260509`
  - `bak/README.md.pre_pyqtgraph_data_api_20260509`
  - `bak/demo_minimal.py.pre_pyqtgraph_data_api_20260509`
  - `bak/demo_thermostat.py.pre_pyqtgraph_data_api_20260509`
  - `bak/smoke_adaptive_performance.py.pre_pyqtgraph_data_api_20260509`
  - `bak/smoke_customize_dialog.py.pre_pyqtgraph_data_api_20260509`
  - `bak/smoke_legend_interaction.py.pre_pyqtgraph_data_api_20260509`
  - `bak/smoke_public_api_cleanup.py.pre_pyqtgraph_data_api_20260509`
  - `bak/CLEANUP_ROADMAP.md.pre_pyqtgraph_data_api_20260509`
  - `bak/CLEANUP_DONE.md.pre_pyqtgraph_data_api_20260509`
  - `bak/AGENTS.md.pre_pyqtgraph_data_api_20260509`

### Test Roadmap Closure

- Completed the test roadmap closure decision on 2026-05-09.
- Decided not to add more smoke tests for the current cleanup stage.
- Moved the optional package-build smoke check out of the active implementation
  roadmap.
- Rationale:
  - `python3 -m build` is not installed locally.
  - Adding build tooling or a network/install step is unnecessary for the
    current unpublished cleanup stage.
  - Existing smoke coverage now checks syntax, adaptive performance, axis
    formatting, customize dialog behavior, legend interaction, public API side
    effects, toolbar assets, toolbar interaction ownership, and version metadata
    drift.
  - Runtime PNG asset metadata is already checked statically by
    `tests/smoke_toolbar_assets.py`.
- Verification:
  - `python3 tests/run_smoke_checks.py`
  - Result: all smoke checks passed.
- Backups made before implementation:
  - `bak/CLEANUP_ROADMAP.md.pre_close_test_roadmap_20260509`
  - `bak/CLEANUP_DONE.md.pre_close_test_roadmap_20260509`

### Legend Interaction Smoke Coverage

- Completed the legend interaction smoke coverage cleanup on 2026-05-09.
- Added `tests/smoke_legend_interaction.py` and registered it in
  `tests/run_smoke_checks.py`.
- The new smoke test verifies:
  - clicking a `PyQtLabGraphLegendItem` toggles curve visibility through the
    widget-owned `set_curve_visible(...)` path
  - the widget curve state and PyQtGraph curve item visibility stay synchronized
  - the legend sample refreshes its visible/hidden opacity state
  - double-clicking a legend item calls `PyQtLabGraphWidget.show_customize_dialog(...)`
    with the selected curve key
  - a legend double-click does not also toggle curve visibility after the click
    delay expires
- Verification:
  - `python3 tests/run_smoke_checks.py`
  - Result: all smoke checks passed.
- Backups made before implementation:
  - `bak/run_smoke_checks.py.pre_legend_smoke_20260509`
  - `bak/CLEANUP_ROADMAP.md.pre_legend_smoke_20260509`
  - `bak/CLEANUP_DONE.md.pre_legend_smoke_20260509`

### Documentation And Version Metadata

- Completed the documentation and version metadata cleanup on 2026-05-09.
- Removed internal cleanup-history files from the user-facing README project
  structure:
  - `CLEANUP_ROADMAP.md`
  - `CLEANUP_DONE.md`
- Kept the README focused on package usage, demos, tests, runtime assets, and
  packaging metadata.
- Removed the hard-coded duplicate version string from
  `pyqt_lab_graph/__init__.py`.
- `pyproject.toml` remains the release metadata source.
- Runtime version resolution now uses:
  - installed package metadata through `importlib.metadata.version("pyqt-lab-graph")`
  - a source-tree fallback that reads the project version from `pyproject.toml`
- Added `tests/smoke_version_metadata.py` and registered it in
  `tests/run_smoke_checks.py`.
- The new smoke test verifies `pyqt_lab_graph.__version__` matches the
  `pyproject.toml` project version.
- Checked optional build smoke feasibility:
  - `python3 -m build --version`
  - Result: the `build` module is not installed locally, so no build-content
    smoke check was added.
- Verification:
  - `python3 tests/run_smoke_checks.py`
  - Result: all smoke checks passed.
- Backups made before implementation:
  - `bak/README.md.pre_docs_packaging_20260509`
  - `bak/__init__.py.pre_docs_packaging_20260509`
  - `bak/run_smoke_checks.py.pre_docs_packaging_20260509`
  - `bak/CLEANUP_ROADMAP.md.pre_docs_packaging_20260509`
  - `bak/CLEANUP_DONE.md.pre_docs_packaging_20260509`

### Public API Side Effects And Stale State

- Completed the public API side-effect cleanup on 2026-05-09.
- Removed import-time `pg.setConfigOptions(antialias=True)` from
  `pyqt_lab_graph/__init__.py`.
- Package import no longer changes the host process' global PyQtGraph
  antialiasing configuration.
- Removed dead theme-owned curve color state:
  - deleted `CurveState.using_theme_color`
  - removed `set_curve_style(...)` and `apply_plot_style(...)` assignments to
    that flag
  - removed the `set_theme(...)` branch that could recolor curves through the
    theme path
- Theme changes now only reapply existing curve styles; plot styles remain the
  only built-in mechanism for changing curve appearance.
- Removed stale `AutoPlotterWindow = ThermostatDemoWindow` from
  `demo_thermostat.py`.
- Added `tests/smoke_public_api_cleanup.py` and registered it in
  `tests/run_smoke_checks.py`.
- The new smoke test verifies:
  - importing `pyqt_lab_graph` does not change `pg.getConfigOption("antialias")`
  - changing themes does not alter an existing curve's `CurveStyle`
- Stale-reference searches were run:
  - `using_theme_color` and `AutoPlotterWindow` no longer appear outside backups
  - `setConfigOptions` only appears in the smoke test that controls PyQtGraph's
    pre-import baseline
  - `Pan` matches only PyQtGraph `PanMode`, not a toolbar button
- Verification:
  - `python3 tests/run_smoke_checks.py`
  - Result: all smoke checks passed.
- Backups made before implementation:
  - `bak/__init__.py.pre_public_api_cleanup_20260509`
  - `bak/models.py.pre_public_api_cleanup_20260509`
  - `bak/widget.py.pre_public_api_cleanup_20260509`
  - `bak/demo_thermostat.py.pre_public_api_cleanup_20260509`
  - `bak/run_smoke_checks.py.pre_public_api_cleanup_20260509`

### Toolbar Behavior Ownership Refactor

- Completed the toolbar ownership cleanup on 2026-05-09.
- Moved X/Y span zoom event filters out of `PyQtLabGraphToolbar` and into
  widget-owned `_AxisSpanZoomFilter` instances in `pyqt_lab_graph/widget.py`.
- Moved `ViewBox` mouse-mode switching into `PyQtLabGraphWidget` through
  `_apply_interaction_behavior(...)`.
- Kept rectangle zoom selection styling in the widget and reuse it whenever
  rectangle zoom mode is activated.
- Moved save/export behavior out of the toolbar:
  - `PyQtLabGraphToolbar` now emits `on_save_requested`.
  - `PyQtLabGraphWidget.save_figure(...)` owns the file dialog and
    `ImageExporter` call.
- `PyQtLabGraphToolbar.sync_state(...)` now only mirrors interaction state into
  action/button check states.
- Added `tests/smoke_toolbar_interaction.py` and registered it in
  `tests/run_smoke_checks.py`.
- The new smoke test verifies toolbar actions through widget-owned state and
  behavior:
  - rectangle zoom switches the widget `ViewBox` to rect mode
  - X/Y zoom enable widget-owned span filters
  - save is emitted as a toolbar intent
  - the reset/show-all action restores default interaction state
  - toolbar no longer stores `plot_widget`, `x_span_filter`, or `y_span_filter`
- Verification:
  - `python3 tests/run_smoke_checks.py`
  - Result: all smoke checks passed.
- Backups made before implementation:
  - `bak/toolbar.py.pre_toolbar_refactor_20260509`
  - `bak/widget.py.pre_toolbar_refactor_20260509`
  - `bak/run_smoke_checks.py.pre_toolbar_refactor_20260509`

### Customize Dialog Data Loss And Empty-Plot Editing

- Completed Phase 1 of `CLEANUP_ROADMAP.md` on 2026-05-09.
- Added X/Y unit controls to the customize dialog Global tab:
  - `pyqtLabGraphXUnitsEdit`
  - `pyqtLabGraphYUnitsEdit`
- The OK handler now passes `x_units` and `y_units` to
  `PyQtLabGraphWidget.set_axis_labels(...)`.
- Empty unit fields are normalized to `None`, matching the existing widget state
  model.
- Removed the early return that prevented opening the customize dialog before
  any curves were added.
- The dialog now always shows the Global tab. Curve tabs are only created when
  curves exist, and a missing `curve_key` leaves the Global tab selected.
- Extended `tests/smoke_customize_dialog.py` to cover:
  - editing axis units through the dialog
  - preserving the intended unit state after accepting
  - opening and accepting the dialog with no curves
  - applying global settings before data exists
- Verification:
  - `python3 tests/run_smoke_checks.py`
  - Result: all smoke checks passed.
- Backups made before implementation:
  - `bak/dialogs.py.pre_phase1_20260509`
  - `bak/smoke_customize_dialog.py.pre_phase1_20260509`

### Fresh Independent Cleanup And Architecture Review

- Completed a read-only fresh review of the active repository on 2026-05-09
  before reading cleanup history.
- The review intentionally skipped `CLEANUP_ROADMAP.md`, `CLEANUP_DONE.md`, and
  `bak/` to avoid bias from prior cleanup work.
- Verification during the review:
  - `python3 tests/run_smoke_checks.py`
  - Result: all smoke checks passed.
- Confirmed active code no longer has obvious stale references to:
  - `demo.py`
  - `pyqt_lab_graph.theme`
  - dict-style curve style access
  - rolling-window seconds compatibility aliases
  - a Pan toolbar button
- Confirmed runtime toolbar assets in `pyqt_lab_graph/assets/` are aligned with
  `pyproject.toml` package data and `tests/smoke_toolbar_assets.py`.
- Confirmed several items are intentional and should not be forced into cleanup:
  - `matplotlibContainer` remains a Qt Designer object name for demo UI
    compatibility.
  - adaptive rendering/performance remains an intentional PyQtLabGraph feature.
  - the simple visible-point scan should stay until profiling shows a real
    bottleneck.
- Findings from the review were moved into `CLEANUP_ROADMAP.md` as active work:
  - customize dialog drops axis units
  - customize dialog cannot edit global settings before curves exist
  - toolbar still owns plot behavior such as span zoom, mouse mode, and export
  - package import mutates global PyQtGraph antialias configuration
  - dead `using_theme_color` state blurs theme/plot-style separation
  - stale `AutoPlotterWindow` demo alias
  - README exposes cleanup-history files as user-facing project structure
  - duplicated version metadata
  - smoke coverage gaps around likely regressions
  - ignored archive artifacts may confuse review but are not runtime packaging
    issues
- Backups made before updating the cleanup documents:
  - `bak/CLEANUP_ROADMAP.md.pre_fresh_review_20260509_104808`
  - `bak/CLEANUP_DONE.md.pre_fresh_review_20260509_104808`

### Theme And QSS

- Removed system dark-mode detection from the library.
- Added named built-in themes: `light`, `dark`, and `solarized`.
- `PyQtLabGraphWidget.set_theme(...)` is the theme entry point.
- Theme changes are scoped to PyQtLabGraph-owned widgets.
- `PyQtLabGraphTheme` no longer has host-app background fields.
- `panel_background` was renamed to `surface_background`.
- QSS selectors in `qt_styles.py` are scoped with PyQtLabGraph object names:
  - `pyqtLabGraphPlotWidget`
  - `pyqtLabGraphPlotFrame`
  - `pyqtLabGraphToolbarFrame`
  - `pyqtLabGraphLegendFrame`
  - `pyqtLabGraphToolbar`
  - `pyqtLabGraphRollingButton`
  - `pyqtLabGraphRollingMenu`
  - `pyqtLabGraphLegend`
  - `pyqtLabGraphCustomizeDialog`
- Host-provided containers such as `toolbarContainer` and `legendContainer` are
  no longer styled by the library.

### Plot Styles And Curve Styles

- Added typed `CurveStyle`.
- `CurveState.style` now stores `CurveStyle`, not `dict[str, object]`.
- Public curve style API now uses typed styles:
  - `add_curve(..., style=CurveStyle(...))`
  - `set_curve_style(key, CurveStyle(...))`
  - `curve_style(key) -> CurveStyle`
- Removed dict-style compatibility. Do not reintroduce it unless there is a real
  in-repo reason.
- Added built-in plot styles: `light`, `dark`, and `solarized`.
- Built-in plot styles produce open square markers by default with:
  - line width `1.0`
  - marker outline width `1.0`
  - marker size `5`
- The customize dialog can apply a built-in plot style to existing curve editors
  via an explicit Apply button.

### Toolbar And Interaction State

- Removed the Pan button. Mouse panning is the default PyQtGraph interaction.
- Added `InteractionTool` and `InteractionState` in `models.py`.
- `PyQtLabGraphWidget` owns interaction state:
  - `autoscale_x`
  - `autoscale_y`
  - `rolling_x`
  - `active_tool`
- `PyQtLabGraphToolbar` now emits user intents and mirrors widget state through
  `sync_state(...)`.
- Old rolling-window seconds compatibility aliases were removed:
  - no `rolling_window_seconds`
  - no `set_rolling_window_seconds`
  - no `get_current_x_window_seconds`
  - no toolbar `get_current_x_window_seconds`
- Toolbar behavior after refactor:
  - the reset/show-all action resets to autoscale X/Y enabled, rolling
    disabled, no active tool.
  - Rolling X disables autoscale X.
  - Rectangle/X/Y zoom disables autoscale X/Y and rolling.
  - X/Y zoom remain active until the user toggles them off or another
    tool/reset action replaces them.
  - Manual navigation disables autoscale X/Y and rolling but does not force-clear
    the currently active tool.

### Zoom And Selection Behavior

- X/Y zoom selection is constrained to the plot area.
- X/Y zoom uses a `QRubberBand` over the plot rect.
- Rectangle zoom selection color was aligned to the X/Y zoom color.
- Rectangle zoom selection styling is reapplied after zoom reset/show-all so it
  does not fall back to PyQtGraph's default yellow.

### Customize Dialog

- Added per-curve visibility checkbox.
- Antialiasing now applies to markers as well as lines.
- Added marker outline width for open markers.
- Plot style application was explicit via an Apply button at this stage. Later
  cleanup moved plot style selection to immediate preview in the Global tab.
- Dialog styles were scoped through `pyqtLabGraphCustomizeDialog` at this stage.
  Later cleanup removed the dedicated dialog stylesheet so host Qt styling owns
  the dialog chrome.

### Demos And Documentation

- Added `demo_minimal.py` as a readable minimal example.
- Renamed `demo.py` to `demo_thermostat.py`.
- Translated demo/documentation-facing text to English.
- The thermostat demo explicitly let the user choose PyQtLabGraph themes at
  this stage. Later cleanup moved plot background selection into the customize
  dialog and removed the main-window theme combo.
- The demo does not theme the surrounding host application UI.
- `demo_minimal.py` uses explicit beginner-friendly axis labels.
- README examples state that domain-specific axis labels should be set
  explicitly by the embedding application.

### Library Defaults

- Removed thermostat-specific axis defaults from `PyQtLabGraphWidget`.
- The widget now starts with neutral labels:
  - X label `"X"`
  - Y label `"Y"`
  - no default units
- The explicit empty-widget start range is now neutral:
  - X range `0.0 .. 1.0`
  - Y range `0.0 .. 1.0`
- `_setup_plot()` now uses the widget's current label state instead of hard-coded
  thermostat labels.
- Thermostat-specific labels remain in `demo_thermostat.py`, where they belong.

### Zoom Selection Styling

- Removed `AXIS_ZOOM_COLOR_BY_AXIS` from `styles.py`.
- Zoom selection color is now a single shared interaction color in `themes.py`:
  - `ZOOM_SELECTION_COLOR`
  - `ZOOM_SELECTION_FILL_ALPHA`
  - `ZOOM_SELECTION_BORDER_ALPHA`
- Rectangle zoom and X/Y axis zoom use the same selection color.
- The previous Y-axis-specific color was not used for the actual selection
  boxes; removing the map matches the visible behavior.
- This is intentionally not fully theme-dependent yet. A later theme cleanup can
  move these constants into `PyQtLabGraphTheme` fields together with axis label
  and tick styling.

### Widget Magic Numbers

- Named the central hard-coded values in `pyqt_lab_graph/widget.py` as private
  module constants without changing behavior.
- Covered values include:
  - neutral initial X/Y ranges
  - adaptive performance activation/restore thresholds
  - plot layout margins
  - primary and secondary axis tick geometry
  - fixed bottom/left axis sizes
  - axis label margins
  - grid z-order and pen width
  - range padding
  - rectangle zoom selection border width
  - plot/toolbar/legend frame margins
  - embedded container margins and layout spacing
  - X autoscale lower bound and rolling-window lower bound
  - Y autoscale margin behavior
- This is intentionally private configuration. No public settings object was
  introduced because these values are still implementation details.
- Verification after the change:
  - `python3 -m py_compile pyqt_lab_graph/*.py demo_thermostat.py demo_minimal.py`
  - Offscreen smoke test creating a widget with toolbar/legend, setting curve
    data, switching X/Y/rectangle zoom tools, and resetting the full view.

### Toolbar Magic Numbers

- Named the local hard-coded values in `pyqt_lab_graph/toolbar.py` as private
  module constants without changing behavior.
- Covered values include:
  - toolbar icon size
  - zoom selection border width
  - custom rolling-window spin-box minimum, maximum, decimals, and default
  - fixed rolling-window presets and their menu labels
  - generated fallback X/Y zoom icon size, rectangles, points, pen widths, and
    label font size
- Long action-construction and painter calls were wrapped while preserving the
  existing control flow.
- This is still private implementation detail. The toolbar does not expose a
  public appearance/configuration object.
- Verification after the change:
  - `python3 -m py_compile pyqt_lab_graph/*.py demo_thermostat.py demo_minimal.py`
  - Offscreen smoke test creating a widget with toolbar/legend, checking toolbar
    icon size and rubber-band style, switching X/Y/rectangle zoom tools, applying
    a rolling-window preset, and resetting the full view.

### Legend Magic Numbers

- Named the local hard-coded values in `pyqt_lab_graph/legend.py` as private
  module constants without changing behavior.
- Covered values include:
  - outer legend layout margins and spacing
  - vertical stretch factor
  - legend-item click delay
  - legend-item margins, spacing, border radius, hover color, and visible/hidden
    opacity
  - curve sample widget width/height
  - sample minimum marker size, line inset, centering divisor, and filled-marker
    outline width
- Replaced the inline vertical/horizontal layout ternary with a short `if` block
  for readability.
- Verification after the change:
  - `python3 -m py_compile pyqt_lab_graph/*.py demo_thermostat.py demo_minimal.py`
  - Offscreen smoke test creating a widget with toolbar/legend, checking legend
    sample size and click delay, changing theme, toggling curve visibility, and
    checking visible/hidden opacity.

### Dialog Magic Numbers

- Named the local hard-coded values in `pyqt_lab_graph/dialogs.py` as private
  module constants without changing behavior.
- Covered values include:
  - customize dialog default size
  - line-width editor minimum, maximum, decimals, and step
  - marker-size editor minimum and maximum
  - marker-outline-width editor minimum, maximum, decimals, and step
  - manual X/Y range editor minimum, maximum, and decimals
  - compact helper-row layout margins
  - color-button text contrast threshold, border width, border radius, and
    padding
- Added small helper functions for repeated spin-box configuration:
  - `_configure_line_width_spin_box(...)`
  - `_configure_marker_outline_width_spin_box(...)`
- This is intentionally private dialog implementation detail. No public dialog
  configuration object was introduced.
- Verification after the change:
  - `python3 -m py_compile pyqt_lab_graph/*.py demo_thermostat.py demo_minimal.py`
  - Offscreen smoke test creating a widget with toolbar/legend, adding a curve,
    opening the customize dialog non-interactively, checking dialog size,
    spin-box ranges, row margins, curve editor controls, and color-button
    contrast styling.

### Toolbar Assets And Package Data

- Kept the active toolbar asset format as PNG.
- Cleaned `pyqt_lab_graph/assets/` so it contains only toolbar PNG assets that
  are referenced by `pyqt_lab_graph/toolbar.py` and packaged by `pyproject.toml`:
  - `autox.png`
  - `autoy.png`
  - `edit_params.png`
  - `reset_zoom.png`
  - `rolling.png`
  - `saveplot.png`
  - `x-zoom.png`
  - `y-zoom.png`
  - `zoom_area.png`
- Replaced the active `x-zoom.png` and `y-zoom.png` files, which contained SVG
  XML despite their `.png` extension, with the existing real PNG versions from
  `x-zoom_old.png` and `y-zoom_old.png`.
- Moved SVG source/original files out of package assets and into
  `original_icons/toolbar/`:
  - `x-zoom.svg`
  - `y-zoom.svg`
  - `x-zoom.active-misnamed.svg`
  - `y-zoom.active-misnamed.svg`
- Moved unused PNG assets to `bak/unused_assets/` instead of deleting them:
  - `pan.png`
  - `check_dark.png`
  - `check_light.png`
  - `spin_down_dark.png`
  - `spin_down_light.png`
  - `spin_up_dark.png`
  - `spin_up_light.png`
- Removed `assets/pan.png` from `pyproject.toml` package data because the Pan
  action was removed earlier and `toolbar.py` no longer references it.
- Verification after the change:
  - `file pyqt_lab_graph/assets/*` confirms all active assets are PNG images.
  - `python3 -m py_compile pyqt_lab_graph/*.py demo_thermostat.py demo_minimal.py`
  - Offscreen smoke test creating a toolbar-backed widget and verifying that
    each action/button icon is non-null after theme changes.

### Toolbar Icon Fallbacks

- Removed the hard-coded X/Y zoom fallback icon drawing code from
  `pyqt_lab_graph/toolbar.py`.
- The toolbar now relies on the packaged PNG assets for all toolbar icons.
- Removed the fallback plumbing from action creation and theme refresh:
  - `_themed_icon_actions` now stores only `(action, icon_filename)`.
  - `_add_action(...)` no longer accepts a fallback icon.
  - `_themed_icon(...)` no longer accepts or returns fallback icons.
- Removed the unused `_png_icon(...)` helper.
- Removed the generated axis-zoom icon geometry constants and related imports
  (`QPointF`, `QRectF`, `QFont`, `QPen`).
- Rationale: missing packaged icons should be caught by tests/package checks
  instead of being hidden by complex fallback drawing logic.
- Verification after the change:
  - `rg -n "fallback_icon|_create_axis_zoom_icon|_AXIS_ZOOM_ICON|def _png_icon" pyqt_lab_graph/toolbar.py`
    returns no matches.
  - `python3 -m py_compile pyqt_lab_graph/*.py demo_thermostat.py demo_minimal.py`
  - Offscreen smoke test creating a toolbar-backed widget and verifying all
    toolbar icons remain non-null after theme changes.

### Visible Point Counting Fast Path Reverted

- A temporary `bisect` optimization for `_visible_data_point_count()` was tested
  and then removed again to keep the implementation simpler.
- The removed approach added internal sorted X bookkeeping and used
  `bisect_left`/`bisect_right` for sorted X data while falling back to a full
  scan for unsorted scatter data.
- The rollback is intentional:
  - PyQtGraph's rendering/downsampling is already fast for the currently tested
    data sizes.
  - The extra sorted-state bookkeeping was premature complexity.
  - Arbitrary scatter-like X ordering remains naturally supported.
- Backups of the removed implementation are available if it should be restored
  for comparison:
  - `bak/widget.py.pre_remove_visible_count_bisect`
  - `bak/models.py.pre_remove_visible_count_bisect`
  - `bak/CLEANUP_ROADMAP.md.pre_remove_visible_count_bisect`
- Current behavior has since been superseded by the pyqtgraph-native data
  ownership cleanup: visible point counting reads normalized X arrays from
  `PlotDataItem.getData()`.
- Future optimization should be measurement-driven. Reintroduce a fast path only
  if adaptive-performance bookkeeping is shown to be a real bottleneck.
- Adaptive Performance itself should stay in PyQtLabGraph. It is considered a
  useful feature because it can automatically simplify expensive rendering
  choices such as markers and antialiasing when many points are visible.
- Verification after the rollback:
  - `python3 -m py_compile pyqt_lab_graph/*.py demo_thermostat.py demo_minimal.py`
  - Offscreen smoke test with sorted and unsorted curve data verifying the simple
    visible-point count.

### Adaptive Performance Documentation And Smoke Test

- Kept Adaptive Performance as an intentional PyQtLabGraph feature.
- Documented the behavior in `README.md`:
  - PyQtGraph downsampling and clip-to-view handle rendering efficiency.
  - Adaptive Performance is a PyQtLabGraph layer that watches visible point
    count.
  - Dense views temporarily disable markers and antialiasing.
  - Marker and antialiasing settings are restored when fewer points are visible.
  - Scatter-style data with arbitrary X ordering remains supported.
- Added a short docstring to `_update_adaptive_performance(...)` in
  `pyqt_lab_graph/widget.py`.
- Added `tests/smoke_adaptive_performance.py` as a standalone offscreen smoke
  test. It does not require editable installation because it adds the repository
  root to `sys.path`.
- The smoke test forces low thresholds and verifies:
  - Adaptive Performance becomes active for a dense visible range.
  - Markers are disabled while active.
  - Effective antialiasing is disabled while active.
  - Markers and effective antialiasing are restored for a sparse visible range.
  - Disabling Adaptive Performance keeps it inactive even for a dense view.
- Verification after the change:
  - `python3 -m py_compile pyqt_lab_graph/*.py demo_thermostat.py demo_minimal.py tests/smoke_adaptive_performance.py`
  - `QT_QPA_PLATFORM=offscreen python3 tests/smoke_adaptive_performance.py`

### AGENTS.md Refresh

- Updated `AGENTS.md` so future LLM sessions start from the current project
  shape instead of stale pre-cleanup assumptions.
- Removed or corrected outdated guidance:
  - no `demo.py` as the active demo name
  - no Pan toolbar button
  - no required system dark-mode synchronization
  - no theme work in the old single `theme.py` implementation file
- Added current guidance:
  - repository source, UI text, comments, documentation, and demo labels stay in
    English
  - `demo_minimal.py` and `demo_thermostat.py` are the current demo entry points
  - themes and plot styles are separate concepts
  - theme selection is explicit and scoped to PyQtLabGraph-owned widgets
  - Adaptive Performance is an intentional feature and should stay
  - unused assets should be moved to `bak/` instead of deleted
  - active toolbar runtime assets remain PNG files in `pyqt_lab_graph/assets/`
    while source/original variants live outside runtime assets
- Verification after the change:
  - `python3 -m py_compile pyqt_lab_graph/*.py demo_thermostat.py demo_minimal.py tests/smoke_adaptive_performance.py`
  - `QT_QPA_PLATFORM=offscreen python3 tests/smoke_adaptive_performance.py`

### Adaptive Rendering UI Wording

- Renamed the user-facing customize-dialog label from
  `"Adaptive performance:"` to `"Adaptive rendering:"`.
- Added a tooltip to the checkbox:
  `"Temporarily hides markers and disables anti-aliasing when many points are visible."`
- Updated README wording so user-facing documentation refers to "adaptive
  rendering" for the visible feature description.
- Kept the internal names `adaptive_performance_enabled` and
  `adaptive_performance_active` unchanged. They are implementation names and
  changing them would add churn without improving the public behavior.
- The standalone test file remains named `tests/smoke_adaptive_performance.py`
  because it tests the internal feature state.
- Verification after the change:
  - `python3 -m py_compile pyqt_lab_graph/*.py demo_thermostat.py demo_minimal.py tests/smoke_adaptive_performance.py`
  - `QT_QPA_PLATFORM=offscreen python3 tests/smoke_adaptive_performance.py`

### Removed Theme Re-Export Module

- Removed the obsolete active package module `pyqt_lab_graph/theme.py`.
- The file was only a compatibility re-export for objects implemented in
  `pyqt_lab_graph/themes.py`.
- This project is unreleased, so keeping a backward-compatibility import path
  was unnecessary and made the theme module structure less clear.
- No in-repo code imported `pyqt_lab_graph.theme`; active code already imports
  from `pyqt_lab_graph.themes`.
- The removed file was moved to `bak/theme.py.removed_reexport_20260508_225429`
  instead of being deleted.
- `AGENTS.md` was updated so future work no longer treats `theme.py` as an
  active project file.
- Public package exports still come from `pyqt_lab_graph/__init__.py`, which
  imports theme objects from `pyqt_lab_graph/themes.py`.
- Verification after the change:
  - `python3 -m py_compile pyqt_lab_graph/*.py demo_thermostat.py demo_minimal.py tests/smoke_adaptive_performance.py`
  - `QT_QPA_PLATFORM=offscreen python3 tests/smoke_adaptive_performance.py`

### Package Metadata And Project Structure Review

- Reviewed `pyproject.toml`, README project-structure documentation,
  `AGENTS.md`, and the current active file layout after the demo/theme/assets
  cleanup.
- Confirmed active runtime toolbar assets are exactly the PNG files listed in
  `pyproject.toml` package data:
  - `assets/autox.png`
  - `assets/autoy.png`
  - `assets/edit_params.png`
  - `assets/reset_zoom.png`
  - `assets/rolling.png`
  - `assets/saveplot.png`
  - `assets/x-zoom.png`
  - `assets/y-zoom.png`
  - `assets/zoom_area.png`
- Added `[tool.setuptools] include-package-data = false` so package data stays
  explicit and runtime packaging does not depend on incidental manifest/VCS
  behavior.
- README project-structure documentation now distinguishes:
  - package runtime PNG assets in `pyqt_lab_graph/assets/`
  - source/original icons in `original_icons/`
  - standalone smoke tests in `tests/`
  - cleanup handoff notes in `CLEANUP_ROADMAP.md`
  - backups in `bak/`
  - packaging metadata in `pyproject.toml`
- `AGENTS.md` now also notes that `pyproject.toml` package data should remain
  explicit and should package active PNG runtime assets only.
- Verification after the change:
  - `python3 -m py_compile pyqt_lab_graph/*.py demo_thermostat.py demo_minimal.py tests/smoke_adaptive_performance.py`
  - `QT_QPA_PLATFORM=offscreen python3 tests/smoke_adaptive_performance.py`

### Public API Export Cleanup

- Reviewed the top-level public exports in `pyqt_lab_graph/__init__.py`.
- Kept the primary user-facing package exports deliberate:
  - `PyQtLabGraphWidget`
  - `CurveStyle`
  - `PyQtLabGraphPlotStyle`
  - `PyQtLabGraphTheme`
  - `AxisMode`
  - `BUILTIN_THEMES`
  - `BUILTIN_PLOT_STYLES`
  - `__version__`
- Removed implementation/support components from top-level `__all__`:
  - `PyQtLabGraphToolbar`
  - `PyQtLabGraphLegend`
  - `SmartAxisItem`
  - `resolve_theme`
  - `resolve_plot_style`
- The removed top-level names remain available from their implementation modules
  for advanced use:
  - `pyqt_lab_graph.toolbar`
  - `pyqt_lab_graph.legend`
  - `pyqt_lab_graph.axis`
  - `pyqt_lab_graph.themes`
  - `pyqt_lab_graph.styles`
- README import guidance now describes the intended top-level API and points
  advanced users to submodules for implementation components.

### Demo Internal Access Cleanup

- Added `PyQtLabGraphWidget.curve_data(key)` as a small public read helper.
- This behavior has since been superseded by the pyqtgraph-native data
  ownership cleanup: `curve_data(...)` now returns normalized arrays from the
  underlying `PlotDataItem.getData()`.
- Updated `demo_thermostat.py` so bulk test point insertion no longer reads
  `live_plot.curves[...]` directly.
- README usage guidance now lists `curve_data(...)` with the other public curve
  methods and states that direct `.curves` access is not recommended API.
- `tests/smoke_adaptive_performance.py` still intentionally touches internal
  adaptive-performance state and private range helpers because it is focused
  smoke coverage for implementation behavior.

### Axis Formatting Cleanup

- Named the time-unit and subsecond-spacing constants in `pyqt_lab_graph/axis.py`
  without changing formatting behavior.
- Simplified `SmartAxisItem.tickStrings(...)` time-mode formatting to a list
  comprehension.
- Added `tests/smoke_axis_formatting.py` as a standalone offscreen smoke test
  for `SmartAxisItem` time formatting.
- The smoke test covers plain seconds, minute/hour/day composition, negative
  values, subsecond precision thresholds, and a basic linear-mode non-crash
  check.

### Axis Mode Typing Cleanup

- Changed `AxisMode` from a plain string-constant class to `class AxisMode(str, Enum)`.
- Added `resolve_axis_mode(...)` in `pyqt_lab_graph/axis.py` to normalize
  `AxisMode` values and the strings `"auto"`, `"linear"`, and `"time"`.
- Kept user-facing widget calls string-compatible:
  - `set_axis_labels(..., x_mode="time")`
  - `set_axis_labels(..., x_mode=AxisMode.TIME)`
- `PyQtLabGraphWidget` now stores normalized `AxisMode` values internally.
- `SmartAxisItem.set_mode(...)` accepts both `AxisMode` and string values and
  raises a clear `ValueError` for unknown modes.
- README examples now show the typed `AxisMode.TIME` form while documenting that
  string values remain accepted.
- `tests/smoke_axis_formatting.py` now covers string mode input, enum mode
  input, resolver behavior, and invalid-mode errors.

### Customize Dialog Smoke Coverage

- Added stable internal Qt object names to the existing customize-dialog
  controls so offscreen tests can drive the dialog without relying on widget
  construction order.
- Added `tests/smoke_customize_dialog.py` as a standalone offscreen smoke test
  for accepting the customize dialog and applying state back to
  `PyQtLabGraphWidget`.
- The smoke test covers:
  - X/Y labels and typed axis modes
  - grid and rendering flags
  - explicit built-in plot style application
  - per-curve visibility and curve style editing
  - manually applied X/Y ranges, including reversed input order
- No reset behavior was added in this pass. The existing dialog state flow is
  now covered well enough to catch stale reads/writes before adding more dialog
  features.

### Toolbar Runtime Asset Smoke Coverage

- Added `tests/smoke_toolbar_assets.py` as a standalone static smoke test for
  toolbar runtime assets and package data.
- The test parses `pyqt_lab_graph/toolbar.py` for runtime icon filenames passed
  to `_add_action(...)` and `_themed_icon(...)`.
- The test verifies:
  - every toolbar runtime icon exists in `pyqt_lab_graph/assets/`
  - active runtime assets are exactly the toolbar-requested PNG files
  - active runtime asset files have a PNG signature
  - `pyproject.toml` package data exactly lists those runtime PNG assets
  - source/original icons and SVG files are not package data

### Smoke Check Runner

- Added `tests/run_smoke_checks.py` as a lightweight wrapper over the existing
  standalone development smoke checks.
- The runner keeps each smoke test directly executable and does not introduce a
  test framework dependency.
- The runner verifies:
  - Python compilation for package modules, demos, standalone smoke tests, and
    the runner itself
  - adaptive-performance behavior with `QT_QPA_PLATFORM=offscreen`
  - axis formatting behavior with `QT_QPA_PLATFORM=offscreen`
  - customize-dialog state application with `QT_QPA_PLATFORM=offscreen`
  - toolbar runtime asset/package-data consistency
- README development instructions now use `python3 tests/run_smoke_checks.py` as
  the standard local verification command.

### Packaging And Documentation Surface Review

- Reviewed the active file layout, package metadata, README, local agent
  instructions, and cleanup roadmap after adding the smoke-check runner.
- Confirmed `pyproject.toml` package data still lists only active runtime PNG
  toolbar assets from `pyqt_lab_graph/assets/`.
- Confirmed `README.md` describes the current active structure:
  `demo_minimal.py`, `demo_thermostat.py`, `pyqt_lab_graph/themes.py`,
  `pyqt_lab_graph/qt_styles.py`, `original_icons/`, and the smoke checks in
  `tests/`.
- Updated `AGENTS.md` Quick Checks to use `python3 tests/run_smoke_checks.py`
  as the standard verification command while keeping the individual checks
  documented for failure isolation.
- Updated `GEMINI.md`, which is ignored by git but still present locally, so it
  no longer points future agents at obsolete `demo.py`.
- Left historical roadmap references to `demo.py`, `pyqt_lab_graph/theme.py`,
  and `assets/pan.png` intact where they describe completed cleanup history.

### Generated Artifact Cleanup

- Reviewed ignored generated directories in the working tree.
- Found stale generated package metadata in `pyqt_lab_graph.egg-info/` and
  `archive/pyqt_lab_graph.egg-info/`; those generated files still referenced
  obsolete paths such as `demo.py`, `pyqt_lab_graph/theme.py`, and
  `pyqt_lab_graph/assets/pan.png`.
- Moved generated artifact directories into
  `bak/generated_artifacts_20260509_102722/` instead of editing or deleting
  generated metadata by hand:
  - root `__pycache__/`
  - `pyqt_lab_graph/__pycache__/`
  - `tests/__pycache__/`
  - root `pyqt_lab_graph.egg-info/`
  - `archive/pyqt_lab_graph.egg-info/`
- Updated `tests/run_smoke_checks.py` so its syntax check uses Python's
  `compile(...)` directly instead of `python -m py_compile`. This keeps the
  same syntax coverage without creating bytecode cache files.
- The smoke runner now also sets `PYTHONDONTWRITEBYTECODE=1` for child smoke
  test processes.
