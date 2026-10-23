model livelab

  constant Real k_roof_ang = Modelica.Constants.pi / 4;
  package Air = Buildings.Media.Air(extraPropertiesNames = {"CO2"});
  parameter String p_weather_file = "resources/tmy3.mos";
  parameter String p_weather_mat  = "resources/tmy3.mat";
  parameter Real p_room_h = 3.84;
  parameter Real p_room_area = 31.4 / p_room_h;
  parameter Real p_cp_base = 0.6;
  parameter Real p_win_width = 1.2;
  constant Real k_win_height = 0.6;
  constant Real k_win_sill = 8.7;
  parameter Real p_log_aspect = Modelica.Math.log(0.85165);
  parameter Real p_cd_rect = 0.62;
  parameter Real p_vent_floor = -0.00366 "Minimum (forced) ventilation flow, kg/s, negative = exhaust";
  parameter Real p_wind_dir_set = -1 "Override wind direction (rad, 0=N pi/2=E pi=S 3pi/2=W), <0 = use TMY3";
  parameter Real p_wind_spe_set = -1 "Override wind speed (m/s), <0 = use TMY3";
  parameter Real wnd_dir_use = if p_wind_dir_set >= 0 then 1 else 0;
  parameter Real wnd_spe_use = if p_wind_spe_set >= 0 then 1 else 0;
  Real wnd_dir = wnd_dir_use * p_wind_dir_set + (1 - wnd_dir_use) * wth_bus.winDir;
  Real wnd_spe = wnd_spe_use * p_wind_spe_set + (1 - wnd_spe_use) * wth_bus.winSpe;
  Real var_cp;
  Real var_cd;
  Real var_win_ang;
  function f_nv
    input Real u;
    output Real y;
  algorithm
    y := (u ^ (2 / 7) - (k_win_sill + k_win_height / 2) ^ (2 / 7)) ^ 0.5;
  end f_nv;

  Real out_T_mat "T_dryBul read from .mat reader, deg C";
  parameter Buildings.HeatTransfer.Data.Solids.Generic mat_insul(x = 0.087, k = 0.049, c = 836.8, d = 265, nStaRef = 5);
  parameter Buildings.HeatTransfer.Data.Solids.GypsumBoard mat_gypsum(x = 0.0127, k = 0.16, c = 830, d = 784, nStaRef = 2);
  parameter Buildings.HeatTransfer.Data.Solids.Generic mat_wall_outer(x = 0.02, k = 1.1, c = 1000, d = 1514, nStaRef = 1);
  parameter Buildings.HeatTransfer.Data.Solids.Generic mat_wall_mid1(x = 0.015, k = 0.2, c = 1700, d = 165, nStaRef = 1);
  parameter Buildings.HeatTransfer.Data.Solids.Generic mat_wall_mid2(x = 0.095, k = 0.04658, c = 840, d = 132.5, nStaRef = 5);
  parameter Buildings.HeatTransfer.Data.Solids.Generic mat_wall_mid3(x = 0.1, k = 0.04, c = 840, d = 80, nStaRef = 5);
  parameter Buildings.HeatTransfer.Data.Solids.Generic mat_wall_inner(x = 0.015, k = 0.13, c = 1500, d = 455, nStaRef = 1);
  parameter Buildings.HeatTransfer.Data.Solids.Generic mat_glass_panel(x = 0.0057, k = 1.0, c = 800, d = 2500, nStaRef = 5);
  parameter Buildings.HeatTransfer.Data.Solids.Plywood mat_plywood(x = 0.01, k = 0.11, d = 544, nStaRef = 1);
  parameter Buildings.HeatTransfer.Data.Glasses.Generic mat_glass(x = 0.0057, k = 1.0, tauSol = {0.771}, rhoSol_a = {0.070}, rhoSol_b = {0.070}, tauIR = 0, absIR_a = 0.5, absIR_b = 0.5);
  parameter Buildings.HeatTransfer.Data.GlazingSystems.Generic glz_window(
    final glass = {mat_glass, mat_glass, mat_glass},
    final gas = {Buildings.HeatTransfer.Data.Gases.Air(x = 0.0127), Buildings.HeatTransfer.Data.Gases.Air(x = 0.0127)},
    UFra = 0.6,
    shade = Buildings.HeatTransfer.Data.Shades.Gray(tauSol_a = 0.1, tauSol_b = 0.1, rhoSol_a = 0.25, rhoSol_b = 0.25, absIR_a = 0.25, absIR_b = 0.25),
    haveInteriorShade = false,
    haveExteriorShade = true);
  parameter Buildings.HeatTransfer.Data.OpaqueConstructions.Generic con_roof(final nLay = 3, absIR_a = 0.9, absIR_b = 0.9, absSol_a = 0.5, absSol_b = 0.5, material = {mat_plywood, mat_insul, mat_gypsum});
  parameter Buildings.HeatTransfer.Data.OpaqueConstructions.Generic con_wall_ext(final nLay = 5, absIR_a = 0.9, absIR_b = 0.9, absSol_a = 0.5, absSol_b = 0.5, material = {mat_wall_outer, mat_wall_mid1, mat_wall_mid2, mat_wall_mid3, mat_wall_inner});
  parameter Buildings.HeatTransfer.Data.OpaqueConstructions.Generic con_wall_bound_glass(final nLay = 1, material = {mat_glass_panel});
  parameter Buildings.HeatTransfer.Data.OpaqueConstructions.Generic con_wall_bound_wood(final nLay = 1, material = {mat_plywood});
  parameter Buildings.HeatTransfer.Data.OpaqueConstructions.Generic con_slab(
    nLay = 3,
    material = {
      Buildings.HeatTransfer.Data.Solids.Generic(x = 0.05, k = 0.225, c = 730, d = 1800, nSta = 3),
      Buildings.HeatTransfer.Data.Solids.Generic(x = 0.03, k = 0.032, c = 840, d = 80, nSta = 2),
      Buildings.HeatTransfer.Data.Solids.Generic(x = 0.022, k = 0.12, c = 1500, d = 450, nSta = 1)});
  parameter Real p_vent_area = Modelica.Math.Nonlinear.quadratureLobatto(function f_nv (), k_win_sill + k_win_height / 2, k_win_sill + k_win_height);
  Modelica.Blocks.Interfaces.RealOutput out_vent_flow;
  Modelica.Blocks.Interfaces.RealOutput out_time;
  Modelica.Blocks.Interfaces.RealInput u_win_angle(start = 15.0) "Window opening angle in degrees";
  Modelica.Blocks.Interfaces.RealInput u_occupancy(start = 0.5) "Occupancy fraction (0-1)";
  Buildings.BoundaryConditions.WeatherData.ReaderTMY3 wth_reader(
    filNam = p_weather_file,
    computeWetBulbTemperature = false);
  Buildings.BoundaryConditions.WeatherData.Bus wth_bus;
  Buildings.ThermalZones.Detailed.MixedAir z_room(
    redeclare package Medium = Air,
    use_C_flow = true,
    AFlo = 8.17547,
    hRoo = p_room_h,
    nSurBou = 1,
    nConExt = 2,
    nConExtWin = 3,
    nConBou = 6,
    nConPar = 0,
    surBou(A = {2.13 * 3.84}, each absIR = 0.9, each absSol = 0.9, each til = Buildings.Types.Tilt.Floor),
    datConExt(layers = {con_roof, con_roof}, A = {2.23 * 4.11, 2.23 * 4.11 - 1.07 * 1.77 - 0.2}, til = {k_roof_ang, k_roof_ang}, azi = {Buildings.Types.Azimuth.E, Buildings.Types.Azimuth.W}),
    datConBou(
      layers = {con_wall_bound_glass, con_wall_bound_glass, con_wall_bound_wood, con_wall_bound_wood, con_wall_bound_wood, con_wall_bound_glass},
      A = {4.11 * 1.95, 1.07 * 1.92, 1.07 * 1.92, 0.61 * 3.84, 1.07 * 3.84, 3.51 * 1.95},
      til = {Buildings.Types.Tilt.Wall, Buildings.Types.Tilt.Wall, Buildings.Types.Tilt.Wall, Buildings.Types.Tilt.Wall, Buildings.Types.Tilt.Wall, Buildings.Types.Tilt.Wall},
      azi = {Buildings.Types.Azimuth.W, Buildings.Types.Azimuth.N, Buildings.Types.Azimuth.N, Buildings.Types.Azimuth.W, Buildings.Types.Azimuth.S, Buildings.Types.Azimuth.E},
      stateAtSurface_a = {false, false, false, false, false, false}),
    datConExtWin(
      layers = {con_wall_ext, con_roof, con_roof},
      A = {2.13 * 3.84, 1.07 * 0.885 + 0.1, 1.07 * 0.885 + 0.1},
      glaSys = {glz_window, glz_window, glz_window},
      wWin = {1.58, 1.07, 1.07},
      hWin = {1.45, 0.885, 0.885},
      fFra = {0.48, 0.6, 0.6},
      til = {
        Buildings.Types.Tilt.Wall,
        Buildings.Types.Tilt.Ceiling,
        Buildings.Types.Tilt.Wall},
      azi = {
        Buildings.Types.Azimuth.S,
        Buildings.Types.Azimuth.W,
        Buildings.Types.Azimuth.W}),
    intConMod = Buildings.HeatTransfer.Types.InteriorConvection.Temperature,
    extConMod = Buildings.HeatTransfer.Types.ExteriorConvection.TemperatureWind,
    energyDynamics = Modelica.Fluid.Types.Dynamics.FixedInitial,
    nPorts = 4);
  Buildings.Fluid.Sources.Outside wth_outside(redeclare package Medium = Air, nPorts = 1);
  Buildings.Fluid.FixedResistances.PressureDrop vent_resistance(redeclare package Medium = Air, allowFlowReversal = false, linearized = true, from_dp = true, dp_nominal = 50, m_flow_nominal = -1.5 * 3 * 6 / 3600 * 1.2);
  Buildings.Fluid.Sources.MassFlowSource_T src_air_vent(use_m_flow_in = true, redeclare package Medium = Air, m_flow = 0, use_T_in = false, T = 293.15, nPorts = 1);
  Buildings.Fluid.Sources.MassFlowSource_T src_water_in(nPorts = 1, use_m_flow_in = true, use_T_in = true, redeclare package Medium = Buildings.Media.Water);
  Buildings.Fluid.HeatExchangers.RadiantSlabs.SingleCircuitSlab slab_radiant(sysTyp = Buildings.Fluid.HeatExchangers.RadiantSlabs.Types.SystemType.Floor, iLayPip = 1, redeclare package Medium = Buildings.Media.Water, pipe = Buildings.Fluid.Data.Pipes.PEX_RADTEST(), layers = con_slab, m_flow_nominal = 0.02, A = 8.17547, disPip = slab_radiant.A / slab_radiant.length, length = 50.3, energyDynamics = Modelica.Fluid.Types.Dynamics.FixedInitial, stateAtSurface_b = false);
  Buildings.Fluid.Sources.Boundary_pT src_water_out(redeclare package Medium = Buildings.Media.Water, nPorts = 1);
  Modelica.Blocks.Math.MatrixGain ctrl_gain_heat(K = 120 / p_room_area * [0.4; 0.4; 0.2]);
  Modelica.Blocks.Routing.Replicator ctrl_shade(nout = 3, u = 1);
  Modelica.Blocks.Math.Gain ctrl_gain_co2(k = 0);
  Modelica.Blocks.Sources.Constant ctrl_mflow_water(k = 0.02);
  Modelica.Blocks.Sources.Constant ctrl_temp_water(k = 295.15);
  Buildings.Fluid.Sensors.TemperatureTwoPort sn_temp_water_ret(redeclare package Medium = Buildings.Media.Water, m_flow_nominal = 0.02, allowFlowReversal = false);
  Buildings.Fluid.Sensors.RelativeHumidityTwoPort sn_rh_vent(redeclare package Medium = Air, m_flow_nominal = 0.02, initType = Modelica.Blocks.Types.Init.InitialState);
  Buildings.Fluid.Sensors.TemperatureTwoPort sn_temp_vent(redeclare package Medium = Air, m_flow_nominal = 0.02, allowFlowReversal = false);
  Buildings.Fluid.Sensors.PPM sn_co2_zone(redeclare package Medium = Air, warnAboutOnePortConnection = false);
  Modelica.Thermal.HeatTransfer.Sensors.TemperatureSensor sn_temp_zone;
  Buildings.Fluid.Sensors.RelativeHumidity sn_rh_zone(redeclare package Medium = Air, warnAboutOnePortConnection = false);
  Modelica.Thermal.HeatTransfer.Sensors.TemperatureSensor sn_temp_slab;
  Buildings.HeatTransfer.Sources.PrescribedTemperature src_temp_boundary;
  Modelica.Blocks.Sources.Sine sch_bound_temp(amplitude = 1.5, f = 1 / 3600 / 24, phase = 4.7123889803847, offset = 294.65);
  Modelica.Blocks.Sources.CombiTimeTable wth_Tdry(
    tableOnFile = true,
    tableName = "Tdry",
    fileName = p_weather_mat,
    extrapolation = Modelica.Blocks.Types.Extrapolation.HoldLastPoint);

