"""Reproduce Figs 6-18 from Han et al. 2024 (HouseZero data
descriptor, https://doi.org/10.1038/s41597-024-03770-7) from data.csv,
with the paper's example dates shifted into this dataset's June 2024 -
May 2025 year.  Writes PNGs to han_figs/.  Ported from hz/code."""

from pathlib import Path
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

DST = Path("han_figs")
DST.mkdir(exist_ok=True)

units = dict(pd.read_csv("rubric.tsv", sep="\t").iloc[:, :2].values)
df = pd.read_csv("data.csv", index_col=0)
df.index = pd.to_datetime(df.index, utc=True).tz_convert("America/New_York")
df = df.resample("h").mean()
for c in df.columns:
    if units.get(c) == "F":
        df[c] = (df[c] - 32) * 5 / 9

# Tell matplotlib to label tz-aware axes in the dataset's local tz
# (otherwise tick labels print UTC and "00:00 EST" looks like "05:00").
mpl.rcParams["timezone"] = str(df.index.tz)


def save(fig, name):
    p = DST / name
    fig.tight_layout()
    fig.savefig(p, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {p}")


def day_slice(date_str, hours=24):
    t0 = pd.Timestamp(date_str, tz=df.index.tz)
    t1 = t0 + pd.Timedelta(hours=hours)
    return df.loc[t0:t1]


# loads/* category groups (paper labels), in ALPHABETICAL key order so
# pandas's default tab10 cycle assigns colours the way the paper's
# Figs 9 & 10 do: Control=blue, Cooling=orange, DHW=green, Heat Pump=red,
# IT=purple, Lighting=brown, Others=pink, Plug_Total=gray.
# Conventions:
#   - "Lighting" is main lighting (all floors); emergency_lighting is
#     in Others.
#   - "Heat Pump" is the whole heat-pump system: compressor electric +
#     mechanical (circulation).
LOAD_CATS = {
    "Control": ["load/controls"],
    "Cooling": ["load/cooling_pump"],
    "DHW": ["load/dhw/electric", "load/dhw/solar"],
    "Heat Pump": ["load/heat_pump", "load/heat_pump_mechanical"],
    "IT": ["load/it"],
    "Lighting": [
        "load/lighting/basement", "load/lighting/floor1",
        "load/lighting/floor2", "load/lighting/floor3"
    ],
    "Others": [
        "load/battery_cabinet", "load/elevator", "load/exhaust_fan",
        "load/fire_alarm", "load/sump_pump", "load/solar_rapid_shutdown",
        "load/emergency_lighting"
    ],
    "Plug_Total": [
        "load/plug/basement", "load/plug/floor1", "load/plug/floor2",
        "load/plug/floor3"
    ],
}


def cat_sum(df_, cols):
    have = [c for c in cols if c in df_.columns]
    return df_[have].sum(axis=1, min_count=1)


# CO2 / RH zone column lists from the paper Figs 12 & 13
ZONE_LIST = [
    "Z11", "Z12_Z13", "Z15_Z16", "Z17", "Z01", "Z21", "Z22_Z23", "Z24",
    "Z25_Z26_Z27", "Z31", "Z32", "Z33", "Z03", "Z04", "Z05"
]

# Best ambient outdoor proxy: mean of the four `_high` facade sensors
# (N/S/E/W). The weather-station air sensor is sun-exposed and reads
# ~5 C hotter than the paper's outdoor curve.
HIGH_FACADES = [
    "outdoor/facade/north/high", "outdoor/facade/south/high",
    "outdoor/facade/east/high", "outdoor/facade/west/high_right"
]


def outdoor_temp(d):
    return d[HIGH_FACADES].mean(axis=1)


# ---------- Fig 6: zone temperature, full year ------------------------
# Paper Fig 6 shows pre-filter raw data with red outlier markers.  We
# only have the cleaned data, so we just plot the clean trace.
def fig6():
    s = df["zone/Z22_Z23/air_temperature"].loc["2024-06-01":"2025-05-31"]
    ax = pd.DataFrame({"Data": s}).plot(figsize=(9, 3.5), color="0.4", lw=0.5)
    ax.set_ylim(0, 30)
    ax.set_ylabel("Temperature (\N{DEGREE SIGN}C)")
    ax.set_xlabel("Time")
    ax.legend(loc="upper right")
    save(ax.figure, "fig_06_outlier_zscore.png")


# ---------- Fig 7: zone temperature, summer window --------------------
def fig7():
    s = df["zone/Z21/air_temperature"].loc["2024-07-19":"2024-07-31"]
    ax = pd.DataFrame({"Data": s}).plot(figsize=(9, 3.5), color="0.4", lw=0.6)
    ax.set_xlabel("Time")
    ax.set_ylabel("Temperature (\N{DEGREE SIGN}C)")
    ax.legend(loc="upper left")
    save(ax.figure, "fig_07_repetition_filter.png")


# ---------- Fig 8: pie chart, annual breakdown ------------------------
PIE_ORDER = [
    "IT", "Plug load", "Others", "Controls", "Lighting", "DHW", "Cooling",
    "Heating"
]
PIE_COLOR = {
    "IT": "#F5CBA7",
    "Plug load": "#ABEBC6",
    "Others": "#909497",
    "Controls": "#F8D7DA",
    "Lighting": "#F8C471",
    "DHW": "#FAD7A0",
    "Cooling": "#AED6F1",
    "Heating": "#F1948A",
}
PIE_CATS = {
    "IT": LOAD_CATS["IT"],
    "Plug load": LOAD_CATS["Plug_Total"],
    "Others": LOAD_CATS["Others"],
    "Controls": LOAD_CATS["Control"],
    "Lighting": LOAD_CATS["Lighting"],
    "DHW": LOAD_CATS["DHW"],
    "Cooling": LOAD_CATS["Cooling"],
    "Heating": LOAD_CATS["Heat Pump"],
}


def fig8():
    fig, ax = plt.subplots(figsize=(5.5, 5))
    ydf = df.loc["2024-06-01":"2025-05-31"]
    sizes = [cat_sum(ydf, PIE_CATS[k]).sum() for k in PIE_ORDER]
    ax.pie(sizes,
           labels=PIE_ORDER,
           colors=[PIE_COLOR[k] for k in PIE_ORDER],
           autopct="%.0f%%",
           startangle=90,
           counterclock=False,
           textprops={"fontsize": 9})
    ax.set_title("June 2024 - May 2025")
    save(fig, "fig_08_pie_breakdown.png")


# ---------- Fig 9 / Fig 10: daily electricity end uses ----------------
def fig_daily_loads(date_str, name, title_suffix):
    d = day_slice(date_str)
    parts = pd.DataFrame(
        {lab: cat_sum(d, cols)
         for lab, cols in LOAD_CATS.items()})
    ax = parts.plot(figsize=(9, 3.8), marker=".", ms=3, lw=0.8)
    ax.set_ylabel("Loads (kWh)")
    ax.set_xlabel("Time")
    ax.set_title(title_suffix)
    save(ax.figure, name)


# ---------- Fig 11: BTU energy by zone, winter day ---------------------
def fig11(date_str="2025-01-13"):
    d = day_slice(date_str)
    btu_cols = {
        "BTU10(Z21+22+23+24+25+26+27)_energy (kBTU/h)":
        "tabs/Z21_Z22_Z23_Z24_Z25_Z26_Z27/energy",
        "BTU11(Z32+33)_energy (kBTU/h)": "tabs/Z32_Z33/energy",
        "BTU13(Z31)_energy (kBTU/h)": "tabs/Z31/energy",
        "BTU5(Z2+3+4+5)_energy (kBTU/h)": "tabs/Z02_Z03_Z04_Z05/energy",
        "BTU6(Z1)_energy (kBTU/h)": "tabs/Z01/energy",
        "BTU7(Z14+15+16+17)_energy (kBTU/h)": "tabs/Z14_Z15_Z16_Z17/energy",
        "BTU8(Z11+12+13)_energy (kBTU/h)": "tabs/Z11_Z12_Z13/energy",
    }
    sub = d[list(btu_cols.values())].rename(
        columns={v: k
                 for k, v in btu_cols.items()})
    ax = sub.plot(figsize=(9, 4), marker=".", ms=3, lw=0.8)
    ax.set_ylabel("BTU Energy (kBTU/h)")
    ax.set_xlabel("Time")
    ax.legend(fontsize=7)
    save(ax.figure, "fig_11_btu_winter.png")


# ---------- Fig 12: CO2 daily summer -----------------------------------
def fig12(date_str="2024-08-10"):
    d = day_slice(date_str)
    cols = [f"zone/{z}/co2" for z in ZONE_LIST if f"zone/{z}/co2" in d.columns]
    sub = d[cols].rename(
        columns={c: f"{c.split('/')[1]}_CO2 (ppm)"
                 for c in cols})
    ax = sub.plot(figsize=(9, 4), marker=".", ms=3, lw=0.7)
    ax.set_ylabel("CO2 Concentration (ppm)")
    ax.set_xlabel("Time")
    ax.legend(fontsize=6, ncol=1)
    save(ax.figure, "fig_12_co2_summer.png")


# ---------- Fig 13: RH daily summer ------------------------------------
def fig13(date_str="2024-08-10"):
    d = day_slice(date_str)
    cols = [
        f"zone/{z}/humidity" for z in ZONE_LIST
        if f"zone/{z}/humidity" in d.columns
    ]
    sub = d[cols].rename(
        columns={c: f"{c.split('/')[1]}_RH (%)"
                 for c in cols})
    ax = sub.plot(figsize=(9, 4), marker=".", ms=3, lw=0.7)
    ax.set_ylabel("Relative Humidity (%)")
    ax.set_xlabel("Time")
    ax.legend(fontsize=6, ncol=3)
    save(ax.figure, "fig_13_rh_summer.png")


# ---------- Fig 14: nat-vent passive mode (triple y-axis) --------------
def fig14():
    d = df.loc["2025-05-21":"2025-05-31"]
    fig, ax = plt.subplots(figsize=(9, 4))
    l1, = ax.plot(d.index,
                  d["outdoor/weather/air_temperature"],
                  color="C0",
                  lw=0.9,
                  label="Outdoor Air Temperature")
    l2, = ax.plot(d.index,
                  d["zone/Z22_Z23/air_temperature"],
                  color="C2",
                  lw=0.9,
                  label="Zone Temperature")
    ax.set_ylabel("Temperature (\N{DEGREE SIGN}C)")
    ax.set_xlabel("Date")
    ax.set_ylim(0, 35)
    ax2 = ax.twinx()
    win = d.filter(regex=r"^zone/Z2[23]/window_opening").mean(axis=1)
    l3, = ax2.plot(d.index,
                   win,
                   color="C1",
                   ls=":",
                   lw=0.9,
                   label="Window Opening")
    ax2.set_ylabel("Window Opening (%)")
    ax2.set_ylim(0, 100)
    ax3 = ax.twinx()
    ax3.spines["right"].set_position(("outward", 55))
    l4, = ax3.plot(d.index,
                   d["zone/Z22_Z23/co2"],
                   color="C3",
                   ls="--",
                   lw=0.9,
                   label="Indoor CO2 Concentration")
    ax3.set_ylabel("Indoor CO2 Concentration (ppm)")
    ax3.set_ylim(0, 2000)
    ax.legend(handles=[l1, l2, l3, l4], fontsize=8)
    save(fig, "fig_14_natvent_may2025.png")


# ---------- Fig 15: monthly PV -----------------------------------------
def fig15():
    d = df.loc["2024-06-01":"2025-05-31"]
    pv = d["pv/meter1"].fillna(0) + d["pv/meter2"].fillna(0)  # kW, hourly
    sr = d["outdoor/weather/solar_radiation"]  # W/m^2
    pv_m = pv.resample("ME").sum()  # kWh
    sr_m = sr.resample("ME").sum() / 1000.0  # kWh/m^2
    fig, ax = plt.subplots(figsize=(9, 4))
    months = pv_m.index.strftime("%b")
    ax.bar(months,
           pv_m.values,
           color="C0",
           alpha=0.7,
           label="PV Production (kWh)")
    ax.set_ylabel("PV Production (kWh)")
    ax.set_xlabel("Month")
    ax2 = ax.twinx()
    ax2.plot(months,
             sr_m.values,
             color="red",
             marker="o",
             ls="--",
             lw=1.0,
             label="Solar_Rad")
    ax2.set_ylabel("Solar Radiation (kWh/m\N{SUPERSCRIPT TWO})")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8)
    ax.set_title("June 2024 - May 2025")
    save(fig, "fig_15_monthly_pv.png")


