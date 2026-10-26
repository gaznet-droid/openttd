#!/usr/bin/env python3
"""Build functional airport/industry tiles from the original supplied transparent art.

Every source pixel belongs to exactly one footprint tile. No decorative objects
are required and regenerating the assets never changes the original artwork.
"""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT.parent / 'corporate_infrastructure' / 'originals'
GFX = ROOT / 'gfx'


def tiles(key, filename, feature, start=0):
    source = Image.open(ART / filename).convert('RGBA')
    source = source.crop(source.getchannel('A').point(lambda a: 255 if a > 80 else 0).getbbox())
    metadata = {}
    for zoom in (1, 2):
        tw, th = 64 * zoom, 32 * zoom
        width = 4 * tw
        image = source.resize((width, round(source.height * width / source.width)), Image.Resampling.LANCZOS)
        north_x, north_y = width // 2, image.height - 4 * th
        pieces = {(x, y): Image.new('RGBA', image.size) for y in range(4) for x in range(4)}
        dst = {p: im.load() for p, im in pieces.items()}
        pixels = image.load()
        for py in range(image.height):
            for px in range(width):
                sx = (px + 0.5 - north_x) / (tw / 2)
                sy = (py + 0.5 - north_y) / (th / 2)
                u, v = (sy + sx) / 2, (sy - sx) / 2
                rgba = pixels[px, py]
                if rgba[3] < 40:
                    if not (0 <= v < 4 and 0 <= u < 4):
                        continue
                    rgba = (126, 126, 122, 255)
                owner = (min(3, max(0, int(v // 1))), min(3, max(0, int(u // 1))))
                dst[owner][px, py] = rgba
        for (x, y), piece in pieces.items():
            box = piece.getbbox()
            piece = piece.crop(box)
            name = f'{key}_{x}_{y}_{zoom}x'
            piece.save(GFX / (name + '.png'))
            metadata[name] = [0, 0, piece.width, piece.height,
                              box[0] - (north_x + (y - x) * tw // 2),
                              box[1] - (north_y + (x + y) * th // 2)]
    lines = []
    for y in range(4):
        for x in range(4):
            name = f'{key}_{x}_{y}'
            for zoom in (1, 2):
                args = ', '.join(map(str, metadata[f'{name}_{zoom}x']))
                if zoom == 1:
                    lines.append(f'spriteset({name}_sprite, ZOOM_LEVEL_NORMAL, BIT_DEPTH_32BPP, "gfx/{name}_1x.png") {{ [{args}] }}')
                else:
                    lines.append(f'alternative_sprites({name}_sprite, ZOOM_LEVEL_IN_2X, BIT_DEPTH_32BPP, "gfx/{name}_2x.png") {{ [{args}] }}')
            lines.append(f'spritelayout {name}_layout {{ ground {{ sprite: {name}_sprite(0); }} }}')
            props = 'substitute: 0;'
            if feature == 'FEAT_INDUSTRYTILES':
                props += ' land_shape_flags: 15; accepted_cargos: [[VALU, 8], [GOLD, 8], [DIAM, 8]];'
            lines.append(f'item({feature}, {name}_tile, {start + y * 4 + x}) {{ property {{ {props} }} graphics {{ default: {name}_layout; }} }}')
    lines.append(f'tilelayout {key}_footprint {{')
    if feature == 'FEAT_AIRPORTTILES':
        lines.append('    rotation: DIRECTION_NORTH;')
    for y in range(4):
        for x in range(4):
            lines.append(f'    {x}, {y}: {key}_{x}_{y}_tile;')
    lines.append('}')
    (GFX / f'{key}_tiles.nml').write_text('\n'.join(lines) + '\n')
    return metadata


def drone():
    image = Image.open(ART / 'openttd_cargo_drone_transparent.png').convert('RGBA')
    image = image.crop(image.getchannel('A').point(lambda a: 255 if a > 80 else 0).getbbox())
    lines = ['/* A multirotor can translate in every direction while maintaining a fixed yaw. */']
    for zoom in (1, 2):
        size = (40 * zoom, round(image.height * 40 * zoom / image.width))
        sprite = image.resize(size, Image.Resampling.LANCZOS)
        sprite.save(GFX / f'cargo_drone_{zoom}x.png')
        args = f'0, 0, {size[0]}, {size[1]}, {-size[0] // 2}, {-size[1]}'
        prefix = 'spriteset' if zoom == 1 else 'alternative_sprites'
        level = 'ZOOM_LEVEL_NORMAL' if zoom == 1 else 'ZOOM_LEVEL_IN_2X'
        lines.append(f'{prefix}(cargo_drone_body, {level}, BIT_DEPTH_32BPP, "gfx/cargo_drone_{zoom}x.png") {{')
        lines.extend(f'    [{args}]' for _ in range(8))
        lines.append('}')
    Image.new('RGBA', (1, 1)).save(GFX / 'empty.png')
    lines.append('spriteset(cargo_drone_rotor, ZOOM_LEVEL_NORMAL, BIT_DEPTH_32BPP, "gfx/empty.png") { [0, 0, 1, 1, 0, 0] [0, 0, 1, 1, 0, 0] [0, 0, 1, 1, 0, 0] [0, 0, 1, 1, 0, 0] }')
    (GFX / 'cargo_drone.nml').write_text('\n'.join(lines) + '\n')


def orbital_assets():
    """Use exactly the same supplied launch scenery and vehicle in both GRFs."""
    import re
    import shutil
    source = ROOT.parent / 'starship'
    nml = (source / 'starship.nml').read_text()
    body = nml[nml.index('spriteset(starship_'):nml.index('item(FEAT_AIRCRAFT, starship,')]
    body = body.replace('starship_', 'orbital_rocket_')
    pad = nml[nml.index('spriteset(pad_sprite_0_0,'):nml.index('/* The first NewGRF airport')]
    pad = pad.replace('pad_', 'orbital_pad_').replace('starship_orbital_pad_layout', 'orbital_spaceport_layout')
    pad = re.sub(r'(item\(FEAT_AIRPORTTILES, [^,]+, )(\d+)', lambda m: m[1] + str(int(m[2]) + 16), pad)
    for name in re.findall(r'"gfx/([^"]+)"', body):
        shutil.copy(source / 'gfx' / name, GFX / name)
    for original in (source / 'gfx').glob('pad_[0-3]_[0-3]_[12]x.png'):
        shutil.copy(original, GFX / original.name.replace('pad_', 'orbital_pad_'))
    (GFX / 'orbital_rocket.nml').write_text(body + pad)


def distribution_hub():
    """Use the supplied warehouse over a 3x4 rear and four live front bays."""
    image = Image.open(ART / 'openttd_distribution_centre_4x4_transparent.png').convert('RGBA')
    image = image.crop(image.getchannel('A').point(lambda a: 255 if a > 80 else 0).getbbox())
    lines = []
    for zoom in (1, 2):
        width = 256 * zoom
        sprite = image.resize((width, round(image.height * width / image.width)), Image.Resampling.LANCZOS)
        sprite.save(GFX / f'distribution_hub_{zoom}x.png')
        prefix = 'spriteset' if zoom == 1 else 'alternative_sprites'
        level = 'ZOOM_LEVEL_NORMAL' if zoom == 1 else 'ZOOM_LEVEL_IN_2X'
        args = f'0, 0, {sprite.width}, {sprite.height}, {-width // 2}, {128 * zoom - sprite.height}'
        lines.append(f'{prefix}(distribution_hub_sprite, {level}, BIT_DEPTH_32BPP, "gfx/distribution_hub_{zoom}x.png") {{ [{args}] }}')
    lines.extend([
        'spritelayout distribution_hub_layout { ground { sprite: GROUNDSPRITE_CONCRETE; } building { sprite: distribution_hub_sprite(0); xextent: 48; yextent: 64; zextent: 56; } }',
        'spritelayout distribution_hub_ground { ground { sprite: GROUNDSPRITE_CONCRETE; } }',
        'switch(FEAT_OBJECTS, SELF, distribution_hub_object_graphics, relative_pos) { 0: distribution_hub_layout; distribution_hub_ground; }',
        'item(FEAT_OBJECTS, distribution_warehouse, 0) { property { class: "FLHB"; name: string(STR_DISTRIBUTION_WAREHOUSE); climates_available: ALL_CLIMATES; size: [3, 4]; build_cost_multiplier: 4; remove_cost_multiplier: 3; introduction_date: date(2022, 1, 1); end_of_life_date: 0xFFFFFFFF; object_flags: bitmask(OBJ_FLAG_NO_FOUNDATIONS); height: 56; num_views: 1; badges: ["fl_format/2", "fl_id/distribution_warehouse"]; } graphics { default: distribution_hub_object_graphics; purchase: distribution_hub_layout; tile_check: ((extra_callback_info1 & bitmask(0,1,2,3,4)) == 0) ? CB_RESULT_LOCATION_ALLOW : CB_RESULT_LOCATION_DISALLOW; } }',
        'item(FEAT_ROADSTOPS, distribution_centre, 0) { property { class: "FLHB"; classname: string(STR_DISTRIBUTION_CENTRE); name: string(STR_DISTRIBUTION_CENTRE); availability_type: 1; draw_mode: 0; general_flags: bitmask(2,4,5); badges: ["fl_format/2", "fl_id/distribution_centre"]; } graphics { default: distribution_hub_ground; purchase: distribution_hub_layout; } }',
    ])
    (GFX / 'distribution_hub.nml').write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    GFX.mkdir(exist_ok=True)
    info = tiles('data_centre', 'openttd_data_centre_transparent.png', 'FEAT_INDUSTRYTILES')
    info.update(tiles('drone_port', 'openttd_drone_port_transparent.png', 'FEAT_AIRPORTTILES'))
    drone()
    orbital_assets()
    distribution_hub()
    (GFX / 'functional_sprites.json').write_text(json.dumps(info, indent=2, sort_keys=True) + '\n')

    nml = ROOT / 'future_logistics.nml'
    text = nml.read_text()
    begin = text.index('/* BEGIN GENERATED FUNCTIONAL SPRITES */')
    end = text.index('/* END GENERATED FUNCTIONAL SPRITES */', begin) + len('/* END GENERATED FUNCTIONAL SPRITES */')
    block = '/* BEGIN GENERATED FUNCTIONAL SPRITES */\n' + '\n'.join((GFX / name).read_text() for name in ['cargo_drone.nml', 'drone_port_tiles.nml', 'data_centre_tiles.nml', 'orbital_rocket.nml', 'distribution_hub.nml']) + '/* END GENERATED FUNCTIONAL SPRITES */'
    nml.write_text(text[:begin] + block + text[end:])
