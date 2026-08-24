import sys
import holidays
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

STATES = [
    "zone/Z01/air_temperature",
    "zone/Z02/air_temperature",
    "zone/Z03/air_temperature",
    "zone/Z04/air_temperature",
    "zone/Z05/air_temperature",
    "zone/Z11/air_temperature",
    "zone/Z12_Z13/air_temperature",
    "zone/Z14/air_temperature",
    "zone/Z15_Z16/air_temperature",
    "zone/Z17/air_temperature",
    "zone/Z21/air_temperature",
    "zone/Z22_Z23/air_temperature",
    "zone/Z24/air_temperature",
    "zone/Z25_Z26_Z27/air_temperature",
    "zone/Z31/air_temperature",
    "zone/Z32/air_temperature",
    "zone/Z33/air_temperature",
    "zone/Z01/slab_temperature",
    "zone/Z02/slab_temperature",
    "zone/Z04/slab_temperature",
    "zone/Z11/slab_temperature",
    "zone/Z12/slab_temperature",
    "zone/Z13/slab_temperature",
    "zone/Z14/slab_temperature",
    "zone/Z15/slab_temperature",
    "zone/Z16/slab_temperature",
    "zone/Z17/slab_temperature",
    "zone/Z21/slab_temperature",
    "zone/Z22/slab_temperature",
    "zone/Z23/slab_temperature",
    "zone/Z24/slab_temperature",
    "zone/Z25/slab_temperature",
    "zone/Z26/slab_temperature",
    "zone/Z27/slab_temperature",
    "zone/Z31/slab_temperature",
    "zone/Z32/slab_temperature",
    "zone/Z33/slab_temperature",
]
EXTERNALS = [
    "outdoor/weather/air_temperature",
    "outdoor/weather/solar_radiation",
    "zone/Z01/valve",
    "zone/Z02/valve",
    "zone/Z03_Z04_Z05/valve",
    "zone/Z11/valve",
    "zone/Z12/valve",
    "zone/Z13/valve",
    "zone/Z14/valve",
    "zone/Z15/valve",
    "zone/Z16_Z17/valve",
    "zone/Z21/valve",
    "zone/Z22/valve",
    "zone/Z23/valve",
    "zone/Z24/valve",
    "zone/Z25/valve",
    "zone/Z26/valve",
    "zone/Z27/valve",
    "zone/Z31/valve",
    "zone/Z32/valve",
    "zone/Z33/valve",
    "zone/Z01/window_opening/south",
    "zone/Z03/window_opening/north",
    "zone/Z04/window_opening/north",
    "zone/Z05/window_opening/north",
    "zone/Z11/window_opening/east",
    "zone/Z11/window_opening/south",
    "zone/Z12/window_opening/south",
    "zone/Z13/window_opening/south",
    "zone/Z13/window_opening/west",
    "zone/Z15/window_opening/north",
    "zone/Z15/window_opening/west",
    "zone/Z16/window_opening/north",
    "zone/Z17/window_opening/north",
    "zone/Z21/window_opening/east",
    "zone/Z21/window_opening/sky",
    "zone/Z21/window_opening/south",
    "zone/Z22/window_opening/south",
    "zone/Z23/window_opening/sky",
    "zone/Z23/window_opening/south",
    "zone/Z23/window_opening/west",
    "zone/Z24/window_opening/sky",
    "zone/Z24/window_opening/west",
    "zone/Z25/window_opening/north",
    "zone/Z25/window_opening/sky",
    "zone/Z25/window_opening/west",
    "zone/Z26/window_opening/north",
    "zone/Z27/window_opening/north",
    "zone/Z27/window_opening/sky",
    "zone/Z31/window_opening/sky",
    "zone/Z31/window_opening/south",
    "zone/Z32/window_opening/west",
    "zone/Z33/window_opening/north",
    "zone/Z33/window_opening/sky",
]
Z31_STATES = [
    "zone/Z31/air_temperature",
    "zone/Z31/slab_temperature",
]
Z31_EXTERNALS = [
    "outdoor/weather/air_temperature",
    "outdoor/weather/solar_radiation",
    "zone/Z31/valve",
    "zone/Z31/window_opening/sky",
    "zone/Z31/window_opening/south",
]
Z32_STATES = [
    "zone/Z32/air_temperature",
    "zone/Z32/slab_temperature",
]
Z32_EXTERNALS = [
    "outdoor/weather/air_temperature",
    "outdoor/weather/solar_radiation",
    "zone/Z32/valve",
    "zone/Z32/window_opening/west",
]
if len(sys.argv) > 1:
    z = sys.argv[1]
    if z == "Z31":
        STATES, EXTERNALS = Z31_STATES, Z31_EXTERNALS
    elif z == "Z32":
        STATES, EXTERNALS = Z32_STATES, Z32_EXTERNALS
    else:
        sys.exit(f"fit.py: error: unknown zone {z}")
    ZONE = f"zone/{z}/air_temperature"
    OUT = f"fit.{z}"
