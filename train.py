# ---
# jupyter:
#   jupytext:
#     formats: py:percent,ipynb
#     text_representation:
#       extension: .py
#       format_name: percent
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # HouseZero single-zone twin
# <https://github.com/slitvinov/hzconvert>

# %%
import os
import sys
import subprocess

if "google.colab" in sys.modules:
    subprocess.run(["pip", "-q", "install", "holidays", "matplotlib"],
                   check=True)
    if not os.path.exists("bootstrap.sh"):
        if not os.path.isdir("hzconvert"):
            subprocess.run(["git", "clone", "-q",
                            "https://github.com/slitvinov/hzconvert"],
                           check=True)
        os.chdir("hzconvert")

if not os.path.exists("data.csv"):
    subprocess.run(["./bootstrap.sh"], check=True)

# %%
ZONE = "Z31"
VAL_START = "2025-05-01"
HIDDEN = 64
NOISE = 0.02
QUICK = False
STAGES = ([(64, 200, 1e-3, 64), (256, 200, 1e-3, 64)] if QUICK else
          [(64, 1500, 1e-3, 128), (256, 1500, 1e-3, 128),
           (1024, 800, 3e-4, 64), (4096, 300, 1e-4, 32)])

STATES = [
    f"zone/{ZONE}/air_temperature",
    f"zone/{ZONE}/slab_temperature",
]
EXTERNALS = [
    "outdoor/weather/air_temperature",
    "outdoor/weather/solar_radiation",
    "tabs/Z31/supply_temperature",
    "outdoor/weather/wind_speed",
    "outdoor/weather/wind_direction/sin",
    "outdoor/weather/wind_direction/cos",
    f"zone/{ZONE}/valve",
    f"zone/{ZONE}/window_opening/sky",
    f"zone/{ZONE}/window_opening/south",
]

# %%
import holidays
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

torch.manual_seed(0)
np.random.seed(0)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

WD = "outdoor/weather/wind_direction"
RAW = [e for e in EXTERNALS if not e.startswith(WD + "/")]

df = pd.read_csv("data.csv", index_col=0,
                 usecols=["timestamp"] + STATES + RAW + [WD])
df.index = pd.to_datetime(df.index, utc=True).tz_convert("America/New_York")


def fill(d):
    return (d.replace([np.inf, -np.inf], np.nan)
             .interpolate(method="nearest").ffill().bfill())


theta = np.deg2rad(fill(df[WD]))
df[WD + "/sin"] = np.sin(theta)
df[WD + "/cos"] = np.cos(theta)

v0 = df.index.searchsorted(pd.Timestamp(VAL_START, tz=df.index.tz))

Y = fill(df[STATES]).to_numpy()
hol = holidays.US(subdiv="MA", years=[2024, 2025])
hour = df.index.hour + df.index.minute / 60.0
work = (df.index.weekday < 5) & ~np.isin(df.index.date, sorted(hol.keys()))
U = np.column_stack([
    fill(df[EXTERNALS]).to_numpy(),
    np.sin(2 * np.pi * hour / 24),
    np.cos(2 * np.pi * hour / 24),
    work.astype(float),
])

ym, ys = Y[:v0].mean(0), Y[:v0].std(0)
um, us = U[:v0].mean(0), U[:v0].std(0)
us[us == 0.0] = 1.0

K, N = len(STATES), len(Y)
Z = torch.tensor((Y - ym) / ys, dtype=torch.float32, device=DEVICE)
Ut = torch.tensor((U - um) / us, dtype=torch.float32, device=DEVICE)
print(N, "minutes,", K, "states,", U.shape[1], "inputs, held out", N - v0)

# %%
cell = nn.LSTMCell(K + U.shape[1], HIDDEN).to(DEVICE)
head = nn.Linear(HIDDEN, K).to(DEVICE)
head.weight.data.zero_()
head.bias.data.zero_()
params = [*cell.parameters(), *head.parameters()]


def free_run(z0, useq, noise=0.0):
    z, hc, out = z0, None, []
    for t in range(useq.shape[1]):
        if noise:
            z = z + noise * torch.randn_like(z)
        hc = cell(torch.cat([z, useq[:, t]], 1), hc)
        z = z + head(hc[0])
        out.append(z)
    return torch.stack(out, 1)


# %%
import time

opt = torch.optim.Adam(params, lr=STAGES[0][2])
t0 = time.time()
for L, steps, lr, B in STAGES:
    for g in opt.param_groups:
        g["lr"] = lr
    for i in range(steps):
        s = torch.randint(0, v0 - L - 1, (B,), device=DEVICE)
        idx = s[:, None] + torch.arange(L, device=DEVICE)
        loss = ((free_run(Z[s], Ut[idx], NOISE) - Z[idx + 1]) ** 2).mean()
        opt.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
    print("L=%d loss %.5f (%.0f s)" % (L, loss.item(), time.time() - t0))

# %%
j = STATES.index(f"zone/{ZONE}/air_temperature")
with torch.no_grad():
    pred = free_run(Z[0:1], Ut[None, :N - 1])[0, :, j].cpu().numpy()
pred = pred * ys[j] + ym[j]
meas = Y[1:, j]


def rmse(a, b):
    return float(np.sqrt(np.mean((a - b) ** 2)))


print("year %.2f F, held out %.2f F"
      % (rmse(meas, pred), rmse(meas[v0:], pred[v0:])))

# %%
torch.save({"cell": cell.state_dict(), "head": head.state_dict(),
            "ym": torch.tensor(ym), "ys": torch.tensor(ys),
            "um": torch.tensor(um), "us": torch.tensor(us),
            "states": STATES, "externals": EXTERNALS},
           f"notebook.{ZONE}.pt")

# %%
import matplotlib.pyplot as plt

t = df.index[1:]
m = t >= pd.Timestamp(VAL_START, tz=t.tz)
fig, ax = plt.subplots(2, 1, figsize=(11, 5))
for a, sel, lw in ((ax[0], slice(None), 0.4), (ax[1], m, 0.7)):
    a.plot(t[sel], meas[sel], color="0.35", lw=lw, label="measured")
    a.plot(t[sel], pred[sel], color="#D8232A", lw=lw, label="twin, free run")
    a.set_ylabel("deg F")
    a.legend(loc="upper right", fontsize=8, ncol=2)
ax[0].set_title(f"{ZONE} air temperature, free run")
ax[1].set_title("held-out month")
fig.tight_layout()
plt.show()
