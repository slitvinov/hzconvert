import numpy as np
from fmpy import simulate_fmu

FMU   = "livelab.fmu"
START = 200 * 86400.0
STOP  = START + 86400.0

inputs = np.array(
    [(START, 15.0, 1.0), (STOP, 15.0, 1.0)],
    dtype=[("time", "f8"), ("u_win_angle", "f8"), ("u_occupancy", "f8")],
)

result = simulate_fmu(
    FMU,
    start_time=START,
    stop_time=STOP,
    output_interval=3600,
    input=inputs,
    output=["sn_temp_zone.T", "sn_co2_zone.ppm", "sn_rh_zone.phi"],
    start_values={"ctrl_gain_co2.k": 5e-6},
    relative_tolerance=1e-8,
)

print(f"{'h':>4} {'T-20':>6} {'CO2-400':>9} {'RH':>5}")
for row in result:
    h   = int((row["time"] - START) / 3600)
    T   = row["sn_temp_zone.T"] - 293.15
    co2 = row["sn_co2_zone.ppm"]
    rh  = row["sn_rh_zone.phi"]
    print(f"{h:>4d} {T:>+6.1f} {co2:>+9.0f} {rh:>5.1f}")
