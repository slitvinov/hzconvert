# LiveLab Modelica Model

A Modelica/Buildings model of the LiveLab room at HouseZero. The room is
a small (8.18 m²) experimental office on the third floor with a pitched
roof, three windows including a skylight, and TABS radiant slab heating.
The model is single-zone and produces an FMU with about 17,000 named
variables, but the actual ODE has only 73 state variables. LiveLab
corresponds to dataset zone Z31 (third-floor south office with operable
South wall window and West-tilted skylight); compare with `Indoor
Sensors/.../Zone_temp_hourly/...csv` column `Z31_temp`. Identification is
based on `data/System Sensors/.../Window_opening_hourly`: only Z31 has
`Z31_S_opening + Z31_Sky_opening` matching the model's `azi = {S, W, W}`
with one Tilt.Ceiling. Z32 has only a West opening; Z33 has North + Sky.

The Modelica file is `livelab.mo`. The default weather file is
`resources/tmy3.mos` (canonical full-year Boston TMY3). At runtime you
can override `p_weather_file` to `resources/winter.mos` (cold months
Nov to Feb only, assembled as a stress test) or any other path. Build
the FMU with
`omc fmu.mos` (about 4 min on Apple Silicon); build a standalone
simulation executable with `omc build.mos`. Generate the runtime
weather file with
`python resources/mos_to_mat.py resources/tmy3.mos resources/tmy3.mat`
(not checked in). Run the FMU from the directory containing the
`.mat`, or pass an absolute path via `p_weather_file`.

The room is conceptually:

```
                ┌── pitched roof (E + W slopes, 45°) ──┐
                │   1 skylight in W-facing slope        │
                │                                       │
   south wall ──┤    LiveLab zone, 8.18 m²              ├── west wall
   (1 window) ──┤    Air, CO₂, RH                       ├── (1 window)
                │                                       │
                └─── TABS radiant slab ─────────────────┘
                              │
                       water in/out (controlled)
```

External inputs and outputs:

```
  symbol           default   range         what it does
  u_win_angle      15.0      0 to 90 deg   window opening, drives natural ventilation through var_cd
  u_occupancy      0.5       0 to 1        occupancy fraction, drives internal heat gain (~120 W/person)
  out_vent_flow                            natural ventilation mass flow into the zone, kg/s, negative = inflow
  out_time                                 simulation time, passthrough
```

The sensors you read via the FMU's `output` argument:

```
  sn_temp_zone.T         zone air temperature, K
  sn_co2_zone.ppm        zone CO2 concentration, ppm
  sn_rh_zone.phi         zone relative humidity, 0 to 1
  sn_temp_slab.T         slab surface temperature, K
  sn_temp_water_ret.T    TABS return-water temperature, K
  sn_temp_vent.T         outdoor air temperature at vent inlet, K
  sn_rh_vent.phi         outdoor air relative humidity at vent inlet, 0 to 1
```

Most-impactful tunable parameters (set at runtime via
`start_values={...}`; every `parameter` in the model is reachable, but
these are the ones that matter for calibration):

```
  parameter             default        what it controls
  p_weather_file        "resources/tmy3.mos"   weather file path (relative to FMU cwd)
  mat_insul.x           0.087 m        insulation thickness, biggest envelope knob
  mat_insul.k           0.049 W/m/K    insulation conductivity
  ctrl_temp_water.k     295.15 K       TABS water setpoint
  ctrl_mflow_water.k    0.02 kg/s      TABS water flow rate
  ctrl_gain_co2.k       0              per-occupant CO2 emission rate. Set to ~5e-6 to enable CO2 (default disables it)
  p_cd_rect             0.62           window discharge coefficient (rectangular reference)
  p_cp_base             0.6            base wind pressure coefficient (Swami & Chandra)
```

Geometry (taken from `livelab.mo`):

