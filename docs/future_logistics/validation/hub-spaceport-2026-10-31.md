# Hub and Spaceport validation — 31 October 2026

PR #10 completes Distribution Centre automatic joining/catchment and the
Spaceports airport category/generated station name. It remains separate from
the Bank supply and inflation harness PRs. No NewGRF rebalance or elevated
Hyperloop/Starship art redesign is included.

## Build and automated checks

Environment: Linux x86_64, GCC 13.3, CMake 4.4.4, Ninja 1.13.2, SDL 2.30.0,
OpenGFX 7.1. Debug build with assertions enabled and `-O0 -g0`; optional CURL,
OpenGL and complex-font libraries were not used by this test build.

The tested source includes the PR's hub/Spaceport implementation, the string
range/documentation fixes, the explicit fmt include for dedicated builds,
the map-edge preview guard, and the distant-joining-disabled hub fixture.

Commands (from the repository root, with the installed tools on PATH):

```sh
cmake --build build --parallel 3
ctest --test-dir build --output-on-failure --parallel 3
python3 tests/future_logistics/integration.py \
  --binary build/openttd \
  --baseset /workspace/scratch/c0dbc96ae083/deps/usr/share/games/openttd/baseset \
  --output work/pr10-hub --only hub
python3 tests/future_logistics/integration.py \
  --binary build/openttd \
  --baseset /workspace/scratch/c0dbc96ae083/deps/usr/share/games/openttd/baseset \
  --output work/pr10-orbital --only orbital
python3 tests/future_logistics/integration.py \
  --binary build/openttd \
  --baseset /workspace/scratch/c0dbc96ae083/deps/usr/share/games/openttd/baseset \
  --output work/pr10-airports --only airports
python3 -m py_compile tests/future_logistics/integration.py
python3 .github/unused-strings.py
git diff --check
```

Results:

- Build succeeded; **112/112 CTest checks passed**, including upstream saved-game
  script regressions. This count is from this build, not copied from an earlier
  development checkpoint.
- Hub regression passed. All four generated worlds explicitly disable distant
  station joining, and the Game Script verifies the saved-game setting. The
  ordinary western stop and all four eastern bays share station 0. The truck
  completes round trips, town/population restrictions hold, and restored traffic
  counters increase after reload.
- Orbital regression passed with generated name **Slindham Spaceport**, full
  launches, home-pad returns, the shared monthly pad limit and off-world reload.
- Airport compatibility passed with Future Logistics alone, Starship alone,
  and both loading orders, retaining one ordinary country airport.
- Python compilation, unused strings and whitespace checks passed.

## Rendered picker review

The rebuilt SDL client was loaded into the controlled hub and orbital saves,
paused, and driven through normal picker inputs. A temporary external SDL event
driver and viewport screenshots were used for visual inspection; no test hooks
were added to the game or repository.

- Distribution Centre remains selectable in the truck-stop picker with a 4×4
  placement footprint. With coverage enabled, the blue outline follows the
  eastern 1×4 bay strip: at truck radius 3 it spans 7×10 tiles, rather than the
  10×10 area that a 4×4 warehouse-based calculation would imply. The rural
  inspected site correctly shows no accepted/supplied cargo.
- Spaceports appears as a separate airport-class choice, alongside ordinary
  small, large, hub and helicopter airports.
- The explicit catchment-text calculation uses the same 1×4 bay rectangle.
  At the eastern map edge, `TileAddWrap` prevents the bay origin wrapping to
  another map row.

## Compatibility and limits

The new saved station-name string is appended after the existing fallback name;
the existing save-specific string IDs are retained. The string-list length and
name-range sentinel are updated without inventing a translatable sentinel.

This records the targeted checks and rendered Linux UI review. It does not
claim a completed full Future Logistics integration suite, a new economy
balance, a NewGRF rebuild, or completion of the separately deferred art work.
Intel packaging and platform CI results are tracked on the PR.
