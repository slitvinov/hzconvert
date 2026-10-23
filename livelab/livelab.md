# LiveLab Modelica model: detailed reference

`README.md` in this directory is the entry point: what the model is, the
geometry, the component table with line links, the inputs and outputs,
how to build and run, and the simulation figures. This file is the
reference behind it and does not repeat those: the ventilation
derivations and where the code departs from the papers, the
state-variable breakdown, the full parameter, interface and material
tables. Ground truth is `livelab.mo`, 179 lines. The Maxima files in
`resources/` carry the symbolic form of each equation discussed here:
`qbar.mac`, `qmass.mac`, `vent_area.mac`, `cd.mac`, `cp.mac`.

## Which zone this is

LiveLab corresponds to dataset zone Z31, the third-floor south office
with an operable South wall window and a West-tilted skylight; compare
with `Indoor Sensors/.../Zone_temp_hourly/...csv` column `Z31_temp`.
Identification is from `data/System Sensors/.../Window_opening_hourly`:
only Z31 has `Z31_S_opening + Z31_Sky_opening` matching the model's
`azi = {S, W, W}` with one `Tilt.Ceiling`. Z32 has only a West opening;
Z33 has North + Sky.

## Building

Run from this directory. `omc resources/fmu.mos` produces `livelab.fmu`,
about 3.0 MB, FMI 2.0 co-simulation, built with
`--fmiFlags=s:cvode --fmiSources=false`; a few minutes on Apple Silicon.
`omc resources/build.mos` instead checks the model and builds a
standalone simulation executable. Confirmed with `omc`
v1.27.0-dev-418-gdd34633c74 on macOS arm64.

The Buildings library must come from the fork
https://github.com/slitvinov/modelica-buildings, not from the
OpenModelica package index. `resources/buildings.mos` resolves it: it
uses `$BUILDINGS_DIR` if set and otherwise
`~/hz/forks/modelica-buildings`. The fork is required, not a
preference. Every package-index build of Buildings, 13.0.0 and 13.0.1
alike, defines
`BoundaryConditions/WeatherData/BaseClasses/LimiterWindDirection.mo` as
`winDir = noEvent(mod(u, uMax))`. `mod` has no derivative with respect
to time, so `wth_bus.winDir` cannot be differentiated and the build
dies with `IndexReduction.pantelidesIndexReduction failed!`. The fork
keeps the older, differentiable `winDir = min(uMax, max(uMin, u))`.

Both weather files are checked in and no preprocessing step is needed.
`resources/mos_to_mat.py` documents how `resources/tmy3.mat` was
produced from `resources/tmy3.mos`, but running it is not a
prerequisite. The cold-months stress-test weather file used upstream
(`winter.mos`, November to February only) is not included here.

The FMU is driven from Python with `fmpy`. `fmu_example.py` is a plain
`simulate_fmu` run; `fmu_control.py` steps `FMU2Slave` by hand as a
closed-loop CO2-driven window controller. Both are working examples.

## Weather and the airflow path

Weather enters twice. `wth_reader` is a `ReaderTMY3` on
`p_weather_file = "resources/tmy3.mos"` and feeds `wth_bus`, which
drives the zone and the outside-air source. Separately `wth_Tdry` is a
`CombiTimeTable` reading table `Tdry` from
`p_weather_mat = "resources/tmy3.mat"` and is exposed as `out_T_mat` in
degrees C. Both paths are relative, so either run the FMU from this
directory or override both parameters with absolute paths.

The ventilation flow is applied as an extraction, not an injection.
`out_vent_flow` is negative by construction and is fed to
`src_air_vent.m_flow_in` on zone port 4, so it pulls air out of the
zone; the make-up air enters at port 1 from `wth_outside` through
`sn_temp_vent`, `sn_rh_vent` and a linearized `PressureDrop`
(`dp_nominal = 50`, `m_flow_nominal = -0.009 kg/s`). That is why the
outdoor-air sensors sit on the inlet branch and why a negative
`out_vent_flow` means inflow. `src_air_vent` has `use_T_in = false` and
`T = 293.15`, which never matters while the flow stays negative.

The slab's underside is not adiabatic: `src_temp_boundary` imposes
`sch_bound_temp`, a sine of amplitude 1.5 K about 294.65 K with a
24 h period and phase 3*pi/2, on `slab_radiant.surf_b`.

## Natural ventilation

A hybrid of three sources, not a clean implementation of any one paper.

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

The integral is computed once, at parameter time, by
`quadratureLobatto` on `f_nv` from `z0 = k_win_sill + k_win_height/2`
to `h = k_win_sill + k_win_height`, that is from window mid-height to
top. `z_ref` is hardcoded as `10^(1/7)`. Compared with the paper the
code adds three engineering tweaks: an air-density factor of 1.2 to
convert volumetric to mass flow, a sign flip for the inward-flow
convention, and a min-clamp at `p_vent_floor = -0.00366 kg/s` to model
baseline infiltration.

