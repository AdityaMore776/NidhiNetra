/**
 * Measures the contrast of every colour the design system uses for text and for
 * thin marks, so the numbers in globals.css can be re-checked after any change.
 *
 *   node scripts/contrast.mjs        # exits non-zero if a token fails
 *
 * Thresholds (WCAG 2.1):
 *   1.4.3  text              >= 4.5:1  (3:1 only for >= 24px or >= 19px bold)
 *   1.4.11 non-text contrast >= 3:1    for bars, dots, borders and icons
 */

const token = (name) => {
  const m = new RegExp(`^\\s*--${name}:\\s*(#[0-9a-fA-F]{6})`, "m").exec(CSS);
  if (!m) throw new Error(`token --${name} not found in globals.css`);
  return m[1];
};

const CSS = await (await import("node:fs/promises")).readFile(
  new URL("../src/app/globals.css", import.meta.url),
  "utf8",
);

const lum = (hex) => {
  const c = [1, 3, 5]
    .map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};

const ratio = (a, b) => {
  const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

/** [label, foreground token, background token, minimum] */
const CHECKS = [
  ["body text on canvas", "foreground", "canvas", 4.5],
  ["body text on surface", "foreground", "surface", 4.5],
  ["secondary text on surface", "secondary", "surface", 4.5],
  ["muted text on canvas", "muted", "canvas", 4.5],
  ["muted text on surface", "muted", "surface", 4.5],
  ["muted text on sunken", "muted", "sunken", 4.5],
  ["navy text on surface", "navy", "surface", 4.5],
  ["navy button label", "surface", "navy", 4.5],

  ["critical badge text on its tint", "critical-ink", "critical-tint", 4.5],
  ["high badge text on its tint", "high-ink", "high-tint", 4.5],
  ["medium badge text on its tint", "medium-ink", "medium-tint", 4.5],
  ["low badge text on its tint", "low-ink", "low-tint", 4.5],
  ["critical mark on canvas", "critical", "canvas", 3],
  ["high mark on canvas", "high", "canvas", 3],
  ["medium mark on canvas", "medium-mark", "canvas", 3],
  ["low mark on canvas", "low-mark", "canvas", 3],
  ["focus ring on surface", "focus", "surface", 3],
  ["focus ring on canvas", "focus", "canvas", 3],
];

let failed = 0;
console.log("DRISHTI design-system contrast\n");
console.log("  check                                    ratio   min   result");
console.log("  " + "-".repeat(58));
for (const [label, fg, bg, min] of CHECKS) {
  const r = ratio(token(fg), token(bg));
  const ok = r >= min;
  if (!ok) failed++;
  console.log(
    `  ${label.padEnd(40)} ${r.toFixed(2).padStart(5)}:1  ${String(min).padStart(3)}:1  ${ok ? "pass" : "FAIL"}`,
  );
}

console.log("");
if (failed) {
  console.error(`${failed} token pair(s) below the WCAG minimum. Fix globals.css.`);
  process.exit(1);
}
console.log(`All ${CHECKS.length} token pairs meet WCAG 2.1 AA.`);
