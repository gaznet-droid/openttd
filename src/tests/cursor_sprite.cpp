/*
 * This file is part of OpenTTD.
 * OpenTTD is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, version 2.
 * OpenTTD is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the GNU General Public License for more details. You should have received a copy of the GNU General Public License along with OpenTTD. If not, see <https://www.gnu.org/licenses/old-licenses/gpl-2.0>.
 */

/** @file cursor_sprite.cpp Regression test for cursor zoom below the viewport minimum. */

#include "../stdafx.h"
#include "../3rdparty/catch2/catch.hpp"
#include "../blitter/8bpp_optimized.hpp"
#include "../blitter/32bpp_optimized.hpp"
#include "../blitter/32bpp_sse2.hpp"
#include "../core/backup_type.hpp"
#include "../gfx_func.h"
#include "../settings_type.h"
#include "../spritecache.h"

#include "../safeguards.h"

TEST_CASE("Cursor sprites include zoom levels below the viewport minimum", "[cursor]")
{
	const uint8_t preset = GENERATE(0, 1, 2);
	AutoRestoreBackup min_backup(_settings_client.gui.zoom_min, ZoomLevel::Normal);
	AutoRestoreBackup max_backup(_settings_client.gui.zoom_max, ZoomLevel::Max);
	AutoRestoreBackup size_backup(_settings_client.gui.cursor_size, preset);
	AutoRestoreBackup gui_backup(_gui_zoom, ZoomLevel::Normal);
	const ZoomLevel zoom = GetCursorZoom();
	REQUIRE(zoom == ZoomLevel::Normal - preset);

	std::unique_ptr<Blitter> blitter;
	SECTION("8bpp optimized") { blitter = std::make_unique<Blitter_8bppOptimized>(); }
	SECTION("32bpp optimized") { blitter = std::make_unique<Blitter_32bppOptimized>(); }
#ifdef WITH_SSE
	SECTION("32bpp SSE2") { blitter = std::make_unique<Blitter_32bppSSE2>(); }
#endif
	REQUIRE(blitter != nullptr);
	const bool indexed = blitter->GetScreenDepth() == 8;

	SpriteLoader::SpriteCollection source{};
	for (ZoomLevel z = ZoomLevel::Min; z <= ZoomLevel::Max; z++) {
		auto &sprite = source[z];
		sprite.width = sprite.height = 64 >> to_underlying(z);
		sprite.AllocateData(z, sprite.width * sprite.height);
		/* A distinct colour at each zoom catches a decoder reading the wrong stream. */
		const uint8_t colour = 40 + to_underlying(z);
		std::fill_n(sprite.data, sprite.width * sprite.height, SpriteLoader::CommonPixel{colour, colour, colour, 255, uint8_t(indexed ? colour : 0)});
	}

	/* Compare with a viewport explicitly allowing the cursor's zoom. Reject missing
	 * encoded data before drawing, so the broken encoder fails without crashing. */
	_settings_client.gui.zoom_min = zoom;
	UniquePtrSpriteAllocator reference;
	blitter->Encode(SpriteType::Normal, source, reference);
	_settings_client.gui.zoom_min = ZoomLevel::Normal;
	UniquePtrSpriteAllocator actual;
	const Sprite *encoded = blitter->Encode(SpriteType::Normal, source, actual);
	REQUIRE(actual.size == reference.size);

	const int width = source[zoom].width;
	const int height = source[zoom].height;
	const int pitch = width + 2;
	const int bytes_per_pixel = indexed ? 1 : 4;
	std::vector<uint32_t> storage(pitch * (height + 2), 0);
	auto *pixels = reinterpret_cast<uint8_t *>(storage.data());
	Blitter::BlitterParams bp{};
	bp.sprite = encoded->data;
	bp.width = bp.sprite_width = width;
	bp.height = bp.sprite_height = height;
	bp.left = bp.top = 1;
	bp.pitch = pitch;
	bp.dst = pixels;
	blitter->Draw(&bp, BlitterMode::Normal, zoom);

	const uint8_t colour = 40 + to_underlying(zoom);
	for (int y = 0; y < height + 2; y++) {
		for (int x = 0; x < pitch; x++) {
			const bool inside = x > 0 && x <= width && y > 0 && y <= height;
			const auto *pixel = pixels + (y * pitch + x) * bytes_per_pixel;
			CHECK(pixel[0] == (inside ? colour : 0));
			if (!indexed) {
				CHECK(pixel[1] == (inside ? colour : 0));
				CHECK(pixel[2] == (inside ? colour : 0));
			}
		}
	}
}
