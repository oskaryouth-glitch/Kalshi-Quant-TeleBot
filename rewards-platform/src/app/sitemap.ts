import type { MetadataRoute } from "next";
import { publicRoutes } from "@/lib/routes";
import { site } from "@/lib/site-config";

export default function sitemap(): MetadataRoute.Sitemap {
  return publicRoutes.map((path) => ({
    url: new URL(path, site.url).toString(),
    changeFrequency: "monthly",
    priority: path === "/" ? 1 : 0.6,
  }));
}
