"""2D 移流拡散方程式の数値解生成

∂u/∂t = D ∇²u - (v_x ∂u/∂x + v_y ∂u/∂y)

- 周期境界、64×64 グリッド、有限差分 (D=0.02, v=(0.5,0.3))
- Explicit Euler で dt を CFL 制限内に選択
- ランダムな Gaussian 初期条件でトラジェクトリを生成
"""
from __future__ import annotations
import numpy as np


def step_advdiff(u: np.ndarray, D: float, vx: float, vy: float,
                 dx: float, dt: float) -> np.ndarray:
    # 中心差分 + 周期境界 (np.roll)
    lap = (np.roll(u, 1, 0) + np.roll(u, -1, 0)
         + np.roll(u, 1, 1) + np.roll(u, -1, 1) - 4 * u) / dx**2
    dudx = (np.roll(u, -1, 1) - np.roll(u, 1, 1)) / (2 * dx)
    dudy = (np.roll(u, -1, 0) - np.roll(u, 1, 0)) / (2 * dx)
    return u + dt * (D * lap - vx * dudx - vy * dudy)


def random_initial(rng: np.random.Generator, n: int = 64, n_blobs: int = 3) -> np.ndarray:
    """複数のガウシアン重ね合わせで初期場を作る"""
    x = np.linspace(-1, 1, n)
    X, Y = np.meshgrid(x, x)
    u = np.zeros_like(X)
    for _ in range(n_blobs):
        cx = rng.uniform(-0.6, 0.6); cy = rng.uniform(-0.6, 0.6)
        s = rng.uniform(0.08, 0.20)
        amp = rng.uniform(0.5, 1.5)
        u += amp * np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / (2 * s ** 2))
    return u.astype(np.float32)


def generate_trajectories(n_traj: int, n_steps: int, n: int = 64,
                          D: float = 0.02, vx: float = 0.5, vy: float = 0.3,
                          dx: float = 2.0 / 64, seed: int = 42
                          ) -> tuple[np.ndarray, float]:
    """Return array of shape (n_traj, n_steps+1, n, n) and dt used"""
    # CFL: dt < min(dx/|v|, dx²/(4D))
    dt_cfl = min(dx / max(abs(vx), abs(vy)), dx ** 2 / (4 * D))
    dt = 0.4 * dt_cfl
    rng = np.random.default_rng(seed)
    trajs = np.zeros((n_traj, n_steps + 1, n, n), dtype=np.float32)
    for i in range(n_traj):
        u = random_initial(rng, n=n)
        trajs[i, 0] = u
        for t in range(n_steps):
            u = step_advdiff(u, D, vx, vy, dx, dt)
            trajs[i, t + 1] = u
    return trajs, dt
