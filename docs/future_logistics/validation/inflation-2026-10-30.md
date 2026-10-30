# Controlled 2050 inflation validation — 30 October 2026

Scope: test runner, a read-only Game Script probe and documentation only. No
engine, gameplay price, NewGRF or savegame definition changes.

## Environment

- Base source: enhancement branch at `a89b539c65d43a84259f754881faa291bdb454e7`.
- Runtime: existing Intel macOS app from Actions run `40303168922` (artifact
  source `d4b139884d4725a35ef451bbbc64d016f0af5e53`; displayed binary version
  `20261026--g54d57379e1`). The intervening enhancement commits change only hub
  tests; the engine and committed GRFs are unchanged.
- Host: Intel Mac, macOS Monterey 12.7.6, Python 3.9, OpenGFX 8.0.
- Every comparison world was freshly generated in 2050, with seed 12345, both
  Future Logistics/Starship GRFs, and bootstrap disabled. No comparison save was
  loaded into the other world, and the probe never changed the setting.

## Results

The active saved-game setting was logged as `0` in `inflation-off` and `1` in
`inflation-on`. All six prices were positive and higher in the on world.
Numbers are internal money units; these exact amounts are observations, not
hard-coded compatibility requirements.

| Metric | Inflation off | Inflation on |
| --- | ---: | ---: |
| Road construction | 71 | 925 |
| Truck stop | 150 | 1,948 |
| Road depot | 375 | 4,872 |
| International airport | 22,050 | 286,454 |
| Starship purchase | 522,949 | 6,794,532 |
| Starship annual running cost | 7,171 | 93,181 |

The default hub regression passed construction, four connected bays, live truck
round trips, town restrictions and resumed traffic after reload. Each generated
configuration (`hub-seed`, `hub-prepared`, `hub-built`, `hub-reloaded`) contained
`[economy]` / `inflation = false`.

## Commands and host adaptation

From the new review worktree:

```sh
python3 -m py_compile tests/future_logistics/integration.py
git diff --check
python3 tests/future_logistics/integration.py \
  --binary '/Users/garethbrown/Applications/OpenTTD Latest.app/Contents/MacOS/openttd' \
  --baseset '/Users/garethbrown/Documents/OpenTTD/Builds/Latest-20261030-a89b539/profile/baseset' \
  --output '/Users/garethbrown/Documents/OpenTTD/Builds/Controlled-2050-Inflation/verification-direct' \
  --only inflation
```

All passed. Before the direct comparison, the matching app's `Resources/lang`
was copied to each isolated world's `lang` directory: the macOS app needs these
with `-X`. The paired regression uses the null driver and needed no driver
substitution. Its logs, independent snapshots and `inflation-comparison.json`
are in the stated output directory.

The existing hub runner's first seed uses SDL, which is absent from this native
Cocoa binary. The following in-memory adapter was used for the hub run; no
committed runner code or assertions were changed by it:

```sh
python3 - <<'PY'
from pathlib import Path
import sys
r = Path('/Users/garethbrown/Documents/OpenTTD/Builds/Controlled-2050-Inflation')
p = r / 'source/tests/future_logistics/integration.py'
s = p.read_text().replace(
    '        folder.mkdir(exist_ok=True)',
    '        folder.mkdir(exist_ok=True)\n'
    '        shutil.copytree(Path(binary).parents[1] / "Resources/lang", folder / "lang", dirs_exist_ok=True)'
).replace('else "sdl")', 'else "cocoa")')
sys.argv = [str(p), '--binary',
    '/Users/garethbrown/Applications/OpenTTD Latest.app/Contents/MacOS/openttd',
    '--baseset', '/Users/garethbrown/Documents/OpenTTD/Builds/Latest-20261030-a89b539/profile/baseset',
    '--output', str(r / 'hub-native'), '--only', 'hub']
exec(compile(s, str(p), 'exec'), {'__file__': str(p), '__name__': '__main__'})
PY
```

The four generated hub configs were independently parsed and asserted to have
`economy.inflation == false`. The probe logs were also checked directly for
year 2050 and saved-game setting values 0/1.

## Limits

This is targeted runtime validation on Intel macOS, not a full integration-suite
pass, a new engine release, a reproducible-GRF build check, or a new complete CI
sign-off. An additional Linux build was not completed; no Linux pass is claimed.
Existing base-branch CI failures remain separate from these targeted results.

The balancing baseline is a **new** 2050 world with inflation off. Disabling
inflation after loading an inflated save only stops future increases; it does
not reset the accumulated inflation in that save.