The ventilation opening is its own geometry and is not tied to the
three glazed constructions: `p_win_width = 1.2 m`,
`k_win_height = 0.6 m`, sill at `k_win_sill = 8.7 m` above ground,
which is a third-floor elevation. None of these match the South window
in `datConExtWin` (1.58 x 1.45 m). Changing the window areas in the
envelope does not change the ventilation flow, and vice versa.

Window discharge coefficient `var_cd`, Wang, Karava & Chen 2015 Eq. (5)
for hopper windows:

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

Wind pressure coefficient `var_cp` does not come from Wang & Chen; it
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
trigonometric coefficients match Swami & Chandra exactly. The incidence
angle is taken as `var_win_ang = abs(wnd_dir - pi)`, so the opening is
treated as facing due South, and `abs(var_cp)` is used in the flow
equation because the logarithm goes negative at some angles.

## State variables

The FMU's `modelDescription.xml` names 17,347 variables, but the ODE
has 73 states: that is the number of entries under `<Derivatives>`.
Of the named variables, 14,952 are `variability="fixed"` and only 1,185
of those carry `causality="parameter"`; the remaining ~13,800 are local
quantities that Buildings computes once at initialization (radiation
view factors, glazing optics, per-layer thermal coefficients). They add
no dynamics, only XML. There are 2 inputs, 2 outputs and 17 event
indicators.

The 73 states come mostly from temperatures inside construction layers.
Conceptually: zone air (4: internal energy U, mass m, CO2 mass mC[1],
water-vapor mass fraction Xi[1]; relative humidity is derived, not
independent), construction temperatures (about 60: per-layer
temperatures for each surface, which together give the thermal mass and
time lags), slab (about 7: water energy plus slab-layer temperatures),
and a few small internal sensor states.

## Interface

```
  input            default   range          what it does
  u_win_angle      15.0      0 to 90 deg    window opening, drives ventilation through var_cd
  u_occupancy      0.5       0 to 1         occupancy fraction, drives internal gain and CO2

  output                                    units
  out_vent_flow                             ventilation mass flow, kg/s, negative = inflow
  out_time                                  simulation time, s, passthrough

  readable variable                         units
  out_T_mat                                 dry-bulb temperature from the .mat reader, deg C
  sn_temp_zone.T                            zone air temperature, K
  sn_co2_zone.ppm                           zone CO2 concentration, ppm
  sn_rh_zone.phi                            zone relative humidity, 0 to 1
  sn_temp_slab.T                            slab surface temperature at the zone interface, K
  sn_temp_water_ret.T                       TABS return-water temperature, K
  sn_temp_vent.T                            outdoor air temperature at the vent inlet, K
  sn_rh_vent.phi                            outdoor air relative humidity at the vent inlet
```

## Parameters

Every `parameter` in the model is reachable at run time through fmpy's
`start_values`. These are the ones that matter.

```
  parameter             default                  what it controls
  p_weather_file        "resources/tmy3.mos"     TMY3 path for ReaderTMY3
  p_weather_mat         "resources/tmy3.mat"     path for the Tdry CombiTimeTable
  mat_insul.x           0.087 m                  insulation thickness, biggest envelope knob
  mat_insul.k           0.049 W/m/K              insulation conductivity
  ctrl_temp_water.k     295.15 K                 TABS supply-water temperature
  ctrl_mflow_water.k    0.02 kg/s                TABS water flow rate
  ctrl_gain_co2.k       0                        per-occupant CO2 emission. ~5e-6 enables CO2
  p_cd_rect             0.62                     window discharge coefficient, rectangular ref.
  p_cp_base             0.6                      base wind pressure coefficient
  p_win_width           1.2 m                    ventilation opening width
  p_vent_floor          -0.00366 kg/s            infiltration floor on out_vent_flow
  p_log_aspect          log(0.85165)             building side ratio G in var_cp
  p_wind_dir_set        -1                       wind direction override, rad; <0 = use TMY3
  p_wind_spe_set        -1                       wind speed override, m/s; <0 = use TMY3
  p_room_h              3.84 m                   hRoo; p_room_area = 31.4 / p_room_h
```

`k_win_sill = 8.7 m` and `k_win_height = 0.6 m` are `constant`, not
`parameter`, so unlike the above they cannot be overridden at run time.

## Surfaces

Areas as written in `livelab.mo`. The envelope does not close into one
solid; see README.md on that.

