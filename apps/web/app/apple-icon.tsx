import { ImageResponse } from "next/og";

import { appIconDataUri } from "@/components/brand/svg/appIcon.ts";

/**
 * Apple touch icon.
 *
 * Home-screen icons must be raster, so this one is rendered at build time from
 * the same artwork `app/icon.svg` is generated from — there is no second
 * drawing to keep in step. iOS composites onto the tile's own corners, which
 * is why the artwork already carries a background.
 */
export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <img
        src={appIconDataUri(size.width)}
        width={size.width}
        height={size.height}
        alt=""
      />
    ),
    { ...size },
  );
}
