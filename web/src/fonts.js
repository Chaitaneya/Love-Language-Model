// Self-hosted, SIL OFL 1.1 (see node_modules/@fontsource/*/LICENSE). Only the Latin subsets are imported,
// bundled by Vite into the build: no CDN, no third-party request. The interface uses the system font;
// these two families are for the poster and the big type.
import "@fontsource/dm-serif-display/latin-400.css";
import "@fontsource/dm-serif-display/latin-400-italic.css";
import "@fontsource/inter/latin-600.css";

// A canvas only uses a font that is already loaded, so the poster must wait for these. They are also
// fetched before any chat is read, so the privacy readout stays true (docs/decision.md D33, D37).
export function loadFonts() {
  return Promise.all([
    document.fonts.load('400 40px "DM Serif Display"'),
    document.fonts.load('italic 400 40px "DM Serif Display"'),
    document.fonts.load('600 26px "Inter"'),
  ]);
}