else:
    ZONE = "zone/Z31/air_temperature"
    OUT = "fit"
VAL_START = "2025-05-01"
ROLL_CHECK = "2025-01-01"
HIDDEN = 64
NOISE = 0.02
STAGES = [(64, 1500, 1e-3, 128), (256, 1500, 1e-3, 128), (1024, 800, 3e-4, 64),
          (4096, 300, 1e-4, 32)]
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

torch.manual_seed(0)
np.random.seed(0)

df = pd.read_csv("data.csv",
                 index_col=0,
                 usecols=["timestamp"] + STATES + EXTERNALS)
df.index = pd.to_datetime(df.index, utc=True).tz_convert("America/New_York")


def fill(d):
    return (d.replace([np.inf, -np.inf],
                      np.nan).interpolate(method="nearest").ffill().bfill())


v0 = df.index.searchsorted(pd.Timestamp(VAL_START, tz=df.index.tz))
r0 = df.index.searchsorted(pd.Timestamp(ROLL_CHECK, tz=df.index.tz))

Y = fill(df[STATES]).to_numpy()
hol = holidays.US(subdiv="MA", years=[2024, 2025])
hour = df.index.hour + df.index.minute / 60.0
work = ((df.index.weekday < 5) & ~np.isin(df.index.date, sorted(hol.keys())))
U = np.column_stack([
    fill(df[EXTERNALS]).to_numpy(),
    np.sin(2 * np.pi * hour / 24),
    np.cos(2 * np.pi * hour / 24),
    work.astype(float)
])
N = len(Y)

ym, ys = Y[:v0].mean(0), Y[:v0].std(0)
um, us = U[:v0].mean(0), U[:v0].std(0)
us[us == 0.0] = 1.0

j = STATES.index(ZONE)
K = len(STATES)

Yt = torch.tensor((Y - ym) / ys, dtype=torch.float32, device=DEVICE)
Ut = torch.tensor((U - um) / us, dtype=torch.float32, device=DEVICE)
zm, zsd = Yt[:v0].mean(0), Yt[:v0].std(0)
ZN = (Yt - zm) / zsd

cell = nn.LSTMCell(K + U.shape[1], HIDDEN).to(DEVICE)
head = nn.Linear(HIDDEN, K).to(DEVICE)
head.weight.data.zero_()
head.bias.data.zero_()


def ckpt():
    return {"cell": cell.state_dict(), "head": head.state_dict(),
            "ym": torch.tensor(ym), "ys": torch.tensor(ys),
            "um": torch.tensor(um), "us": torch.tensor(us),
            "zm": zm.cpu(), "zsd": zsd.cpu(),
            "states": STATES, "externals": EXTERNALS}


def free_run(z0, useq, noise=0.0):
    z, hc, zs = z0, None, []
    for t in range(useq.shape[1]):
        if noise:
            z = z + noise * torch.randn_like(z)
        hc = cell(torch.cat([z, useq[:, t]], 1), hc)
        z = z + head(hc[0])
        zs.append(z)
    return torch.stack(zs, 1)


def roll_rmse(i0):
    with torch.no_grad():
        zr = free_run(ZN[i0:i0 + 1], Ut[None, i0:N - 1])[0] * zsd + zm
        yv = zr[:, j].cpu().numpy() * ys[j] + ym[j]
    return np.sqrt(np.mean((Y[i0 + 1:, j] - yv)**2))


params = [*cell.parameters(), *head.parameters()]
opt = torch.optim.Adam(params, lr=STAGES[0][2])
for L, steps, lr, B in STAGES:
    for g in opt.param_groups:
        g["lr"] = lr
    for it in range(steps):
        s = torch.randint(0, v0 - L - 1, (B, ), device=DEVICE)
        idx = s[:, None] + torch.arange(L, device=DEVICE)
        loss = ((free_run(ZN[s], Ut[idx], NOISE) - ZN[idx + 1])**2).mean()
        opt.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
        if (it + 1) % 500 == 0:
            print(
                f"fit.py: info: L={L} {it + 1}/{steps}  "
                f"mse {loss.item():.5f}",
                file=sys.stderr,
                flush=True)
    print(
        f"fit.py: info: stage L={L} done  "
        f"val-month {roll_rmse(v0):.2f} F  "
        f"jan-roll {roll_rmse(r0):.2f} F",
        file=sys.stderr,
        flush=True)
    torch.save(ckpt(), f"{OUT}.{L}.pt")
    print(f"fit.py: info: saved {OUT}.{L}.pt", file=sys.stderr, flush=True)
torch.save(ckpt(), f"{OUT}.pt")

rmse = roll_rmse(0)
print(
    f"fit.py: info: {ZONE}  year roll = {rmse:.2f} F   "
    f"val month = {roll_rmse(v0):.2f} F   "
    f"jan-roll = {roll_rmse(r0):.2f} F",
    file=sys.stderr,
    flush=True)
print(f"fit.py: info: saved {OUT}.pt", file=sys.stderr, flush=True)
