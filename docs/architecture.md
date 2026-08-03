# Architecture

`PyQtLabGraphWidget` is the public plotting facade and the Qt composition root.
Hosts issue plot commands through this widget and subscribe to its public
signals. `PyQtLabGraphToolbar`, `PyQtLabGraphLegend`, and
`PyQtLabGraphCursorWidget` are independent companion widgets: they send user
intents through the facade and project facade-owned state.

## Ownership

- The curve subsystem owns curve metadata, order, and the PyQtGraph
  `PlotDataItem` lifecycle. X/Y arrays remain owned by `PlotDataItem`.
- The range, rendering, style, interaction, cursor-domain, cursor-presentation,
  and layout subsystems have separate responsibilities.
- Runtime rollback uses immutable `PlotSnapshot` values. Persisted layouts use
  separate layout DTOs and a strict, complete version-1 JSON format. Saved
  cursor state is authoritative, while curve settings reconcile against the
  host-created curve set.
- Cursor selection belongs to the plot. Any attached cursor panels project the
  same canonical selection through their Qt selection models.
- Themes control the ViewBox background and grid. Plot styles control curve
  lines and markers. Host Qt palettes and styles control axes and UI chrome.

Internal collaborators receive explicit plot items, view boxes, providers, and
callbacks instead of using the public widget as a service locator. Productive
components must not access another component's private attributes.

## Updates and Signals

Widget commands pass through a dispatcher that orders dependent updates,
coalesces notifications, and supports atomic state replacement. The public
widget is the only publisher of public state-change signals. Failed commands
and effective no-ops do not emit semantic change signals.

Curve data updates follow this order:

1. Mutate the curve data.
2. Refresh snapped cursors.
3. Apply automatic ranges.
4. Evaluate Adaptive Performance for the final visible range.
5. Reapply appearance only if adaptive mode changed.
6. Refresh cursor presentation.
7. Publish coalesced widget signals.

## Native Integration

Advanced hosts may deliberately bypass the high-level API through
`native_plot_widget`, `native_plot_item`, `native_view_box`, and
`curve_item(key)`. These are public escape hatches; private controller,
presenter, and manager attributes are not extension APIs.

## Enforced Boundaries

The test suite parses productive modules with Python's AST to reject
cross-component private attribute access and runtime import cycles. Ruff checks
imports and common correctness issues. Mypy checks the package while explicitly
treating PySide6 and PyQtGraph as untyped integration boundaries.

CI runs these checks with the behavioral and offscreen Qt suites on Python
3.11, 3.12, and 3.13. It builds the source distribution and wheel, then
installs the wheel into a clean environment to verify imports, public exports,
version metadata, `py.typed`, and runtime PNG assets.
