import { ImageResponse } from "next/og";
import { site } from "@/lib/site-config";

export const alt = `${site.name}: ${site.tagline}`;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: "72px",
        background: "#f7f5f0",
        color: "#16161a",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "18px" }}>
        <div
          style={{
            width: 56,
            height: 56,
            borderRadius: 16,
            background: "#16161a",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            gap: 6,
            padding: "0 14px",
          }}
        >
          <div style={{ height: 5, width: 28, borderRadius: 3, background: "#3a2ee8" }} />
          <div style={{ height: 5, width: 21, borderRadius: 3, background: "#fff" }} />
          <div
            style={{ height: 5, width: 14, borderRadius: 3, background: "rgba(255,255,255,0.55)" }}
          />
        </div>
        <div style={{ fontSize: 40, fontWeight: 700, letterSpacing: "-0.02em" }}>{site.name}</div>
      </div>
      <div
        style={{
          fontSize: 76,
          fontWeight: 700,
          letterSpacing: "-0.035em",
          lineHeight: 1.05,
          maxWidth: 980,
        }}
      >
        {site.tagline}
      </div>
      <div
        style={{ display: "flex", justifyContent: "space-between", fontSize: 28, color: "#5f5f69" }}
      >
        <span>Clear terms first. Honest numbers when we have them.</span>
        <span style={{ color: "#3a2ee8" }}>Pre-launch</span>
      </div>
    </div>,
    size,
  );
}
