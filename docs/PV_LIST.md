# EPICS PV list

PVs produced by the `fastcs_carbide.CarbideController` IOC, derived from the
sub-controller structure in
[`carbide_controller.py`](../src/fastcs_carbide/controller/carbide_controller.py)
and mirrored in
[`device.py`](../src/fastcs_carbide/device.py)'s ophyd-async wrapper.

Prefix below is `LA18L-EA-CARB-01`, the default `id` set in
[`fastcs.yaml`](../fastcs.yaml). Verify one PV first before batch-checking the
rest, e.g.:

```
cainfo LA18L-EA-CARB-01:STATUS:ActualStateName
```

## INFO

- `LA18L-EA-CARB-01:INFO:LaserIdentificationNumber`
- `LA18L-EA-CARB-01:INFO:SerialNumber`

## STATUS

- `LA18L-EA-CARB-01:STATUS:ActualStateName`
- `LA18L-EA-CARB-01:STATUS:IsOutputEnabled`
- `LA18L-EA-CARB-01:STATUS:GeneralStatus`
- `LA18L-EA-CARB-01:STATUS:Warnings`
- `LA18L-EA-CARB-01:STATUS:Errors`

## BASIC

- `LA18L-EA-CARB-01:BASIC:SelectedPresetIndex`
- `LA18L-EA-CARB-01:BASIC:LastExecutedPresetIndex`
- `LA18L-EA-CARB-01:BASIC:ActualAttenuatorPercentage`
- `LA18L-EA-CARB-01:BASIC:ActualOutputEnergy`
- `LA18L-EA-CARB-01:BASIC:ActualOutputFrequency`
- `LA18L-EA-CARB-01:BASIC:ActualOutputPower`
- `LA18L-EA-CARB-01:BASIC:ActualPulseDuration`
- `LA18L-EA-CARB-01:BASIC:ActualPpDivider`
- `LA18L-EA-CARB-01:BASIC:ActualShutterState`
- `LA18L-EA-CARB-01:BASIC:ActualRaFrequency`
- `LA18L-EA-CARB-01:BASIC:ActualHarmonic`
- `LA18L-EA-CARB-01:BASIC:TargetAttenuatorPercentage`
- `LA18L-EA-CARB-01:BASIC:TargetPulseDuration`
- `LA18L-EA-CARB-01:BASIC:TargetPpDivider`
- `LA18L-EA-CARB-01:BASIC:TargetRaFrequency`

## ADVANCED

- `LA18L-EA-CARB-01:ADVANCED:IsRemoteInterlockActive`
- `LA18L-EA-CARB-01:ADVANCED:IsPpEnabled`
- `LA18L-EA-CARB-01:ADVANCED:IsPowerlockEnabled`
- `LA18L-EA-CARB-01:ADVANCED:AomTriggerSource`

## ACTIONS

- `LA18L-EA-CARB-01:ACTIONS:ApplySelectedPreset`
- `LA18L-EA-CARB-01:ACTIONS:EnableOutput`
- `LA18L-EA-CARB-01:ACTIONS:CloseOutput`
- `LA18L-EA-CARB-01:ACTIONS:GoToStandby`
- `LA18L-EA-CARB-01:ACTIONS:ResetRemoteInterlock`
- `LA18L-EA-CARB-01:ACTIONS:EnablePp`
- `LA18L-EA-CARB-01:ACTIONS:DisablePp`
- `LA18L-EA-CARB-01:ACTIONS:EnablePowerlock`
- `LA18L-EA-CARB-01:ACTIONS:DisablePowerlock`
- `LA18L-EA-CARB-01:ACTIONS:ReduceLeak`

## Note

The EPICS PV grouping above (`BASIC`/`ADVANCED`/etc., i.e. which
sub-controller an attribute lives on) is independent of the REST API's own
`/v1/Basic/`/`/v1/Advanced/` grouping used internally in
[`connection.py`](../src/fastcs_carbide/connection.py). The two don't have to
match, and in practice don't always: e.g. `ActualRaFrequency` and
`TargetRaFrequency` are both `BASIC:` PVs here, but their REST endpoints live
under `/v1/Advanced/` on the real Supervisor API. Don't assume one grouping
from the other when debugging.
