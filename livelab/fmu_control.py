from fmpy import read_model_description, extract
from fmpy.fmi2 import FMU2Slave

FMU       = "livelab.fmu"
START     = 200 * 86400.0
STOP      = START + 86400.0
CO2_LIMIT = 100.0
OCCUPANCY = 1.0

md = read_model_description(FMU)
ud = extract(FMU)
vr = {v.name: v.valueReference for v in md.modelVariables}

fmu = FMU2Slave(guid=md.guid, unzipDirectory=ud,
                modelIdentifier=md.coSimulation.modelIdentifier, instanceName="m")
fmu.instantiate()
fmu.setupExperiment(startTime=START)
fmu.setReal([vr["ctrl_gain_co2.k"]], [5e-6])
fmu.enterInitializationMode()
fmu.exitInitializationMode()
fmu.setReal([vr["u_occupancy"]], [OCCUPANCY])

read  = [vr["sn_temp_zone.T"], vr["sn_temp_vent.T"], vr["sn_co2_zone.ppm"]]
write = [vr["u_win_angle"]]

print(f"{'h':>4} {'T_z-20':>6} {'T_o-20':>9} {'CO2-400':>9} {'win':>5}")
t, dt = START, 3600.0
while t < STOP:
    Tz, To, co2 = fmu.getReal(read)
    win = 30.0 if co2 > CO2_LIMIT else 0.0
    fmu.setReal(write, [win])
    h = int((t - START) / 3600)
    print(f"{h:>4d} {Tz - 293.15:>+6.1f} {To - 293.15:>+9.1f} {co2:>+9.0f} {win:>5.0f}")
    fmu.doStep(currentCommunicationPoint=t, communicationStepSize=dt)
    t += dt

fmu.terminate()
fmu.freeInstance()
