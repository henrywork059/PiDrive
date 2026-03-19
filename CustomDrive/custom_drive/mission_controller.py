from __future__ import annotations

from typing import Any, Optional

from .config import MissionConfig
from .debug_tools import append_event, trim_events
from .interfaces import RobotInterface
from .mission_state import MissionState
from .models import DriveCommand, FramePerception, MissionSnapshot
from .route_script import TimedRouteFollower
from .visual_servo import VisualServoController, select_best_detection


class MissionController:
    def __init__(self, robot: RobotInterface, config: Optional[MissionConfig] = None):
        self.robot = robot
        self.config = config or MissionConfig()
        self.route_follower = TimedRouteFollower(self.config.routes)
        self.visual = VisualServoController(self.config)

        self.state = MissionState.IDLE
        self.state_entered_at = self.robot.now()
        self.retries = 0
        self.completed_cycles = 0
        self.center_hold_counter = 0
        self.active_route_leg: Optional[str] = None
        self.last_command = DriveCommand(note='init')
        self.detail = 'created'
        self.debug_events: list[dict[str, Any]] = []
        self.debug_limit = 200
        append_event(self.debug_events, 'Mission controller created.', event_type='state', state=self.state.value)

    def start(self) -> None:
        if self.state in (MissionState.COMPLETE, MissionState.FAILED):
            self._record('Mission already finished. Reset runtime to run again.', level='warning', event_type='state')
            return
        now = self.robot.now()
        try:
            self.route_follower.start('to_search_area', now)
            self._set_state(MissionState.DRIVE_TO_SEARCH_AREA, 'mission started')
        except Exception as exc:
            self._set_state(MissionState.FAILED, f'failed to start route: {exc}')
            self._record('Failed to start first route.', level='error', event_type='route', error=str(exc))

    def state_elapsed(self) -> float:
        return self.robot.now() - self.state_entered_at

    def snapshot(self) -> MissionSnapshot:
        return MissionSnapshot(
            state=self.state.value,
            detail=self.detail,
            retries=self.retries,
            completed_cycles=self.completed_cycles,
            last_command=self.last_command,
            active_route_leg=self.active_route_leg,
        )

    def get_debug_events(self, limit: int | None = None) -> list[dict[str, Any]]:
        events = list(self.debug_events)
        if limit is not None and limit > 0:
            return events[-limit:]
        return events

    def update(self, perception: FramePerception) -> MissionSnapshot:
        if self.state in (MissionState.IDLE, MissionState.COMPLETE, MissionState.FAILED):
            return self.snapshot()

        if self.state == MissionState.DRIVE_TO_SEARCH_AREA:
            done, cmd, leg = self.route_follower.update(self.robot.now())
            self._update_route_leg(leg)
            if done:
                self.robot.stop('search area reached')
                self._set_state(MissionState.SCAN_FOR_TARGET, 'coarse route to search area complete')
            else:
                self._send(cmd)
            return self.snapshot()

        if self.state == MissionState.SCAN_FOR_TARGET:
            det = self._get_target_detection(perception)
            if det is not None:
                self.center_hold_counter = 0
                self._record('Target detected.', event_type='perception', label=det.label, confidence=round(float(det.confidence), 3))
                self._set_state(MissionState.ALIGN_TO_TARGET, 'target found')
            elif self.state_elapsed() > self.config.search_timeout_s:
                self._retry_or_fail(MissionState.SCAN_FOR_TARGET, 'target not found in time')
            else:
                self._send(self.visual.search_command('scan for target'))
            return self.snapshot()

        if self.state == MissionState.ALIGN_TO_TARGET:
            det = self._get_target_detection(perception)
            if det is None:
                self._retry_or_fail(MissionState.SCAN_FOR_TARGET, 'lost target during alignment')
                return self.snapshot()

            self._send(self.visual.align_command(det, perception, 'align to target'))
            if self.visual.is_centered(det, perception):
                self.center_hold_counter += 1
            else:
                self.center_hold_counter = 0

            if self.center_hold_counter >= self.config.center_hold_frames:
                self._set_state(MissionState.APPROACH_TARGET, 'target centered')
            return self.snapshot()

        if self.state == MissionState.APPROACH_TARGET:
            det = self._get_target_detection(perception)
            if det is None:
                self._retry_or_fail(MissionState.SCAN_FOR_TARGET, 'lost target during approach')
                return self.snapshot()

            if self.visual.is_close_for_pickup(det, perception):
                self.robot.stop('pickup distance reached')
                self._set_state(MissionState.GRAB_TARGET, 'ready to grab')
                return self.snapshot()

            self._send(self.visual.approach_command(det, perception, 'approach target'))
            return self.snapshot()

        if self.state == MissionState.GRAB_TARGET:
            self.robot.stop('start pickup sequence')
            ok = self.robot.pickup_sequence()
            if not ok:
                self._retry_or_fail(MissionState.SCAN_FOR_TARGET, 'pickup sequence failed')
                return self.snapshot()
            try:
                self.route_follower.start('to_drop_zone', self.robot.now())
            except Exception as exc:
                self._set_state(MissionState.FAILED, f'failed to start drop route: {exc}')
                self._record('Failed to start drop-zone route.', level='error', event_type='route', error=str(exc))
                return self.snapshot()
            self._set_state(MissionState.DRIVE_TO_DROP_ZONE, 'target grabbed')
            return self.snapshot()

        if self.state == MissionState.DRIVE_TO_DROP_ZONE:
            done, cmd, leg = self.route_follower.update(self.robot.now())
            self._update_route_leg(leg)
            if done:
                self.robot.stop('drop search area reached')
                self._set_state(MissionState.SCAN_FOR_DROP_ZONE, 'coarse route to drop zone complete')
            else:
                self._send(cmd)
            return self.snapshot()

        if self.state == MissionState.SCAN_FOR_DROP_ZONE:
            det = self._get_drop_zone_detection(perception)
            if det is not None:
                self.center_hold_counter = 0
                self._record('Drop zone detected.', event_type='perception', label=det.label, confidence=round(float(det.confidence), 3))
                self._set_state(MissionState.ALIGN_TO_DROP_ZONE, 'drop zone found')
            elif self.state_elapsed() > self.config.search_timeout_s:
                self._retry_or_fail(MissionState.SCAN_FOR_DROP_ZONE, 'drop zone not found in time')
            else:
                self._send(self.visual.search_command('scan for drop zone'))
            return self.snapshot()

        if self.state == MissionState.ALIGN_TO_DROP_ZONE:
            det = self._get_drop_zone_detection(perception)
            if det is None:
                self._retry_or_fail(MissionState.SCAN_FOR_DROP_ZONE, 'lost drop zone during alignment')
                return self.snapshot()

            self._send(self.visual.align_command(det, perception, 'align to drop zone'))
            if self.visual.is_centered(det, perception):
                self.center_hold_counter += 1
            else:
                self.center_hold_counter = 0

            if self.center_hold_counter >= self.config.center_hold_frames:
                self._set_state(MissionState.APPROACH_DROP_ZONE, 'drop zone centered')
            return self.snapshot()

        if self.state == MissionState.APPROACH_DROP_ZONE:
            det = self._get_drop_zone_detection(perception)
            if det is None:
                self._retry_or_fail(MissionState.SCAN_FOR_DROP_ZONE, 'lost drop zone during approach')
                return self.snapshot()

            if self.visual.is_close_for_drop(det, perception):
                self.robot.stop('release distance reached')
                self._set_state(MissionState.RELEASE_TARGET, 'ready to release')
                return self.snapshot()

            self._send(self.visual.approach_command(det, perception, 'approach drop zone'))
            return self.snapshot()

        if self.state == MissionState.RELEASE_TARGET:
            self.robot.stop('start release sequence')
            ok = self.robot.release_sequence()
            if not ok:
                self._retry_or_fail(MissionState.SCAN_FOR_DROP_ZONE, 'release sequence failed')
                return self.snapshot()
            self._set_state(MissionState.BACK_OUT, 'target released')
            return self.snapshot()

        if self.state == MissionState.BACK_OUT:
            if self.state_elapsed() >= 0.7:
                self.robot.stop('back-out complete')
                self.completed_cycles += 1
                self.retries = 0
                if self.config.enable_repeat and self.completed_cycles < self.config.max_cycles:
                    try:
                        self.route_follower.start('to_search_area', self.robot.now())
                    except Exception as exc:
                        self._set_state(MissionState.FAILED, f'failed to start next cycle: {exc}')
                        self._record('Failed to start next cycle.', level='error', event_type='route', error=str(exc))
                        return self.snapshot()
                    self._set_state(MissionState.DRIVE_TO_SEARCH_AREA, 'start next cycle')
                else:
                    self._set_state(MissionState.COMPLETE, 'mission complete')
                return self.snapshot()

            self._send(self.visual.back_out_command())
            return self.snapshot()

        return self.snapshot()

    def _get_target_detection(self, perception: FramePerception):
        return select_best_detection(perception, self.config.target_label, self.config.min_confidence)

    def _get_drop_zone_detection(self, perception: FramePerception):
        return select_best_detection(perception, self.config.drop_zone_label, self.config.min_confidence)

    def _update_route_leg(self, leg: Optional[str]) -> None:
        previous = self.active_route_leg
        self.active_route_leg = leg
        if leg != previous and leg is not None:
            self._record('Entered route leg.', event_type='route', leg=leg, state=self.state.value)

    def _send(self, cmd: DriveCommand) -> None:
        self.last_command = cmd
        self.robot.set_drive(cmd.steering, cmd.throttle, cmd.note)
        self.detail = cmd.note

    def _set_state(self, state: MissionState, detail: str) -> None:
        previous_state = self.state
        self.state = state
        self.state_entered_at = self.robot.now()
        if state not in (MissionState.DRIVE_TO_SEARCH_AREA, MissionState.DRIVE_TO_DROP_ZONE):
            self.active_route_leg = None
        self.center_hold_counter = 0
        self.detail = detail
        self._record(
            'State changed.',
            event_type='state',
            from_state=previous_state.value,
            to_state=state.value,
            detail=detail,
            retries=self.retries,
            completed_cycles=self.completed_cycles,
        )

    def _retry_or_fail(self, retry_state: MissionState, detail: str) -> None:
        self.robot.stop(detail)
        self.retries += 1
        if self.retries > self.config.max_retries_per_stage:
            self._set_state(MissionState.FAILED, detail)
            self._record('Maximum retries exceeded.', level='error', event_type='retry', detail=detail, retries=self.retries)
            return
        self._record('Retrying stage.', level='warning', event_type='retry', retry_state=retry_state.value, detail=detail, retries=self.retries)
        self._set_state(retry_state, f'retry {self.retries}: {detail}')

    def _record(self, message: str, *, level: str = 'info', event_type: str = 'runtime', **fields: Any) -> None:
        append_event(self.debug_events, message, level=level, event_type=event_type, limit=self.debug_limit, **fields)
        trim_events(self.debug_events, self.debug_limit)
