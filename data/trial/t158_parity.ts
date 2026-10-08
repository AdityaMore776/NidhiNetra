// T158: the phone's spot maths on the inputs data/trial/t158_replay.py gives it (stdin, JSON), so
// the replay can check the page and the engine agree. Run by t158_replay.py with Node 24 (type
// stripping): node data/trial/t158_parity.ts < cases.json
import { arcCovered, bearing, metres, stretchOf, toBox, turnBy } from "../../apps/web/src/lib/capture.ts";

const chunks: Buffer[] = [];
process.stdin.on("data", (c: Buffer) => chunks.push(c));
process.stdin.on("end", () => {
  const cases = JSON.parse(Buffer.concat(chunks).toString("utf-8"));
  const out = {
    covered: cases.covered.map((c: { arc: never; degs: number[] }) => arcCovered(c.arc, c.degs)),
    stretch: cases.stretch.map((c: { site: never; lat: number; lon: number }) => stretchOf(c.site, c.lat, c.lon)),
    metres: cases.metres.map((c: number[]) => metres(c[0], c[1], c[2], c[3])),
    box: cases.box.map((c: { anchor: never; fix: never }) => toBox(c.anchor, c.fix).inside),
    bearing: cases.bearing.map((c: number[]) => bearing(c[0], c[1], c[2], c[3])),
    turn: cases.turn.map((c: number[]) => turnBy(c[0], c[1])),
  };
  process.stdout.write(JSON.stringify(out));
});
