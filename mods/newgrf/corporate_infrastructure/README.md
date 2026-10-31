# Corporate Infrastructure — source art

The original Corporate Infrastructure handoff images, kept in `originals/` as the source for the game's
sprites. The decorative objects package that used to live here (six placeable scenery objects) was removed
on 31 October 2026 so that only working facilities can be built: the spaceport, data centre, distribution
centre and drone port are real stations and industries in the Future Logistics and Starship NewGRFs.

- `originals/spaceport_empty_pad_transparent.png` and `originals/spaceport_starship_on_pad_transparent.png`
  are the launch pad: `../tools/make_spaceport_art.py` turns them into the 3x4 spaceport and the docked
  Starship in both NewGRFs, in the base game's pixel density.