```
  AFlo (floor area)         8.18 m^2
  hRoo (ceiling height)     3.84 m
  roof pitch                45 deg (E + W slopes)
  south window              1.45 x 1.58 m
  west wall window          0.885 x 1.07 m
  skylight (W-facing)       0.885 x 1.07 m
  nConExt                   2 (E, W roof slopes)
  nConExtWin                3 (2 wall + 1 ceiling)
  nConBou                   6 (interior partitions)
  nSurBou                   1 (slab interface)
```

The 73 state variables come mostly from temperatures inside construction
layers (walls, glazing, slab). Conceptually they break down into: zone
air (4: internal energy U, mass m, CO2 mass mC[1], water-vapor fraction
Xi[1]; relative humidity is derived, not independent), construction
temperatures (about 60: per-layer temperatures for each of the surfaces,
which together provide the building's thermal mass and time lags), slab
(about 7: water energy plus slab-layer temperatures), and a few small
internal sensor states. The FMU exposes thousands of additional
`calculatedParameter` entries that are derived quantities Buildings
precomputes at initialization (radiation view factors, glazing optics,
per-layer thermal coefficients, etc.); these don't add dynamics, just
bloat the FMU XML.

The natural ventilation is a hybrid of three sources, not a clean
implementation of any one paper.

Mean ventilation flow rate, Wang & Chen 2012 Eq. (15):

```
                          h
                         ⌠
                         ⎮         2/7     2/7
       Cd sqrt(Cp) Ubar l⎮   sqrt(z    - z0   ) dz
                         ⎮
                         ⌡
                          z0
Qbar = ──────────────────────────────────────────────
                              1/7
                         z_ref
```

The integral is computed once via `quadratureLobatto` on the function
`f_nv` between window mid-height and top. Compared with the paper, the
code adds three engineering tweaks: an air-density factor of 1.2 to
convert volumetric to mass flow, a sign flip for inward-flow
convention, and a min-clamp at -0.00366 kg/s to model baseline
infiltration.

Window discharge coefficient `var_cd`, Wang & Chen 2015 Eq. (5) for
hopper windows:

```
paper:
                  Cd_conv sqrt(sin(alpha/2))
   min ( 1 , ──────────────────────────────── )
                          Cd_rec

code:
                  0.92  sqrt(sin(alpha))
   min ( 1 , ─────────────────────────────── )
                     0.62  sqrt(2)
```

The code differs from the paper by parenthesis placement
(`sin(alpha)/2` vs `sin(alpha/2)`). The two forms agree at small angles
and diverge at large ones:

```
  alpha     sin(alpha)/2    sin(alpha/2)
  15 deg     0.129           0.131
  45 deg     0.354           0.383
  90 deg     0.500           0.707
```

Wind pressure coefficient `var_cp` does NOT come from Wang & Chen; it
is the Swami & Chandra 1988 ASHRAE empirical formula for low-rise
buildings:

Cp / Cp_base =

```
             3                       2                2    2 theta              theta
log(0.131 sin (2 G theta) - 1.175 sin (theta) + 0.07 G  sin (─────) - 0.703 sin(─────)
                                                               2                  2
                                              2 theta              theta
                                   + 0.717 cos (─────) + 0.769 cos(─────) + 1.248)
                                                  2                  2
```

where theta is the wind incidence angle and G is the building side
ratio (in the code, `p_log_aspect = log(0.85165)`). All seven
trigonometric coefficients match Swami & Chandra exactly.

Things deliberately NOT in the model: there is no HVAC controller, TABS
water flow and temperature are held constant, no setpoint tracking, so
simulated zone temperature drifts wherever the physics takes it (real
Z31 maintains 22 deg C because of an actual TABS controller that this
model omits). There are no lighting or equipment loads beyond occupancy
heat gain. Interior shade dynamics are absent (`ctrl_shade` is hardcoded
to 1). CO2 generation is wired up but disabled by `ctrl_gain_co2.k = 0`
(override at runtime to enable).