import subprocess
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fmpy import simulate_fmu

FMU = "livelab.fmu"
DAY = 86400.0
INK = "#1a1a19"
C1 = "#2a78d6"
C2 = "#eb6834"
C3 = "#1baf7a"
C4 = "#eda100"

def show(p):
    if sys.platform == "darwin":
        subprocess.run(["open", p], check=False)


OUT = ["sn_temp_zone.T", "sn_temp_slab.T", "sn_temp_vent.T",
       "sn_rh_zone.phi", "sn_co2_zone.ppm", "out_vent_flow",
       "wth_bus.HGloHor", "wth_bus.winSpe", "var_cd"]


def run(start, stop, win, occ, step=600, **kw):
    inp = np.array([(start, win, occ), (stop, win, occ)],
                   dtype=[("time", "f8"), ("u_win_angle", "f8"),
                          ("u_occupancy", "f8")])
    return simulate_fmu(FMU, start_time=start, stop_time=stop,
                        output_interval=step, input=inp, output=OUT,
                        relative_tolerance=1e-8, **kw)


def hours(r, start):
    return (r["time"] - start) / 3600.0


def panel(ax, title, ylab):
    ax.set_title(title, color=INK, fontsize=10)
    ax.set_ylabel(ylab, color=INK, fontsize=9)
    ax.tick_params(colors=INK, labelsize=8)
    ax.grid(alpha=0.25, lw=0.6)
    for s in ax.spines.values():
        s.set_color("#c9ccd0")


def main():
    summer = 200 * DAY
    winter = 20 * DAY

    s = run(summer, summer + 3 * DAY, 15.0, 1.0,
            start_values={"ctrl_gain_co2.k": 5e-6})
    w = run(winter, winter + 3 * DAY, 0.0, 0.5)

    fig, axs = plt.subplots(2, 2, figsize=(11, 7), facecolor="white")

    ax = axs[0][0]
    ax.plot(hours(s, summer), s["sn_temp_zone.T"] - 273.15, color=C1, lw=2,
            label="zone air")
    ax.plot(hours(s, summer), s["sn_temp_slab.T"] - 273.15, color=C2, lw=2,
            label="slab surface")
    ax.plot(hours(s, summer), s["sn_temp_vent.T"] - 273.15, color=C3, lw=1.5,
            ls="--", label="outdoor")
    panel(ax, "summer, window 15 deg, 1 occupant", "deg C")
    ax.legend(frameon=False, fontsize=8, labelcolor=INK)

    ax = axs[0][1]
    ax.plot(hours(w, winter), w["sn_temp_zone.T"] - 273.15, color=C1, lw=2,
            label="zone air")
    ax.plot(hours(w, winter), w["sn_temp_slab.T"] - 273.15, color=C2, lw=2,
            label="slab surface")
    ax.plot(hours(w, winter), w["sn_temp_vent.T"] - 273.15, color=C3, lw=1.5,
            ls="--", label="outdoor")
    panel(ax, "winter, window shut, 0.5 occupant", "deg C")
    ax.legend(frameon=False, fontsize=8, labelcolor=INK)

    ax = axs[1][0]
    ax.plot(hours(s, summer), s["sn_co2_zone.ppm"], color=C4, lw=2)
    panel(ax, "zone CO2, summer run (ctrl_gain_co2.k = 5e-6)", "ppm")
    ax.set_xlabel("hours", color=INK, fontsize=9)

    ax = axs[1][1]
    ax.plot(hours(s, summer), -s["out_vent_flow"], color=C3, lw=2)
    panel(ax, "natural ventilation inflow, window 15 deg", "kg/s")
    ax.set_xlabel("hours", color=INK, fontsize=9)

    fig.suptitle("LiveLab FMU, free-running (no thermostat), Boston TMY3",
                 color=INK, fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig("sim_overview.png", dpi=160)
    show("sim_overview.png")

    ang = [0.0, 5.0, 15.0, 30.0, 60.0, 90.0]
    fig2, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4), facecolor="white")
    peak, flow = [], []
    for a in ang:
        r = run(summer, summer + 2 * DAY, a, 1.0)
        t = r["sn_temp_zone.T"] - 273.15
        peak.append(t.max())
        flow.append(float(np.mean(-r["out_vent_flow"])))
        a1.plot(hours(r, summer), t, lw=1.8, label="%g deg" % a)
    panel(a1, "zone air vs window opening angle", "deg C")
    a1.set_xlabel("hours", color=INK, fontsize=9)
    a1.legend(frameon=False, fontsize=8, ncol=2, labelcolor=INK)

    a2.plot(ang, flow, color=C1, lw=2, marker="o", ms=5)
    panel(a2, "mean ventilation inflow vs angle", "kg/s")
    a2.set_xlabel("window angle, deg", color=INK, fontsize=9)

    fig2.suptitle("Window-opening sweep, 2 summer days", color=INK, fontsize=12)
    fig2.tight_layout(rect=(0, 0, 1, 0.93))
    fig2.savefig("sim_window_sweep.png", dpi=160)
    show("sim_window_sweep.png")

    print("peak zone air temperature, deg C")
    for a, p, f in zip(ang, peak, flow):
        print("  %5.1f deg  %6.2f  %8.5f kg/s" % (a, p, f))
    print("wrote sim_overview.png sim_window_sweep.png")


main()
