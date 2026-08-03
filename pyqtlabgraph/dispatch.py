from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager, nullcontext

from .models import InteractionState


class PlotChangeDispatcher:
    """Coalesces widget-owned public notifications across one command."""

    def __init__(
        self,
        *,
        emit_curve_added: Callable[[str], None],
        emit_curve_removed: Callable[[str], None],
        emit_curve_changed: Callable[[str], None],
        emit_curve_data_changed: Callable[[str], None],
        emit_interaction_state_changed: Callable[[InteractionState], None],
        emit_presentation_changed: Callable[[], None],
        emit_state_reset: Callable[[], None],
    ) -> None:
        self._emit_curve_added = emit_curve_added
        self._emit_curve_removed = emit_curve_removed
        self._emit_curve_changed = emit_curve_changed
        self._emit_curve_data_changed = emit_curve_data_changed
        self._emit_interaction_state_changed = emit_interaction_state_changed
        self._emit_presentation_changed = emit_presentation_changed
        self._emit_state_reset = emit_state_reset
        self._batch_participant: (
            Callable[[], AbstractContextManager[None]] | None
        ) = None
        self._discard_participant_changes: Callable[[], None] | None = None
        self._suppress_participant_events: Callable[[], None] | None = None
        self._batch_depth = 0
        self._batch_failed = False
        self._curve_added: dict[str, None] = {}
        self._curve_removed: dict[str, None] = {}
        self._curve_changed: dict[str, None] = {}
        self._curve_data_changed: dict[str, None] = {}
        self._interaction_state: InteractionState | None = None
        self._presentation_changed = False

    @contextmanager
    def state_replacement(self) -> Iterator[None]:
        """Suppress granular notifications and publish one reset on success."""
        if self._batch_depth:
            raise RuntimeError(
                "State replacement cannot start inside another dispatcher batch."
            )
        succeeded = False
        with self.batch():
            try:
                yield
            except BaseException:
                raise
            else:
                succeeded = True
                if self._suppress_participant_events is not None:
                    self._suppress_participant_events()
            finally:
                if (
                    not succeeded
                    and self._discard_participant_changes is not None
                ):
                    self._discard_participant_changes()
                self._clear()
        if succeeded:
            self._emit_state_reset()

    def set_batch_participant(
        self,
        participant: Callable[[], AbstractContextManager[None]],
        *,
        discard_changes: Callable[[], None],
        suppress_events: Callable[[], None],
    ) -> None:
        if self._batch_depth:
            raise RuntimeError("Cannot replace a dispatcher participant during a batch.")
        self._batch_participant = participant
        self._discard_participant_changes = discard_changes
        self._suppress_participant_events = suppress_events

    @contextmanager
    def batch(self) -> Iterator[None]:
        if self._batch_depth:
            self._batch_depth += 1
            try:
                yield
            except BaseException:
                self._batch_failed = True
                raise
            finally:
                self._batch_depth -= 1
            return

        self._batch_failed = False
        self._batch_depth = 1
        participant = (
            self._batch_participant()
            if self._batch_participant is not None
            else nullcontext()
        )
        try:
            with participant:
                try:
                    yield
                except BaseException:
                    self._batch_failed = True
                    if self._discard_participant_changes is not None:
                        self._discard_participant_changes()
                    raise
                else:
                    if (
                        self._batch_failed
                        and self._discard_participant_changes is not None
                    ):
                        self._discard_participant_changes()
        except BaseException:
            self._batch_failed = True
            raise
        finally:
            self._batch_depth -= 1
            if self._batch_failed:
                self._clear()
            else:
                self._flush()

    def curve_added(self, key: str) -> None:
        self._queue_or_emit(self._curve_added, key, self._emit_curve_added)

    def curve_removed(self, key: str) -> None:
        self._queue_or_emit(self._curve_removed, key, self._emit_curve_removed)

    def curve_changed(self, key: str) -> None:
        self._queue_or_emit(self._curve_changed, key, self._emit_curve_changed)

    def curve_data_changed(self, key: str) -> None:
        self._queue_or_emit(
            self._curve_data_changed,
            key,
            self._emit_curve_data_changed,
        )

    def interaction_state_changed(self, state: InteractionState) -> None:
        if self._batch_depth:
            self._interaction_state = state
        else:
            self._emit_interaction_state_changed(state)

    def presentation_changed(self) -> None:
        if self._batch_depth:
            self._presentation_changed = True
        else:
            self._emit_presentation_changed()

    def _queue_or_emit(
        self,
        pending: dict[str, None],
        key: str,
        emitter: Callable[[str], None],
    ) -> None:
        if self._batch_depth:
            pending[key] = None
        else:
            emitter(key)

    def _flush(self) -> None:
        for pending, emitter in (
            (self._curve_added, self._emit_curve_added),
            (self._curve_removed, self._emit_curve_removed),
            (self._curve_changed, self._emit_curve_changed),
            (self._curve_data_changed, self._emit_curve_data_changed),
        ):
            for key in pending:
                emitter(key)
        if self._interaction_state is not None:
            self._emit_interaction_state_changed(self._interaction_state)
        if self._presentation_changed:
            self._emit_presentation_changed()
        self._clear()

    def _clear(self) -> None:
        self._curve_added.clear()
        self._curve_removed.clear()
        self._curve_changed.clear()
        self._curve_data_changed.clear()
        self._interaction_state = None
        self._presentation_changed = False
