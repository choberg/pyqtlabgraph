from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager


class PlotChangeDispatcher:
    """Coalesces public plot notifications and presentation refreshes per command.

    Outside a batch, `publish()` emits immediately and `refresh()` runs at once.
    Inside a batch, events are coalesced by signal and key (the latest arguments
    win) and refreshes run once. At the end of the outermost batch, refreshes
    always run so graphics match the authoritative state; events are emitted
    in signal-registration order only when the batch succeeded.
    """

    def __init__(
        self,
        emitters: Mapping[str, Callable[..., None]],
        *,
        emit_state_reset: Callable[[], None],
    ) -> None:
        self._emitters = dict(emitters)
        self._priority = {name: index for index, name in enumerate(self._emitters)}
        self._emit_state_reset = emit_state_reset
        self._depth = 0
        self._failed = False
        self._pending: dict[tuple[str, object], tuple[object, ...]] = {}
        self._refreshes: dict[Callable[[], None], None] = {}

    @property
    def batching(self) -> bool:
        return self._depth > 0

    def publish(self, signal_name: str, *args: object) -> None:
        emitter = self._emitters[signal_name]
        if not self._depth:
            emitter(*args)
            return
        key = args[0] if args and signal_name != "interaction_state_changed" else None
        self._pending[(signal_name, key)] = args

    def refresh(self, callback: Callable[[], None]) -> None:
        if self._depth:
            self._refreshes[callback] = None
        else:
            callback()

    @contextmanager
    def batch(self) -> Iterator[None]:
        if not self._depth:
            self._failed = False
        self._depth += 1
        try:
            yield
        except BaseException:
            self._failed = True
            raise
        finally:
            self._depth -= 1
            if not self._depth:
                self._finish()

    @contextmanager
    def state_replacement(self) -> Iterator[None]:
        """Suppress granular notifications and publish one reset on success."""
        if self._depth:
            raise RuntimeError("State replacement cannot start inside another dispatcher batch.")
        with self.batch():
            yield
            self._failed = True
        self._emit_state_reset()

    def _finish(self) -> None:
        refreshes = tuple(self._refreshes)
        self._refreshes.clear()
        pending = sorted(self._pending.items(), key=lambda item: self._priority[item[0][0]])
        self._pending.clear()
        for callback in refreshes:
            callback()
        if self._failed:
            return
        for (signal_name, _key), args in pending:
            self._emitters[signal_name](*args)
