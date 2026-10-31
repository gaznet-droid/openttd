# Hyperloop viaduct validation — 31 October 2026

This PR adds an elevated Hyperloop viaduct as the default way to build a
Hyperloop route. Underground tubes stay available for routes that hills or
buildings would block. It is stacked on PR #10 and contains no NewGRF artwork:
the viaduct borrows the Tubular Silicon bridge sprites until the artwork PR.

## Design

- **A dedicated bridge spec past the ordinary ones.** `BRIDGE_HYPERLOOP` is
  spec 13, after `MAX_BRIDGES` (13 ordinary specs). Every existing loop over
  ordinary bridges therefore excludes it without changes: town bridges, the
  bridge picker, script bridge lists, the rival planners' cheapest-bridge
  search and NewGRF bridge overrides. The map stores bridge types in 4 bits,
  so spec 13 needs no map or savegame change.
- **HYPL and the viaduct belong together.** The bridge command refuses
  HYPL on any ordinary bridge type and refuses the viaduct for anything but
  HYPL. Ordinary tunnels refuse HYPL too, so HYPL crosses ground only on its
  viaduct or in its own tubes. Converting a viaduct or tube to another rail
  type, or an ordinary bridge or tunnel to HYPL, is refused.
- **No speed or length cap.** The viaduct's speed is unlimited, and it ignores
  the ordinary maximum-bridge-length setting, matching the uncapped tubes it
  sits alongside.
- **What can go under it.** These are the normal rules for land under bridges.
  Roads of every kind, rail and clear land can pass beneath the viaduct.
  Buildings and land higher than the ramps cannot; in those places a route needs
  a tube.

## Player, rival and script changes

- **Rail toolbar with Hyperloop selected:**
  - The bridge button and autorail drag build a viaduct directly, without the
    bridge picker.
  - The tunnel button builds an underground tube, as before.
  - The tooltips say which is which.
- **Rival planner:** tries a viaduct between terminal exits first and falls
  back to a tube when terrain or buildings block it.
- **Script API:** adds `ScriptBridge::BuildHyperloopViaduct(start, end)`.
  `ScriptTunnel::BuildHyperloopTube` is unchanged.

## Build and automated checks

Environment: Linux x86_64, GCC 13.3, CMake, Ninja, SDL 2.30.0, OpenGFX 7.1
(Ubuntu `openttd-opengfx`). Debug build with assertions enabled and `-O0 -g0`.

```sh
cmake --build build
ctest --test-dir build --output-on-failure
python3 tests/future_logistics/integration.py --binary build/openttd \
  --baseset /usr/share/games/openttd/baseset --output work/<name> --only hyperloop
python3 tests/future_logistics/integration.py ... --only hub
python3 tests/future_logistics/integration.py ... --only orbital
python3 tests/future_logistics/integration.py ... --only airports
python3 -m py_compile tests/future_logistics/integration.py
python3 .github/unused-strings.py
git diff --check
```

Results:

- Build succeeded with no errors. **113/113 CTest checks passed**, including the
  upstream script regressions that exercise the script API.
- **Hyperloop scenario passed:**
  - The original 202-tile tube fixture is unchanged: the pod reached the far
    end at 3,131 km/h.
  - A new 22-tile viaduct fixture puts a road under the viaduct, and a second
    pod crosses it.
  - A short ordinary bridge is first proved to fit for ordinary rail in test
    mode, then refused for HYPL.
  - Converting the viaduct to ordinary rail is refused.
  - On reload, both pods must cross again. The saved "reached" flags are now
    reset when the game is loaded, so a reload cannot pass on stale state.
- **Rival adoption passed.** National Rail built its Hyperloop route. On this
  hilly map that route is a tube (`bridges=0 tunnels=1`), which is the
  intended fallback.
- **Hub, orbital and airport scenarios** still pass.
- **Full Future Logistics suite** (the run CI uses for PRs to `main`): all 55
  runs passed except one check that fails on its own. That check expects
  "Published roadmap milestone" news, which was removed on the feature branch
  in afe937c ("remove obsolete roadmap news"), so it fails without this PR's
  changes too. It was skipped locally to run the rest of the suite. The stale
  check belongs in a fix to #5, not here.
- Python compilation, unused strings and whitespace checks passed.

## Why tubes stay

The first version of this PR replaced tubes outright. On the 512×512 test map,
the rival planner tried 234 times to build a Hyperloop route and every attempt
failed: 201 with *bridge too low for terrain* and 33 with *building must be
demolished*. No straight 200-tile corridor at ramp height existed for the test
fixture either. A viaduct stays one level above its ramps for its whole
length, so long straight routes almost always meet higher ground. Tubes were
therefore kept for those routes, with the viaduct as the default.

## Save compatibility

A save was made by the PR #10 binary (76d6bfe), containing a 202-tile
underground tube and a running pod. It was loaded into this PR's binary. After
loading, the pod crossed the tube again. Bridge specs are not saved, and
existing bridges keep their stored types, so older saves need no conversion.

## Limits

- The viaduct uses Tubular Silicon sprites, recoloured with the concrete
  palette, until the Hyperloop artwork PR.
- NewGRFs cannot restyle spec 13 through the ordinary bridge properties. The
  artwork PR will need its own route for this, such as rail type bridge
  surfaces or a dedicated property.
- This note does not claim a rendered visual review of the viaduct.