equation
  out_T_mat = wth_Tdry.y[1];

  connect(ctrl_gain_co2.y, z_room.C_flow[1]);
  connect(ctrl_gain_heat.y, z_room.qGai_flow);
  connect(ctrl_mflow_water.y, src_water_in.m_flow_in);
  connect(ctrl_shade.y, z_room.uSha);
  connect(ctrl_temp_water.y, src_water_in.T_in);
  connect(out_vent_flow, src_air_vent.m_flow_in);
  connect(u_occupancy, ctrl_gain_co2.u);
  connect(u_occupancy, ctrl_gain_heat.u[1]);
  connect(sch_bound_temp.y, src_temp_boundary.T);
  connect(slab_radiant.port_b, sn_temp_water_ret.port_a);
  connect(slab_radiant.surf_a, z_room.surf_surBou[1]);
  connect(sn_rh_vent.port_b, vent_resistance.port_a);
  connect(sn_temp_vent.port_b, sn_rh_vent.port_a);
  connect(sn_temp_water_ret.port_b, src_water_out.ports[1]);
  connect(src_air_vent.ports[1], z_room.ports[4]);
  connect(src_temp_boundary.port, slab_radiant.surf_b);
  connect(src_water_in.ports[1], slab_radiant.port_a);
  connect(vent_resistance.port_b, z_room.ports[1]);
  connect(wth_bus, wth_outside.weaBus);
  connect(wth_bus, z_room.weaBus);
  connect(wth_outside.ports[1], sn_temp_vent.port_a);
  connect(wth_reader.weaBus, wth_bus);
  connect(z_room.heaPorAir, sn_temp_zone.port);
  connect(z_room.ports[2], sn_co2_zone.port);
  connect(z_room.ports[3], sn_rh_zone.port);
  connect(z_room.surf_surBou[1], sn_temp_slab.port);
  out_time = time;
  var_win_ang = abs(wnd_dir - Modelica.Constants.pi);
  var_cp = p_cp_base * Modelica.Math.log(
    1.248 - 0.703 * Modelica.Math.sin(var_win_ang / 2)
      - 1.175 * (Modelica.Math.sin(var_win_ang)) ^ 2 + 0.131
      * (Modelica.Math.sin(2 * var_win_ang * p_log_aspect)) ^ 3
      + 0.769 * Modelica.Math.cos(var_win_ang / 2)
      + 0.07 * p_log_aspect * p_log_aspect * (Modelica.Math.sin(var_win_ang / 2)) ^ 2
      + 0.717 * (Modelica.Math.cos(var_win_ang / 2)) ^ 2);
  var_cd = min(
    (0.92 / p_cd_rect * sqrt(Modelica.Math.sin(u_win_angle * Modelica.Constants.pi / 180) / 2)),
    1);
  out_vent_flow = min(
    -1 * (var_cd * p_cd_rect * p_win_width * abs(var_cp) ^ 0.5 * p_vent_area)
      / (10 ^ (1 / 7)) * wnd_spe * 1.2,
    p_vent_floor);

end livelab;

