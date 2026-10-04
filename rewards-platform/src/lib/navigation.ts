export type NavItem = { href: string; label: string };

export const primaryNav: NavItem[] = [
  { href: "/how-it-works", label: "How it works" },
  { href: "/trust", label: "Trust & transparency" },
  { href: "/partners", label: "For partners" },
  { href: "/about", label: "About" },
];

export const footerNav: { heading: string; items: NavItem[] }[] = [
  {
    heading: "Product",
    items: [
      { href: "/how-it-works", label: "How it works" },
      { href: "/trust", label: "Trust & transparency" },
      { href: "/early-access", label: "Early access" },
    ],
  },
  {
    heading: "Company",
    items: [
      { href: "/about", label: "About" },
      { href: "/partners", label: "For partners" },
      { href: "/contact", label: "Contact" },
    ],
  },
  {
    heading: "Legal",
    items: [
      { href: "/privacy", label: "Privacy" },
      { href: "/terms", label: "Terms" },
    ],
  },
];
