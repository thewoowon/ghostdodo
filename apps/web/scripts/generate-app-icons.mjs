/**
 * Writes `app/icon.svg` and `app/favicon.ico` from the mascot geometry.
 *
 *   pnpm icons:generate
 *
 * Both have to be real files — Next's icon conventions will not take a module,
 * and `/favicon.ico` is fetched by name by crawlers and older browsers — but
 * the geometry inside them stays authored once, in
 * `components/brand/svg/paths.ts`. So they are generated, and
 * `tests/app-icon.test.ts` fails if a committed copy stops matching.
 *
 * Rasterising reuses `next/og`, the same renderer that produces the Apple
 * touch icon at build time, so the .ico entries and the touch icon cannot
 * disagree. It is imported as `next/og.js` rather than `next/og`: Node's ESM
 * resolver does no extension guessing and `next` publishes no export map.
 *
 * Type stripping lets this import the TypeScript source directly, so there is
 * no build step and no second copy of the paths.
 */
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { ImageResponse } from "next/og.js";

import { appIconDataUri, appIconSvg } from "../components/brand/svg/appIcon.ts";

/** Windows ships 16/32/48 in a favicon; everything larger is served as PNG. */
const ICO_SIZES = [16, 32, 48];

async function renderPng(size) {
  const response = new ImageResponse(
    { type: "img", props: { src: appIconDataUri(size), width: size, height: size } },
    { width: size, height: size },
  );
  return Buffer.from(await response.arrayBuffer());
}

/**
 * Packs PNGs into an .ico. Entries are stored as PNG rather than BMP, which
 * every target since Windows Vista reads and which keeps the alpha channel
 * without the AND-mask dance BMP entries need.
 */
function packIco(images) {
  const HEADER = 6;
  const ENTRY = 16;

  const directory = Buffer.alloc(HEADER + ENTRY * images.length);
  directory.writeUInt16LE(0, 0); // reserved
  directory.writeUInt16LE(1, 2); // 1 = icon
  directory.writeUInt16LE(images.length, 4);

  let offset = directory.length;
  images.forEach(({ size, png }, index) => {
    const at = HEADER + ENTRY * index;
    // 256px is stored as 0; nothing here is that large, but keep the rule.
    directory.writeUInt8(size >= 256 ? 0 : size, at);
    directory.writeUInt8(size >= 256 ? 0 : size, at + 1);
    directory.writeUInt8(0, at + 2); // palette size, 0 for truecolour
    directory.writeUInt8(0, at + 3); // reserved
    directory.writeUInt16LE(1, at + 4); // colour planes
    directory.writeUInt16LE(32, at + 6); // bits per pixel
    directory.writeUInt32LE(png.length, at + 8);
    directory.writeUInt32LE(offset, at + 12);
    offset += png.length;
  });

  return Buffer.concat([directory, ...images.map((image) => image.png)]);
}

const web = dirname(dirname(fileURLToPath(import.meta.url)));

const svgPath = join(web, "app", "icon.svg");
writeFileSync(svgPath, `${appIconSvg(64)}\n`);
console.log(`wrote ${svgPath}`);

const images = [];
for (const size of ICO_SIZES) {
  images.push({ size, png: await renderPng(size) });
}
const icoPath = join(web, "app", "favicon.ico");
writeFileSync(icoPath, packIco(images));
console.log(`wrote ${icoPath} (${ICO_SIZES.join(", ")})`);