# ---------- Fig 16 / 17: TABS Z23 summer / winter day ------------------
def _tabs_day(date_str):
    d = day_slice(date_str, hours=24)
    pairs = [
        ("Zone 23 Temperature", "zone/Z22_Z23/air_temperature"),
        ("Zone 23 Slab Temperature", "zone/Z23/slab_temperature"),
        ("TABS Supply Temperature",
         "tabs/Z21_Z22_Z23_Z24_Z25_Z26_Z27/supply_temperature"),
        ("TABS Return Temperature",
         "tabs/Z21_Z22_Z23_Z24_Z25_Z26_Z27/return_temperature"),
    ]
    sub = pd.DataFrame({"Outdoor Temperature": outdoor_temp(d)})
    for label, col in pairs:
        sub[label] = d[col]
    return sub


def fig16(date_str="2024-08-06"):
    ax = _tabs_day(date_str).plot(figsize=(9, 4), marker=".", ms=4, lw=0.9)
    ax.set_ylabel("Temperature (\N{DEGREE SIGN}C)")
    ax.set_xlabel("Time")
    save(ax.figure, "fig_16_tabs_z23_summer.png")


def fig17(date_str="2024-12-21"):
    ax = _tabs_day(date_str).plot(figsize=(9, 4), marker=".", ms=4, lw=0.9)
    ax.set_ylabel("Temperature (\N{DEGREE SIGN}C)")
    ax.set_xlabel("Time")
    save(ax.figure, "fig_17_tabs_z23_winter.png")


