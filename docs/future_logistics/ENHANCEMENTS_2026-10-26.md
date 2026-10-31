# Future Logistics — 26 October 2026

## Implemented

- Data centres can be funded on ordinary open 4×4 land, including towns below 1,200 population. The inherited bank requirement to demolish houses is removed. One centre per town remains enforced even when the global multiple-industry setting is enabled. Supplied tower art is used on the actual industry.
- New temperate Banks created by this build produce Valuables at ten times the former base rate. At 100% industry cargo scale, complete economy months normally produce 1,080–1,200 Valuables (the observed 31-day test month produced 1,140). Existing Banks retain their saved production rate; build a new Bank or start a new game to test the higher source supply.
- The functional Drone Port uses the supplied 4×4 building and three rooftop landing stands. The fourth stand is intentionally unused. The moving drone uses its supplied art and its 1,609 km/h speed without the conventional-plane speed divisor.
- Starship uses a persistent orbital controller, one home spaceport, 1,000 automatic outbound/inbound passengers, early dispatch at 500 passengers, and one shared launch per spaceport per calendar month. It returns to and services on the same pad. Outbound cargo is actual boarded cargo; the orbital destination supplies the returning manifest. The standalone rocket remains a smaller 200-passenger vehicle using the same controller/art.
- Both functional spaceports use the recovered launch scenery and separate vehicle/flame sprites. Their footprint is 4×4. Ordinary aircraft cannot occupy these dedicated orbital pads.
- Flat underground Hyperloop tubes use native tunnel/wormhole occupancy, reservations, pathfinding and persistence. The two access tiles are occupied; surface tiles over the tube remain available. Crossings/overlaps at the same layer are rejected. The tube tool is dragged between aligned flat access shafts of equal height. Track and propulsion limit are 3,219 km/h; a 202-tile test recorded 3,154 km/h before braking.

## Verification

The GUI Debug build passed all 112 CTest cases, including upstream script regressions and cursor rendering. Focused engine tests passed data-centre placement/duplicate rejection, a real two-ship orbital fleet sharing monthly launch slots, inbound delivery, off-world reload, and underground Hyperloop traversal with a working surface road and save/reload.

Broader adoption/integration checks and native Mac packaging remain in progress. This document is a development checkpoint, not a statement that every requested enhancement is finished.

## Remaining work and limits

Hyperloop currently supports straight tubes between access shafts, with junctions at terminals. It does not provide arbitrary buried curves/intersections. Construction inspection draws blue surface outlines above tubes; terrain translucency and the original terminal's empty/occupied visual states are not implemented. The recovered corporate pack contains no Hyperloop terminal/pod art; repeated earlier-chat/export searches found no originals. Required assets are the original empty and occupied terminal images, the intended footprint/anchors, and pod directional sprites with normal/2× exports.

The Distribution Centre image is recovered but its four functional loading bays are not yet implemented. Its existing Corporate Infrastructure object remains decorative.

Use new games with Future Logistics 3 / Starship 3. Keep earlier apps and saves as fallbacks. Savegame format 369 stores orbital missions and shared launch slots; older builds cannot open these new saves. No company-wide data-centre revenue multiplier has been invented or added.
