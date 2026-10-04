import type { MetadataRoute } from "next";
import { site } from "@/lib/site-config";

/** Block indexing until the real production URL is configured (see layout metadata too). */
export default function robots(): MetadataRoute.Robots {
  const configured = !site.url.startsWith("http://localhost");
  return configured
    ? {
        rules: { userAgent: "*", allow: "/" },
        sitemap: new URL("/sitemap.xml", site.url).toString(),
      }
    : { rules: { userAgent: "*", disallow: "/" } };
}
