from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from pyqtgraph import PlotItem, ViewBox
from PySide6.QtCore import QPointF, QRectF

from .cursor_plot_items import CursorPairPlotItem, CursorPlotItem
from .models import CursorType

if TYPE_CHECKING:
    from .cursor_controller import CursorController


_CURSOR_LABEL_MARGIN_PX = 2.0
_CURSOR_LABEL_ROW_GAP_PX = 2.0


class CursorPlotPresenter:
    """Owns cursor graphics and synchronizes them with controller state."""

    def __init__(
        self,
        *,
        controller: CursorController,
        plot_item: PlotItem,
        view_box: ViewBox,
        x_log_provider: Callable[[], bool],
        y_log_provider: Callable[[], bool],
        plot_background_provider: Callable[[], str],
    ) -> None:
        self.controller = controller
        self._plot_item = plot_item
        self._view_box = view_box
        self._x_log_provider = x_log_provider
        self._y_log_provider = y_log_provider
        self._plot_background_provider = plot_background_provider
        self.cursor_items: dict[str, CursorPlotItem] = {}
        self.pair_items: dict[str, CursorPairPlotItem] = {}

    def create_cursor(self, cursor_key: str) -> None:
        state = self.controller.cursor_state(cursor_key)
        cursor_item = CursorPlotItem(state)
        cursor_item.item.sigPositionChanged.connect(
            lambda _line, key=cursor_key: self.handle_cursor_moved(key)
        )
        cursor_item.item.sigClicked.connect(
            lambda *_args, key=cursor_key: self.handle_cursor_clicked(key)
        )
        self._plot_item.addItem(cursor_item.item, ignoreBounds=True)
        self._plot_item.addItem(cursor_item.label, ignoreBounds=True)
        self.cursor_items[cursor_key] = cursor_item
        self.update_cursor(cursor_key)

    def remove_cursor(self, cursor_key: str) -> None:
        cursor_item = self.cursor_items.pop(cursor_key, None)
        if cursor_item is not None:
            self._plot_item.removeItem(cursor_item.item)
            self._plot_item.removeItem(cursor_item.label)

    def create_pair(self, pair_key: str) -> None:
        pair_state = self.controller.cursor_pair_state(pair_key)
        first_state = self.controller.cursor_state(pair_state.first_cursor_key)

        def move_annotation(position: QPointF, key: str = pair_key) -> None:
            self.handle_pair_annotation_moved(key, position)

        pair_item = CursorPairPlotItem(
            pair_state,
            first_state.cursor_type,
            move_annotation,
        )
        for item in pair_item.items:
            self._plot_item.addItem(item, ignoreBounds=True)
        self.pair_items[pair_key] = pair_item
        self.update_pair(pair_key)

    def remove_pair(self, pair_key: str) -> None:
        pair_item = self.pair_items.pop(pair_key, None)
        if pair_item is None:
            return
        for item in pair_item.items:
            self._plot_item.removeItem(item)

    def update_pair(self, pair_key: str) -> None:
        pair_item = self.pair_items.get(pair_key)
        if pair_item is None:
            return
        pair_state = self.controller.cursor_pair_state(pair_key)
        first_state = self.controller.cursor_state(pair_state.first_cursor_key)
        second_state = self.controller.cursor_state(pair_state.second_cursor_key)
        pair_item.update_from_pair(
            pair_state,
            first_state,
            second_state,
            text=self.controller.cursor_pair_measurement_text(pair_key),
            effective_visible=(
                self.controller.cursor_effective_visible(first_state.key)
                and self.controller.cursor_effective_visible(second_state.key)
            ),
            x_log=self._x_log_provider(),
            y_log=self._y_log_provider(),
            view_rect=self._view_box.viewRect(),
            plot_background=self._plot_background_provider(),
        )

    def update_pair_for_cursor(self, cursor_key: str) -> None:
        try:
            pair_state = self.controller.cursor_pair_for_cursor(cursor_key)
        except KeyError:
            return
        if pair_state is not None:
            self.update_pair(pair_state.key)

    def handle_pair_annotation_moved(self, pair_key: str, scene_position: QPointF) -> None:
        pair_state = self.controller.cursor_pair_state(pair_key)
        first_state = self.controller.cursor_state(pair_state.first_cursor_key)
        view_rect = self._view_box.viewRect()
        if view_rect.isNull():
            return
        view_position = self._view_box.mapSceneToView(scene_position)
        if first_state.cursor_type is CursorType.X:
            position = (view_position.y() - view_rect.top()) / view_rect.height()
        else:
            position = (view_position.x() - view_rect.left()) / view_rect.width()
        self.controller.set_cursor_pair_annotation_position(
            pair_key,
            min(0.98, max(0.02, position)),
        )

    def update_all_pairs(self) -> None:
        for pair_state in self.controller.cursor_pair_states():
            self.update_pair(pair_state.key)

    def update_cursor(self, cursor_key: str) -> None:
        cursor_item = self.cursor_items.get(cursor_key)
        if cursor_item is None:
            return
        state = self.controller.cursor_state(cursor_key)
        cursor_item.update_from_state(
            state,
            text=self.controller.format_cursor_value(state.cursor_type, state.value),
            effective_visible=self.controller.cursor_effective_visible(cursor_key),
            selected=cursor_key in set(self.controller.selected_cursor_keys()),
            x_log=self._x_log_provider(),
            y_log=self._y_log_provider(),
            plot_background=self._plot_background_provider(),
        )
        self.layout_labels()

    def handle_cursor_moved(self, cursor_key: str) -> None:
        cursor_item = self.cursor_items.get(cursor_key)
        if cursor_item is None:
            return
        state = self.controller.cursor_state(cursor_key)
        raw_value = cursor_item.raw_value_from_item(
            state,
            x_log=self._x_log_provider(),
            y_log=self._y_log_provider(),
        )
        if raw_value is None:
            self.update_cursor(cursor_key)
            return
        selected = self.controller.selected_cursor_keys()
        move_selected_peers = cursor_key in selected
        before_value = state.value
        self.controller.set_cursor_value(cursor_key, raw_value)
        if move_selected_peers:
            after_value = self.controller.cursor_state(cursor_key).value
            self.controller.move_selected_cursor_peers(
                anchor_cursor_key=cursor_key,
                selected_cursor_keys=selected,
                cursor_type=state.cursor_type,
                raw_delta=after_value - before_value,
            )

    def handle_cursor_clicked(self, cursor_key: str) -> None:
        if cursor_key not in self.controller.selected_cursor_keys():
            self.controller.set_selected_cursor_keys([cursor_key])

    def update_all(self) -> None:
        selected = set(self.controller.selected_cursor_keys())
        for state in self.controller.cursor_states():
            cursor_item = self.cursor_items.get(state.key)
            if cursor_item is None:
                continue
            cursor_item.update_from_state(
                state,
                text=self.controller.format_cursor_value(state.cursor_type, state.value),
                effective_visible=self.controller.cursor_effective_visible(state.key),
                selected=state.key in selected,
                x_log=self._x_log_provider(),
                y_log=self._y_log_provider(),
                plot_background=self._plot_background_provider(),
            )
        self.layout_labels()
        self.update_all_pairs()

    def layout_labels(self) -> None:
        view_rect = self._view_box.viewRect()
        if view_rect.isNull():
            return
        scene_rect = self._view_rect_scene_bounds(view_rect)
        placed_rects: list[QRectF] = []
        x_middle = view_rect.center().x()
        y_middle = view_rect.center().y()
        for state in self.controller.cursor_states():
            cursor_item = self.cursor_items.get(state.key)
            if cursor_item is None or not cursor_item.label.isVisible():
                continue
            display_value = cursor_item.display_value(
                state,
                x_log=self._x_log_provider(),
                y_log=self._y_log_provider(),
            )
            if display_value is None:
                continue
            label_rect = cursor_item.label.boundingRect()
            width = label_rect.width()
            height = label_rect.height()
            if width <= 0.0 or height <= 0.0:
                continue
            if state.cursor_type is CursorType.X:
                line_scene = self._view_box.mapViewToScene(QPointF(display_value, y_middle))
                candidate = QRectF(
                    line_scene.x() + _CURSOR_LABEL_MARGIN_PX,
                    scene_rect.top() + _CURSOR_LABEL_MARGIN_PX,
                    width,
                    height,
                )
                if candidate.right() > scene_rect.right() - _CURSOR_LABEL_MARGIN_PX:
                    candidate.moveLeft(line_scene.x() - _CURSOR_LABEL_MARGIN_PX - width)
            else:
                line_scene = self._view_box.mapViewToScene(QPointF(x_middle, display_value))
                candidate = QRectF(
                    scene_rect.left() + _CURSOR_LABEL_MARGIN_PX,
                    line_scene.y() - _CURSOR_LABEL_MARGIN_PX - height,
                    width,
                    height,
                )
                if candidate.top() < scene_rect.top() + _CURSOR_LABEL_MARGIN_PX:
                    candidate.moveTop(line_scene.y() + _CURSOR_LABEL_MARGIN_PX)
            candidate = self._clamp_label_rect(candidate, scene_rect)
            max_top = scene_rect.bottom() - _CURSOR_LABEL_MARGIN_PX - height
            while any(candidate.intersects(placed) for placed in placed_rects):
                next_top = candidate.top() + height + _CURSOR_LABEL_ROW_GAP_PX
                if next_top > max_top:
                    candidate.moveTop(max_top)
                    break
                candidate.moveTop(next_top)
            candidate = self._clamp_label_rect(candidate, scene_rect)
            cursor_item.label.setPos(self._view_box.mapSceneToView(candidate.topLeft()))
            placed_rects.append(candidate)

    def _view_rect_scene_bounds(self, view_rect: QRectF) -> QRectF:
        scene_points = [
            self._view_box.mapViewToScene(point)
            for point in (
                view_rect.topLeft(),
                view_rect.topRight(),
                view_rect.bottomLeft(),
                view_rect.bottomRight(),
            )
        ]
        left = min(point.x() for point in scene_points)
        right = max(point.x() for point in scene_points)
        top = min(point.y() for point in scene_points)
        bottom = max(point.y() for point in scene_points)
        return QRectF(QPointF(left, top), QPointF(right, bottom))

    @staticmethod
    def _clamp_label_rect(label_rect: QRectF, scene_rect: QRectF) -> QRectF:
        clamped = QRectF(label_rect)
        minimum_left = scene_rect.left() + _CURSOR_LABEL_MARGIN_PX
        maximum_left = scene_rect.right() - _CURSOR_LABEL_MARGIN_PX - clamped.width()
        minimum_top = scene_rect.top() + _CURSOR_LABEL_MARGIN_PX
        maximum_top = scene_rect.bottom() - _CURSOR_LABEL_MARGIN_PX - clamped.height()
        clamped.moveLeft(min(max(clamped.left(), minimum_left), max(minimum_left, maximum_left)))
        clamped.moveTop(min(max(clamped.top(), minimum_top), max(minimum_top, maximum_top)))
        return clamped
