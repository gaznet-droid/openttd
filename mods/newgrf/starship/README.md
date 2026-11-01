# Orbital service update — 26 October 2026

Use a **new game** with Starship 3 and Future Logistics 3. Earlier launch-site layouts are incompatible.

Starship now operates from one home spaceport. It boards 1,000 actual passengers, launches vertically, spends seven calendar days off-world, returns to that same spaceport with 1,000 inbound passengers, and services on its pad for two days. The green dispatch button permits early departure with 500–999 passengers. Each spaceport has one launch per calendar month, shared by its fleet. All mission state and the shared launch slot survive saving and loading. Ordinary airports cannot serve Starship; ordinary helicopters cannot occupy the dedicated launch complex.

Both functional spaceports use the supplied launch artwork on a 4×4 footprint. The rocket is drawn separately from the empty-pad scenery, including during servicing. Waiting ships use the service bay. Orbital revenue uses a documented notional distance of 256 tiles for each leg; outbound payments deduct feeder shares, and returning passengers enter normal town/company delivery accounting.

The engine integration test exercises real passenger loading, a two-ship fleet sharing monthly slots, inbound delivery, and a save/reload while off-world. The older description below records the original aircraft prototype; its horizontal flight, refit and footprint descriptions are superseded by this update.

---

# Future Logistics: Starship

A NewGRF with a fully reusable rocket, **Starship**, and its **Starship Launch Site**, for the
rocket age of Future Logistics. It follows the Future Logistics tech format
([`docs/future_logistics/tech_format.md`](../../../docs/future_logistics/tech_format.md)) and the
community badge conventions, so rival companies find and adopt it with no change to the game.

It works on its own, or alongside the Future Logistics NewGRF
([`../future_logistics/`](../future_logistics/README.md)), whose Reusable Rocket and Spaceport
belong to the same `rocket` family. Starship is balanced as the top of the transport world: the
most expensive vehicle to buy and to run, the largest capacity (1,000 passengers and 120 mail) and
the most profit; the other numbers are placeholders. See [`PLACEHOLDERS.md`](PLACEHOLDERS.md).

The game ships with this NewGRF and the Future Logistics NewGRF and uses both in new games by
default: they are installed in the game's `newgrf` folder, and added to a new game's NewGRF list
when the configuration does not have one yet (the first run). Players can remove them in the
NewGRF settings.

## Contents

| Item | Kind | What it is |
|---|---|---|
| Starship | aircraft (large) | 1,000 passengers and 120 mail, or express and armoured cargo, between launch sites at 2000 km/h, from 2045 |
| Starship Launch Site | airport (3×4) | The launch complex from the handoff art: launch tower and mount, hangar and propellant tanks |

## How it fits the tech format

| Badge | On | Why |
|---|---|---|
| `fl_format/2` | both | Makes the `fl_` tags count |
| `fl_tech/rocket` | both | Joins the shared rocket family |
| `fl_family/rocket` and its `mechanic`, `market` and `min_tier` declarations | the GRF | Declares the family, so the package works without the Future Logistics NewGRF: built with `airport_pair`, for passengers, mail and freight, in cities and up |
| `fl_needs/launchpad` / `fl_provides/launchpad` | Starship / Launch Site | Starship only flies from airports that provide a launch pad: this launch site, or the Future Logistics Spaceport |
| `fl_role/passenger_intercity`, `fl_role/express`, `fl_role/freight_general` | Starship | The jobs it is declared for |
| `fl_tier/4` | Starship | Its place in the family |
| `fl_id/starship`, `fl_id/starship_launch_site` | both | Stable names for code and the console (`future_logistics_tech find starship`) |
| `role/passenger`, `role/mail`, `role/freight`, `power/rocket` | Starship | The shared classes other NewGRFs, AIs and the purchase list filter read |

No rival rules are added: AeroLink's built-in rule for any new air family adopts the rocket
family two years after it arrives. Other NewGRFs can add rules with
`fl_profile/<profile>/adopt/rocket/...`.

The launch site's movement comes from the country airport. The first NewGRF airport based on a
built-in airport replaces it, so the package defines an unchanged copy of the country airport
before the launch site, and players keep the country airport (the Future Logistics NewGRF copies
the city airport and helistation, not this one).

## Graphics and animation

Made from the Corporate Infrastructure handoff art (`../corporate_infrastructure/originals/`) and
`art/starship_powered.png` by [`../tools/make_spaceport_art.py`](../tools/make_spaceport_art.py), in the base
game's pixel density, with normal and 2× zoom 32-bit sprites. The same script writes the launch pad into the
Future Logistics NewGRF, so both packs show the same spaceport.

- **The launch pad** is 3×4 tiles, the footprint the art is drawn for. The country airport's movement is turned
  a quarter turn to fit it.
- **Docked.** While Starship boards or is serviced it stands on the launch mount in front of the tower, and the
  pad's own tiles draw it there with the tower's clamp arms closed, exactly as in the art. The orbital controller
  switches the pad's tiles between docked and empty (animation frame 1 and 0).
- **Launch and landing.** Starship is a helicopter-type aircraft, so it rises straight up from the launch mount
  and comes straight back down onto it. In the air it is drawn as the helicopter's rotor: the powered rocket with
  three flame frames, placed so it lifts off exactly where the docked rocket stood. The pad shows the tower arms
  swung open while it is away.
- **Menus.** The airport picker shows the docked pad as its preview, and the purchase list and depot show the
  docked rocket.

## Build

1. `python3 -m pip install nml==0.9.0`
2. `./build.sh` (set `NMLC` to use a particular `nmlc`).
3. To remake the sprites from the art: `python3 ../tools/make_spaceport_art.py` (needs Pillow, NumPy and SciPy), then build both packs.

The compiled `starship.grf` is committed; the integration suite fails if it no longer matches its
source.

## Previous-version validation

The results below describe the original airport-pair version, not the requested orbital shuttle.
The 25 October enhancements and outstanding work are tracked in
[`ENHANCEMENTS_2026-10-25.md`](../../../docs/future_logistics/ENHANCEMENTS_2026-10-25.md).

With the integration harness (`tests/future_logistics/integration.py`):

- On its own, in a 512×512 world in 2050, AeroLink opened Starship passenger and mail routes
  between launch sites on day zero, and every Starship served both of its launch sites over
  three months. `future_logistics_tech validate` reports no problems.
- With the Future Logistics NewGRF, `validate` reports no problems, there is one city airport
  whichever order the two are loaded in, and AeroLink chooses Starship over the Reusable Rocket.

## Use

In this fork it is already installed and on for new games. In other OpenTTD builds, put
`starship.grf` in `~/Documents/OpenTTD/newgrf/` and add it under NewGRF Settings before starting a
game. Starship arrives in 2045.
