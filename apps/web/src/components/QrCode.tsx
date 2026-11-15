"use client";

import QRCode from "qrcode";
import { useEffect, useState } from "react";

/** QR code rendered locally as an SVG (no third-party QR service sees the data). */
export function QrCode({ value, label }: { value: string; label: string }) {
  const [svg, setSvg] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    QRCode.toString(value, { type: "svg", margin: 1, errorCorrectionLevel: "M" })
      .then((markup) => active && setSvg(markup))
      .catch(() => active && setSvg(null));
    return () => {
      active = false;
    };
  }, [value]);

  if (!svg) return null;
  return (
    <div
      className="qr"
      role="img"
      aria-label={label}
      // The SVG comes from the qrcode library, built from our own value: no user HTML.
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
