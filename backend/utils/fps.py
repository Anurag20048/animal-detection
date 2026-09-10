import time


class FPSCounter:
    def __init__(self, smoothing: float = 0.90) -> None:
        self.smoothing = smoothing
        self.last_time: float | None = None
        self.fps = 0.0

    def update(self) -> float:
        now = time.perf_counter()
        if self.last_time is None:
            self.last_time = now
            return self.fps

        elapsed = max(now - self.last_time, 1e-9)
        instant_fps = 1.0 / elapsed
        if self.fps <= 0:
            self.fps = instant_fps
        else:
            self.fps = (self.fps * self.smoothing) + (
                instant_fps * (1.0 - self.smoothing)
            )
        self.last_time = now
        return self.fps