```
  construction        layers                 area m^2   til        azi
  datConExt[1]        con_roof               9.165      45 deg     E
  datConExt[2]        con_roof               7.071      45 deg     W    (openings cut out)
  datConExtWin[1]     con_wall_ext           8.179      Wall       S    glazing 1.58 x 1.45
  datConExtWin[2]     con_roof               1.047      Ceiling    W    glazing 1.07 x 0.885
  datConExtWin[3]     con_roof               1.047      Wall       W    glazing 1.07 x 0.885
  datConBou[1]        con_wall_bound_glass   8.015      Wall       W
  datConBou[2]        con_wall_bound_glass   2.054      Wall       N
  datConBou[3]        con_wall_bound_wood    2.054      Wall       N
  datConBou[4]        con_wall_bound_wood    2.342      Wall       W
  datConBou[5]        con_wall_bound_wood    4.109      Wall       S
  datConBou[6]        con_wall_bound_glass   6.845      Wall       E
  surBou[1]           slab interface         8.179      Floor
```

`AFlo = 8.17547` while `surBou[1].A = 2.13 * 3.84 = 8.1792`; the two
differ in the fourth digit. `datConExt[2]` has `1.07 * 1.77 + 0.2` m^2
subtracted, which removes both West-facing openings from the West roof
slope. The window frame fractions are `fFra = {0.48, 0.6, 0.6}`, and
`datConExtWin[3]` is a wall-tilted window that nonetheless uses the
roof layer stack.

## Materials

`x` thickness m, `k` W/m/K, `c` J/kg/K, `d` kg/m^3.

```
  con_roof, 3 layers (outside to inside), absSol 0.5, absIR 0.9
    mat_plywood         x 0.01     k 0.11      c -        d 544
    mat_insul           x 0.087    k 0.049     c 836.8    d 265
    mat_gypsum          x 0.0127   k 0.16      c 830      d 784

  con_wall_ext, 5 layers, absSol 0.5, absIR 0.9
    mat_wall_outer      x 0.02     k 1.1       c 1000     d 1514
    mat_wall_mid1       x 0.015    k 0.2       c 1700     d 165
    mat_wall_mid2       x 0.095    k 0.04658   c 840      d 132.5
    mat_wall_mid3       x 0.1      k 0.04      c 840      d 80
    mat_wall_inner      x 0.015    k 0.13      c 1500     d 455

  con_slab, 3 layers (screed, insulation, finish)
                        x 0.05     k 0.225     c 730      d 1800   nSta 3
                        x 0.03     k 0.032     c 840      d 80     nSta 2
                        x 0.022    k 0.12      c 1500     d 450    nSta 1

  con_wall_bound_glass  mat_glass_panel  x 0.0057  k 1.0  c 800  d 2500
  con_wall_bound_wood   mat_plywood
```

`glz_window` is triple glazing: three `mat_glass` panes
(`x = 0.0057`, `k = 1.0`, `tauSol = 0.771`, `rhoSol = 0.070`,
`tauIR = 0`, `absIR = 0.5`) separated by two 12.7 mm air gaps, with
`UFra = 0.6`. The slab is a `SingleCircuitSlab`, floor type, with
`A = 8.17547 m^2`, 50.3 m of `PEX_RADTEST` pipe in layer 1 and
`m_flow_nominal = 0.02 kg/s`.

Occupancy gain is `ctrl_gain_heat`, a `MatrixGain` with
`K = 120 / p_room_area * [0.4; 0.4; 0.2]`, so one occupant is 120 W
over 8.177 m^2 split 40% radiant, 40% convective, 20% latent.

## What is not in the model

There is no HVAC controller. TABS water flow and supply temperature are
constants, nothing tracks a setpoint, so simulated zone temperature
drifts wherever the physics takes it; the real Z31 sits near 22 deg C
because of a controller this model omits. There are no lighting or
equipment loads beyond the occupancy gain. The shade is not dynamic:
`ctrl_shade` is a `Replicator` hardcoded to `u = 1`, and `glz_window`
has `haveExteriorShade = true` with `haveInteriorShade = false`, so all
three windows run with the exterior shade permanently fully deployed.
CO2 generation is wired up but disabled by `ctrl_gain_co2.k = 0`;
override it at run time to enable.

## References

1. Wang, H., & Chen, Q. (2012). A new empirical model for predicting
   single-sided, wind-driven natural ventilation in buildings. Energy
   and Buildings, 54, 386-394.
2. Wang, H., Karava, P., & Chen, Q. (2015). Development of simple
   semiempirical models for calculating airflow through hopper, awning,
   and casement windows for single-sided natural ventilation. Energy
   and Buildings, 96, 373-384.
3. Swami, M. V., & Chandra, S. (1988). Correlations for pressure
   distribution on buildings and calculation of natural-ventilation
   airflow. ASHRAE Transactions, 94(1), 243-266.