# ---------- Fig 18: heat pump operation, winter day --------------------
# Paper plots House-Side / Geo-Side supply & return temps + heat-pump
# electric load on a secondary y-axis.  The House-Side sensors aren't
# in the released CSVs, so this is a partial repro.
def fig18(date_str="2024-12-21"):
    d = day_slice(date_str, hours=24)
    fig, ax = plt.subplots(figsize=(9, 4))
    l1, = ax.plot(d.index,
                  d["geo/well_common/supply_temperature"],
                  color="C0",
                  lw=0.9,
                  marker=".",
                  ms=4,
                  label="Geo Loop Supply Temperature")
    l2, = ax.plot(d.index,
                  d["geo/well_common/return_temperature"],
                  color="C1",
                  lw=0.9,
                  marker=".",
                  ms=4,
                  label="Geo Loop Return Temperature")
    ax.set_ylabel("Temperature (\N{DEGREE SIGN}C)")
    ax.set_xlabel("Time")
    ax2 = ax.twinx()
    hp = (d["load/heat_pump"].fillna(0) +
          d["load/heat_pump_mechanical"].fillna(0))
    l3, = ax2.plot(d.index,
                   hp.values,
                   color="C4",
                   lw=1.2,
                   marker=".",
                   ms=4,
                   label="Heat Pump (kWh)")
    ax2.set_ylabel("Heat Pump Electric Load (kWh)")
    ax2.set_ylim(0, max(1.0, hp.max() * 1.1 if hp.notna().any() else 1.0))
    ax.legend(handles=[l1, l2, l3], fontsize=8)
    ax.set_title("Partial repro; House-Side T sensors are not released")
    save(fig, "fig_18_heatpump_winter.png")


print("rendering figs to", DST)
fig6()
fig7()
fig8()
fig_daily_loads("2024-08-25", "fig_09_loads_summer.png",
                "Daily pattern of electricity end uses, summer day")
fig_daily_loads("2024-12-20", "fig_10_loads_winter.png",
                "Daily pattern of electricity end uses, winter day")
fig11()
fig12()
fig13()
fig14()
fig15()
fig16()
fig17()
fig18()
