/**
 * `app/icon.svg` and `app/favicon.ico` are generated files.
 *
 * Next's icon conventions need real files on disk, but the mascot geometry is
 * authored once in `paths.ts`. These tests are what keep those two facts from
 * quietly diverging: edit a path, forget `pnpm icons:generate`, and the site
 * ships a favicon of the previous bird.
 *
 * The SVG is checked byte for byte against the generator. The .ico cannot be —
 * rebuilding it needs the `next/og` rasteriser, which does not belong in a
 * unit test — so it is checked structurally instead. That is the weaker of the
 * two guarantees, and the reason the generator writes both files at once.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { COMPACT_BELOW_PX, appIconSvg } from "@/components/brand/svg/appIcon.ts";

const app = join(process.cwd(), "app");
const svg = readFileSync(join(app, "icon.svg"), "utf8");
const ico = readFileSync(join(app, "favicon.ico"));

/** Walks the ICONDIR at the head of an .ico. */
function icoEntries(file: Buffer) {
  const count = file.readUInt16LE(4);
  return Array.from({ length: count }, (_, index) => {
    const at = 6 + 16 * index;
    const length = file.readUInt32LE(at + 8);
    const offset = file.readUInt32LE(at + 12);
    return {
      width: file.readUInt8(at),
      height: file.readUInt8(at + 1),
      length,
      offset,
      signature: file.subarray(offset + 1, offset + 4).toString("latin1"),
    };
  });
}

describe("icon.svg", () => {
  it("matches what the generator would write", () => {
    expect(svg).toBe(`${appIconSvg(64)}\n`);
  });

  it("carries its own background rather than relying on the tab colour", () => {
    expect(svg).toContain('<rect width="64" height="64" fill=');
  });
});

describe("favicon.ico", () => {
  it("is a well-formed icon directory", () => {
    expect(ico.readUInt16LE(0)).toBe(0); // reserved
    expect(ico.readUInt16LE(2)).toBe(1); // 1 = icon, not cursor
    expect(icoEntries(ico)).toHaveLength(3);
  });

  it("carries 16, 32 and 48 as PNG entries that stay inside the file", () => {
    const entries = icoEntries(ico);

    expect(entries.map((entry) => entry.width)).toEqual([16, 32, 48]);
    for (const entry of entries) {
      expect(entry.height).toBe(entry.width);
      expect(entry.signature).toBe("PNG");
      expect(entry.offset + entry.length).toBeLessThanOrEqual(ico.length);
    }
  });
});

describe("small sizes", () => {
  it("crop to the head so the beak survives a 16px tab", () => {
    const tab = appIconSvg(COMPACT_BELOW_PX - 1);
    const full = appIconSvg(COMPACT_BELOW_PX);

    // The crop is a different framing transform, not a different drawing.
    expect(tab).not.toBe(full);
    expect(tab).toContain("<path d=");
  });
});
