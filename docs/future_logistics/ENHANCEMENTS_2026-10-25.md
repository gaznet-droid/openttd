# Future Logistics enhancements — 25 October 2026

This branch is an initial implementation, not completion of the full worker brief.

## Confirmed by Gareth

- One launch per functional spaceport per calendar month, shared across its fleet.
- Automatic departure waits for 1,000 passengers. Explicit manual early departure permits 500–999.
- Return to the originating spaceport with 1,000 inbound passengers.
- A temporary Drone Port with three operational pads and one unused visible pad is acceptable.
- Starship uses one launchpad and remains there during servicing/repairs.

## Initial changes

- All aircraft site requirements declared through `fl_needs` now run through the shared `CanVehicleUseStation` gate. This covers the purchase list, building, station/depot orders, automatic depot selection, servicing and landing eligibility. Requirements are checked against the functional airport specification, so decorative NewObjects cannot grant access. It also enforces the Cargo Drone’s existing `drone_pad` requirement.
- Clear specialist-airport error for rejected purchases and orders.
- Starship passenger capacity is 1,000, retaining 120 mail and existing refits. The engine and NewGRF property already store passenger capacity as a 16-bit word. Rebuilt with NML 0.9.0; NewGRF version incremented to 2 while retaining compatibility version 1.
- Independent cursor enlargement in Settings → Graphics: Normal, Large and Extra large. It scales both software and OpenGL/Cocoa cursor paths and composite tool offsets around the unchanged mouse coordinate. Renderer limit is 4×; presets can coincide at that limit. It does not yet add a contrast outline.
- CMake respects the supplied macOS deployment target. Intel artifact workflow also runs on pull requests and asserts x86_64 output. It requests macOS 12.0, compatible with Monterey 12.7.6; the built app still requires real-Mac validation.

## Remaining work — not implemented

| Request | State / next concrete work |
|---|---|
| Starship orbital shuttle | Existing surface airport-pair movement remains. Add persistent orbital phase, single-pad occupation, calendar-month launch slots, dispatch UI and an explicitly accounted off-world passenger source. No monthly limit is claimed in this branch. |
| Functional four-pad Drone Port art | Authoritative transparent original exists. Split into airport tiles, match three active landing positions and rooftop altitude without changing normal helistations. Obtain normal/2× in-game captures. |
| Moving Cargo Drone art and 1,000 mph | Existing inputs are single-view art. Produce and review missing headings; replace stock helicopter graphics, tune speed, then measure cruise movement with the configured aircraft speed factor. |
| Underground Hyperloop and 2,000 mph | Requires separate subterranean occupancy, construction commands, pathfinding, save records, terrain inspection overlay and terminal connections. Surface rail reskins do not meet the brief. Dedicated terminal/pod/capsule art is absent from this checkout. |
| Toolbar and widget icon presets | Still outstanding. Existing GUI zoom uses discrete 1×/2×/4× steps; 250% layout scale does not produce 250% icons. Add separate image measurement/drawing and minimum hit targets for toolbars, controls and menus, with clipping tests. |
| Cursor contrast and physical Mac QA | Independent sizing is implemented; high-contrast option, before/after Retina captures, tile-hotspot checks and menu-clipping checks remain. |

Do not merge this as the full enhancements release. Do not overwrite the working Mac app or modify existing saves/NewGRF lists during testing. The current integration tests for airport-pair Starship operation are temporary compatibility coverage, not evidence of orbital operation.

## Functional graphics and data-centre checkpoint

- Data Centre is a functional 4x4 industry drawn from the supplied transparent original. The inherited bank house-tile and 1,200-person restrictions are removed. New centres are player-funded instead of pre-populating towns. The strict per-town callback remains active even with the global multiple-industry setting enabled.
- Cargo Drone uses the supplied multirotor body as an actual moving aircraft, holding a fixed yaw while translating in any direction. Its declared speed is 1,609 km/h, with the conventional-plane distance divisor bypassed only for this tagged drone.
- Drone Port is a functional 4x4 airport using the supplied art at normal and 2x zoom, with three aligned rooftop stands and a fourth unused visible stand. Ordinary helistations keep their original movement and landing altitude.
- Modified GRF rebuilt with NML 0.9.0; version 2 requires a new game because the functional layouts changed. Keep prior app/GRFs for existing saves.
- Local Debug build and all 110 CTest cases passed. The new player-command integration check funded centres on flat open land in two different towns, including a town below 1,200 people, and rejected a same-town duplicate with the global multiple-industry setting enabled.
- Live moving-drone speed measurement, rooftop alignment screenshots and physical Mac validation remain required before this checkpoint is called a finished release. Orbital and underground engineering are subsequent work.
- All corporate originals except Hyperloop were recovered in the repository and the Mac export folder. No Hyperloop terminal/pod images were recovered from the earlier-chat or file searches; those remain an asset gap.
