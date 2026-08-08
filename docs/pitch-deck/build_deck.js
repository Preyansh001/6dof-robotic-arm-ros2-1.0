/**
 * Dhrishti — MSME Idea Hackathon 6.0 pitch deck
 * 12 main slides + 5 backup slides, 16:9.
 */
const PptxGenJS = require("pptxgenjs");

const pres = new PptxGenJS();
pres.defineLayout({ name: "DECK16x9", width: 13.3333333, height: 7.5 });
pres.layout = "DECK16x9";
pres.author = "Jenil Patel";
pres.company = "Dhrishti";
pres.title = "Dhrishti — Low-Cost AI Visual Defect Detection Station";

/* ---------- palette + type ---------- */
const NAVY = "1B2838";      // background
const PANEL = "223244";     // card fill
const PANEL_D = "1A2634";   // recessed / placeholder fill
const ROW_A = "1F2C3B";     // table row shade A
const ROW_B = "26374A";     // table row shade B
const TINT = "13384A";      // teal-tinted callout card
const WHITE = "FFFFFF";
const MUTED = "9FB3C4";     // supporting text
const DIM = "7D93A6";       // labels / slide numbers
const TEAL = "00B4D8";
const TEAL_D = "0A5570";    // dark teal for highlighted table row
const RED = "E63946";
const LINE = "2E4356";      // hairline rules
const DASH = "3E5A72";      // placeholder outline
const SLATE = "44607A";     // neutral bar fill

const F = "Inter";

const W = 13.3333333;        // exactly 16:9 at 7.5in tall
const M = 0.62;             // page margin
const CW = W - 2 * M;       // content width 12.093

/* ---------- helpers ---------- */
function slide() {
  const s = pres.addSlide();
  s.background = { color: NAVY };
  return s;
}

function chrome(s, kicker, title, badge, titleSize) {
  s.addText(kicker.toUpperCase(), {
    x: M, y: 0.38, w: 9.6, h: 0.26, margin: 0,
    fontFace: F, fontSize: 10, bold: true, color: TEAL, charSpacing: 2.2, valign: "middle",
  });
  s.addText(badge, {
    x: 11.0, y: 0.38, w: 1.713, h: 0.26, margin: 0, align: "right",
    fontFace: F, fontSize: 10, bold: true, color: DIM, charSpacing: 1.2, valign: "middle",
  });
  s.addText(title, {
    x: M, y: 0.70, w: CW, h: 0.68, margin: 0,
    fontFace: F, fontSize: titleSize || 26, bold: true, color: WHITE, valign: "middle",
  });
}

function card(s, x, y, w, h, fill) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.05, fill: { color: fill || PANEL },
  });
}

function placeholder(s, x, y, w, h, label) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.05,
    fill: { color: PANEL_D },
    line: { color: DASH, width: 1.25, dashType: "dash" },
  });
  s.addText(label, {
    x: x + 0.15, y: y + h / 2 - 0.25, w: w - 0.3, h: 0.5, margin: 0, align: "center", valign: "middle",
    fontFace: F, fontSize: 12.5, bold: true, color: "728EA3", charSpacing: 1.8,
  });
}

function label(s, x, y, w, text, color) {
  s.addText(text.toUpperCase(), {
    x, y, w, h: 0.24, margin: 0,
    fontFace: F, fontSize: 9.5, bold: true, color: color || DIM, charSpacing: 1.6, valign: "middle",
  });
}

function bullets(s, x, y, w, h, items, size, color, gap) {
  const runs = items.map((it, i) => {
    const o = {
      bullet: { indent: 14 }, fontFace: F, fontSize: size, color: color || WHITE,
      paraSpaceAfter: gap === undefined ? 10 : gap, breakLine: i !== items.length - 1,
    };
    return typeof it === "string" ? { text: it, options: o } : { text: it.text, options: Object.assign(o, it.opt || {}) };
  });
  s.addText(runs, { x, y, w, h, margin: 0, valign: "top", lineSpacingMultiple: 1.12 });
}

/* several paragraphs, each an array of [text, {opts}]; even spacing, natural flow.
   pptxgenjs honours paragraph-level options only from the paragraph's FIRST run,
   so paraSpaceAfter goes there and breakLine on the last. */
function paras(s, x, y, w, h, items, size, gapPt) {
  const runs = [];
  items.forEach((parts, i) => {
    parts.forEach((p, j) => {
      const o = Object.assign({ fontFace: F, fontSize: size, color: WHITE }, p[1] || {});
      if (j === 0) o.paraSpaceAfter = gapPt;
      if (j === parts.length - 1 && i !== items.length - 1) o.breakLine = true;
      runs.push({ text: p[0], options: o });
    });
  });
  s.addText(runs, { x, y, w, h, margin: 0, valign: "top", lineSpacingMultiple: 1.14 });
}

/* rich single paragraph: array of [text, {opts}] */
function rich(s, x, y, w, h, parts, base) {
  const runs = parts.map((p) => ({ text: p[0], options: Object.assign({ fontFace: F }, base, p[1] || {}) }));
  s.addText(runs, { x, y, w, h, margin: 0, valign: "top", lineSpacingMultiple: 1.14 });
}

/* table builder: rows = [[c1,c2,...], ...]; opts.headerFill etc. */
function table(s, x, y, colW, rows, o) {
  const opt = o || {};
  const fs = opt.fontSize || 11;
  const body = rows.map((r, ri) => {
    if (ri === 0 && opt.header !== false) {
      return r.map((c, ci) => ({
        text: typeof c === "string" ? c : c.text,
        options: Object.assign({
          fontFace: F, fontSize: opt.headFontSize || 9.5, bold: true, color: TEAL, charSpacing: 1.4,
          fill: { color: NAVY }, valign: "bottom",
          align: ci >= (opt.alignFrom || 1) && opt.alignRight ? "right" : "left",
          border: [{ type: "none" }, { type: "none" }, { type: "solid", pt: 0.75, color: LINE }, { type: "none" }],
          margin: [2, 8, 6, ci === 0 ? 2 : 8],
        }, (typeof c === "object" && c.opt) || {}),
      }));
    }
    const shade = (ri % 2 === 1) ? ROW_A : ROW_B;
    return r.map((c, ci) => {
      const isObj = typeof c === "object";
      const custom = (isObj && c.opt) || {};
      return {
        text: isObj ? c.text : c,
        options: Object.assign({
          fontFace: F, fontSize: fs, color: WHITE, valign: "middle",
          fill: { color: custom.rowFill || shade },
          align: ci >= (opt.alignFrom || 1) && opt.alignRight ? "right" : "left",
          border: [{ type: "none" }, { type: "none" }, { type: "none" }, { type: "none" }],
          margin: [4, 8, 4, ci === 0 ? 8 : 8],
        }, custom),
      };
    });
  });
  s.addTable(body, {
    x, y, colW, rowH: opt.rowH || 0.4, autoPage: false,
    border: { type: "none" }, fontFace: F,
  });
}

/* =========================================================
   SLIDE 1 — TITLE
   ========================================================= */
{
  const s = slide();
  const tags = ["MSME IDEA HACKATHON 6.0", "THEME 4 · INDUSTRY 4.0 & 5.0"];
  const tw = 3.5, tgap = 0.26;
  let tx = (W - (tags.length * tw + (tags.length - 1) * tgap)) / 2;
  tags.forEach((t) => {
    s.addShape(pres.ShapeType.roundRect, {
      x: tx, y: 0.95, w: tw, h: 0.44, rectRadius: 0.22,
      fill: { color: NAVY }, line: { color: TEAL, width: 1 },
    });
    s.addText(t, {
      x: tx, y: 0.95, w: tw, h: 0.44, margin: 0, align: "center", valign: "middle",
      fontFace: F, fontSize: 10, bold: true, color: TEAL, charSpacing: 1.4,
    });
    tx += tw + tgap;
  });

  s.addText("Dhrishti", {
    x: 0.9, y: 2.25, w: W - 1.8, h: 1.35, margin: 0, align: "center", valign: "middle",
    fontFace: F, fontSize: 72, bold: true, color: WHITE, charSpacing: 0.5,
  });
  s.addText("Low-Cost AI Visual Defect Detection Station\nfor MSME Production Lines", {
    x: 1.4, y: 3.65, w: W - 2.8, h: 0.95, margin: 0, align: "center", valign: "top",
    fontFace: F, fontSize: 19, color: TEAL, lineSpacingMultiple: 1.2,
  });
  s.addText(
    [
      { text: "Host Institute: AIC-GISC Foundation, Gujarat Technological University", options: { breakLine: true } },
      { text: "Presented by: Jenil Patel", options: { breakLine: true } },
      { text: "10 August 2026", options: {} },
    ],
    {
      x: 1.4, y: 5.05, w: W - 2.8, h: 1.2, margin: 0, align: "center", valign: "top",
      fontFace: F, fontSize: 12.5, color: MUTED, lineSpacingMultiple: 1.45,
    }
  );
  s.addNotes(
    "15 sec. \"Good afternoon. Thank you for the opportunity. I am Jenil Patel. Our idea is a low-cost AI inspection station " +
    "that lets a small factory check every product for defects automatically, for under fifty thousand rupees.\""
  );
}

/* =========================================================
   SLIDE 2 — PROBLEM & GAP
   ========================================================= */
{
  const s = slide();
  chrome(s, "The problem & the gap", "Quality control in Indian MSMEs is still done by tired human eyes.", "01 / 12", 21.5);

  const LX = M, LW = 5.55;
  // hero problem stat
  s.addText("5–15%", {
    x: LX, y: 1.58, w: LW, h: 0.86, margin: 0, valign: "middle",
    fontFace: F, fontSize: 50, bold: true, color: RED,
  });
  s.addText("of defective output still reaches the customer\n→ returns, rejections, lost orders", {
    x: LX, y: 2.46, w: LW, h: 0.7, margin: 0, valign: "top",
    fontFace: F, fontSize: 13, color: WHITE, lineSpacingMultiple: 1.2,
  });

  rich(s, LX, 3.42, LW, 0.72, [
    ["2–4 QC workers", { bold: true, color: RED }],
    [" per shift, accuracy drops ", {}],
    ["30–40%", { bold: true, color: RED }],
    [" after 2 hours", {}],
  ], { fontSize: 13.5, color: WHITE });

  rich(s, LX, 4.22, LW, 0.72, [
    ["MSME loses ", {}],
    ["₹2–10 lakh", { bold: true, color: RED }],
    [" per year on defects that a machine would catch", {}],
  ], { fontSize: 13.5, color: WHITE });

  // right: comparison table
  const RX = 6.75, RW = 5.96;
  s.addText("Machine vision exists, but not for small factories.", {
    x: RX, y: 1.58, w: RW, h: 0.36, margin: 0, valign: "middle",
    fontFace: F, fontSize: 14, bold: true, color: WHITE,
  });
  table(s, RX, 2.0, [1.62, 2.28, 2.06], [
    ["", "Cognex / Keyence", "Our target"],
    ["Cost", { text: "₹5–20 lakh", opt: { bold: true, color: RED } }, { text: "Under ₹50,000", opt: { bold: true, color: TEAL } }],
    ["Setup", "Vision engineer,\n2–4 weeks", "Plug-and-play,\n30 min"],
    ["New product", "Re-program", "Owner trains it himself"],
  ], { rowH: 0.55, fontSize: 11.5 });

  card(s, RX, 4.42, RW, 0.86, TINT);
  s.addText("No product under ₹1 lakh with AI and no-code training exists in India.", {
    x: RX + 0.26, y: 4.42, w: RW - 0.52, h: 0.86, margin: 0, valign: "middle",
    fontFace: F, fontSize: 14, bold: true, color: TEAL, lineSpacingMultiple: 1.15,
  });

  // bottom: cost gap bars
  s.addShape(pres.ShapeType.rect, { x: M, y: 5.86, w: 7.4, h: 0.42, fill: { color: RED } });
  s.addText("₹5–20 lakh", {
    x: M + 0.18, y: 5.86, w: 3.0, h: 0.42, margin: 0, valign: "middle",
    fontFace: F, fontSize: 14.5, bold: true, color: WHITE,
  });
  s.addText("Cognex / Keyence today", {
    x: 8.22, y: 5.86, w: 4.4, h: 0.42, margin: 0, valign: "middle",
    fontFace: F, fontSize: 11.5, color: MUTED,
  });
  s.addShape(pres.ShapeType.rect, { x: M, y: 6.4, w: 0.62, h: 0.42, fill: { color: TEAL } });
  s.addText("Under ₹50,000 — our target", {
    x: 1.36, y: 6.4, w: 6.0, h: 0.42, margin: 0, valign: "middle",
    fontFace: F, fontSize: 14.5, bold: true, color: TEAL,
  });

  s.addNotes(
    "60 sec. Every small factory has the same weak point — the last step is a worker looking at each piece and deciding good or bad. " +
    "After two hours, accuracy drops by thirty to forty percent and defects slip through. That costs a typical MSME two to ten lakh a year " +
    "in returns and rejected batches. Machine vision solves this — but Cognex and Keyence start at five lakh and need a trained vision engineer. " +
    "An MSME making a different product every week cannot call an engineer every week. The gap is not whether this can be done — it is that " +
    "nobody has made it cheap enough and simple enough for a small factory."
  );
}

/* =========================================================
   SLIDE 3 — OUR SOLUTION
   ========================================================= */
{
  const s = slide();
  chrome(s, "Our solution", "A plug-and-play inspection box that the factory owner trains himself.", "02 / 12", 21);

  bullets(s, M, 1.65, 6.55, 3.3, [
    "Sits at the end of any existing line — table-top or on a conveyor",
    "Owner shows it 50 good pieces and 50 bad pieces, taps “Train”",
    "Ready to inspect in about 30 minutes",
    "Decides PASS or FAIL in under 200 milliseconds, 30–60 pieces per minute",
  ], 14, WHITE, 22);

  card(s, 7.55, 1.65, 5.16, 2.1);
  label(s, 7.9, 2.02, 4.5, "Target price to the MSME");
  s.addText("Under ₹50,000", {
    x: 7.9, y: 2.38, w: 4.5, h: 0.95, margin: 0, valign: "middle",
    fontFace: F, fontSize: 36, bold: true, color: TEAL,
  });

  // 5-step training strip
  label(s, M, 4.95, 6.0, "How the owner trains it");
  const steps = ["Show 50 good", "Show 50 defective", "Tap “Train”", "Auto-train 15 min", "Inspecting"];
  const n = steps.length, gap = 0.32;
  const cwid = (CW - (n - 1) * gap) / n;
  steps.forEach((t, i) => {
    const x = M + i * (cwid + gap);
    card(s, x, 5.32, cwid, 1.25);
    s.addText(String(i + 1).padStart(2, "0"), {
      x: x + 0.2, y: 5.44, w: cwid - 0.4, h: 0.3, margin: 0,
      fontFace: F, fontSize: 11, bold: true, color: TEAL, charSpacing: 1,
    });
    s.addText(t, {
      x: x + 0.2, y: 5.78, w: cwid - 0.4, h: 0.68, margin: 0, valign: "top",
      fontFace: F, fontSize: 12.5, bold: true, color: WHITE, lineSpacingMultiple: 1.1,
    });
    if (i < n - 1) {
      s.addText("→", {
        x: x + cwid, y: 5.32, w: gap, h: 1.25, margin: 0, align: "center", valign: "middle",
        fontFace: F, fontSize: 14, bold: true, color: TEAL,
      });
    }
  });

  s.addNotes(
    "50 sec. Our answer is a small box you place at the end of the line. The owner shows it fifty good pieces and fifty bad pieces and taps " +
    "one button. Fifteen minutes later it is checking parts on its own, about one piece every second, and telling the operator pass or fail. " +
    "No coding, no engineer, no change to the line."
  );
}

/* =========================================================
   SLIDE 4 — HOW IT WORKS (TECHNOLOGY)
   ========================================================= */
{
  const s = slide();
  chrome(s, "How it works — technology", "System block diagram", "03 / 12");
  s.addText("Sensor trigger → lit imaging chamber → AI on the edge → two output paths", {
    x: M, y: 1.36, w: CW, h: 0.34, margin: 0, valign: "middle",
    fontFace: F, fontSize: 14, color: TEAL,
  });

  placeholder(s, 2.55, 1.86, 8.23, 3.1, "BLOCK DIAGRAM — INSERT IMAGE HERE");

  const items = [
    [["Trigger: ", { bold: true, color: TEAL }], ["IR proximity sensor + Arduino Nano", {}]],
    [["Imaging: ", { bold: true, color: TEAL }], ["1080p/5MP USB camera inside a 400×300×300 mm chamber with LED ring light", {}]],
    [["Brain: ", { bold: true, color: TEAL }], ["Raspberry Pi 5 — MobileNetV2 CNN on TensorFlow Lite, runs offline", {}]],
    [["Path 1 — Act: ", { bold: true, color: TEAL }], ["display, buzzer, LED tower, optional pneumatic reject", {}]],
    [["Path 2 — Learn & report: ", { bold: true, color: TEAL }], ["ESP32 over MQTT → phone dashboard (yield %, defect trend)", {}]],
  ];
  paras(s, M, 5.18, 5.85, 1.7, items.slice(0, 3), 11.5, 11);
  paras(s, 6.85, 5.18, 5.85, 1.7, items.slice(3), 11.5, 11);

  s.addNotes(
    "60 sec. A sensor sees the part arrive and triggers the camera. The camera sits inside a lit chamber, so lighting is always the same — " +
    "that is the trick that lets a four-thousand-rupee camera do the job of a one-lakh camera. A Raspberry Pi runs the AI model on the device " +
    "itself, so the factory does not need internet. Then two things happen: the operator gets an instant pass or fail signal, and the result " +
    "goes to the owner's phone as a live yield dashboard."
  );
}

/* =========================================================
   SLIDE 5 — WHAT IS ACTUALLY NEW
   ========================================================= */
{
  const s = slide();
  chrome(s, "Innovation", "Five things that make this different, not just cheaper", "04 / 12");

  // [lead, description, description line count at full column width]
  const rows = [
    ["Few-shot training on the device", "50–100 samples, transfer learning runs on the Pi itself. No cloud, no data leaving the factory.", 1],
    ["Controlled optics instead of a costly camera", "The lit chamber does the work that expensive industrial cameras normally do.", 1],
    ["Closed lighting loop", "The Pi measures image brightness and corrects the LED ring automatically, so the model stays valid as daylight changes through the shift.", 2],
    ["Operator-in-the-loop retraining", "A wrong call is flagged on the screen and feeds back into the model. Accuracy improves week by week.", 1],
    ["Retrofit-first design", "Bolts onto an existing table or belt in 30 minutes. No line redesign.", 1],
  ];
  const top = 1.62, rh = 1.0, g = 0.08;
  rows.forEach((r, i) => {
    const y = top + i * (rh + g);
    const blockH = 0.34 + r[2] * 0.2;
    const off = (rh - blockH) / 2;
    card(s, M, y, CW, rh, i % 2 === 0 ? PANEL : ROW_A);
    s.addText(String(i + 1).padStart(2, "0"), {
      x: M + 0.3, y: y + off - 0.03, w: 0.8, h: 0.4, margin: 0, valign: "middle",
      fontFace: F, fontSize: 22, bold: true, color: TEAL,
    });
    s.addText(r[0], {
      x: M + 1.25, y: y + off, w: CW - 1.6, h: 0.32, margin: 0, valign: "middle",
      fontFace: F, fontSize: 14, bold: true, color: WHITE,
    });
    s.addText(r[1], {
      x: M + 1.25, y: y + off + 0.34, w: CW - 1.6, h: r[2] * 0.22, margin: 0, valign: "top",
      fontFace: F, fontSize: 11.5, color: MUTED, lineSpacingMultiple: 1.1,
    });
  });

  s.addNotes(
    "60 sec. Cheap alone is not innovation. First, training runs on the device from about fifty samples — no data leaves the factory and no AI " +
    "expert is needed. Second, we spend money on controlled lighting instead of an expensive camera — that is the core cost insight. Third, the " +
    "system corrects its own lighting as the day changes, which is the number one reason low-cost vision fails on a real shop floor. Fourth, when " +
    "the operator disagrees with the machine, that correction retrains the model. Fifth, it retrofits — nobody has to rebuild their line."
  );
}

/* =========================================================
   SLIDE 6 — COST PROOF (BOM)
   ========================================================= */
{
  const s = slide();
  chrome(s, "Cost proof", "How we hold ₹50,000", "05 / 12");
  s.addText("Bill of materials — checked against live Indian listings, August 2026", {
    x: M, y: 1.32, w: CW, h: 0.3, margin: 0, valign: "middle",
    fontFace: F, fontSize: 12.5, color: MUTED,
  });

  const hi = { rowFill: TEAL_D, bold: true, color: WHITE };
  table(s, M, 1.82, [6.05, 2.3], [
    ["Item", "Cost"],
    ["Raspberry Pi 5 (8 GB) + power + cooling + storage", "₹10,000–11,000"],
    ["5 MP USB camera module + lens", "₹4,200–4,500"],
    ["LED ring light + diffuser + driver", "₹1,500–3,000"],
    ["7\" touchscreen", "₹5,000–7,000"],
    ["Enclosure, platform, mounts (sheet metal / ACP)", "₹4,000–6,000"],
    ["Arduino Nano, ESP32, IR sensor, buzzer, LED tower", "₹2,000–2,500"],
    ["12 V SMPS, wiring, connectors", "₹1,200–1,500"],
    [{ text: "Prototype BOM (single unit)", opt: hi }, { text: "≈ ₹28,000–35,000", opt: Object.assign({}, hi) }],
    [{ text: "At 100-unit batch", opt: { bold: true, color: TEAL } }, { text: "≈ ₹24,000–27,000", opt: { bold: true, color: TEAL } }],
  ], { rowH: 0.44, fontSize: 11.5, alignRight: true });

  const SX = 9.3, SW = 3.41;
  const stats = [
    ["₹49,000", "Selling price to the MSME", WHITE, 30, 1.35],
    ["40–45%", "Gross margin at 100-unit batch", TEAL, 30, 1.35],
    ["₹15,000–18,000", "Optional add-on: mini conveyor + pneumatic reject", WHITE, 20, 1.5],
  ];
  let sy = 1.82;
  stats.forEach((st) => {
    card(s, SX, sy, SW, st[4]);
    s.addText(st[0], {
      x: SX + 0.26, y: sy + 0.18, w: SW - 0.52, h: 0.55, margin: 0, valign: "middle",
      fontFace: F, fontSize: st[3], bold: true, color: st[2],
    });
    s.addText(st[1], {
      x: SX + 0.26, y: sy + 0.76, w: SW - 0.52, h: 0.6, margin: 0, valign: "top",
      fontFace: F, fontSize: 10.5, color: MUTED, lineSpacingMultiple: 1.12,
    });
    sy += st[4] + 0.1;
  });

  s.addNotes(
    "45 sec. These are current Indian supplier prices, not estimates. A Raspberry Pi 5 with power and cooling is about ten thousand. A five-megapixel " +
    "USB camera module is around four thousand two hundred. Add lighting, screen, enclosure and controls and a single prototype comes to roughly " +
    "thirty thousand. At a hundred-unit batch it drops to about twenty-five thousand. That is how we sell at forty-nine thousand and still hold a " +
    "healthy margin. Backup slide B5 has the live listings."
  );
}

/* =========================================================
   SLIDE 7 — TARGET MARKET & OPPORTUNITY
   ========================================================= */
{
  const s = slide();
  chrome(s, "Target market & business opportunity", "This is a product business, not a project.", "06 / 12");

  table(s, M, 1.5, [5.0, 3.5, 3.593], [
    ["", "Size", "Our price point"],
    ["Manufacturing MSMEs in India", "35 lakh+", { text: "₹49,000/station", opt: { bold: true, color: TEAL } }],
    ["Gujarat GIDC clusters alone", "5+ lakh MSMEs", { text: "~₹50 crore opportunity", opt: { bold: true, color: TEAL } }],
    ["1% national penetration", "35,000 stations", { text: "~₹175 crore", opt: { bold: true, color: TEAL } }],
  ], { rowH: 0.42, fontSize: 11.5 });

  s.addText("We start where we can drive to", {
    x: M, y: 3.34, w: CW, h: 0.3, margin: 0, valign: "middle",
    fontFace: F, fontSize: 14, bold: true, color: WHITE,
  });

  const years = [
    ["Year 1", "Morbi ceramics", "1,000+ tile factories, every tile graded by hand today.", "50 stations", "₹25 lakh revenue"],
    ["Year 2", "Surat textiles + Rajkot auto parts", "", "200 stations", "₹1 crore revenue"],
    ["Year 3", "Multi-cluster Gujarat + first Maharashtra orders", "", "500 stations", "₹2.5 crore revenue"],
  ];
  const g = 0.3, cwid = (CW - 2 * g) / 3;
  years.forEach((yr, i) => {
    const x = M + i * (cwid + g);
    card(s, x, 3.72, cwid, 2.2);
    label(s, x + 0.26, 3.92, cwid - 0.52, yr[0], TEAL);
    s.addText(yr[1], {
      x: x + 0.26, y: 4.16, w: cwid - 0.52, h: 0.58, margin: 0, valign: "top",
      fontFace: F, fontSize: 14, bold: true, color: WHITE, lineSpacingMultiple: 1.08,
    });
    if (yr[2]) {
      s.addText(yr[2], {
        x: x + 0.26, y: 4.76, w: cwid - 0.52, h: 0.42, margin: 0, valign: "top",
        fontFace: F, fontSize: 10.5, color: MUTED, lineSpacingMultiple: 1.1,
      });
    }
    s.addText(yr[3], {
      x: x + 0.26, y: 5.2, w: cwid - 0.52, h: 0.32, margin: 0, valign: "middle",
      fontFace: F, fontSize: 15.5, bold: true, color: TEAL,
    });
    s.addText(yr[4], {
      x: x + 0.26, y: 5.5, w: cwid - 0.52, h: 0.28, margin: 0, valign: "middle",
      fontFace: F, fontSize: 11.5, color: WHITE,
    });
  });

  card(s, M, 6.02, CW, 0.88, TINT);
  rich(s, M + 0.26, 6.18, CW - 0.52, 0.6, [
    ["Impact on MSMEs: ", { bold: true, color: TEAL }],
    ["defect escape rate from 5–15% down to under 1%. QC workers move from staring at parts to running the line — no jobs lost, productivity gained.", { color: WHITE }],
  ], { fontSize: 12.5 });

  s.addNotes(
    "55 sec. We are building a product company. The total addressable market is one hundred seventy-five crore, but here is our honest plan: " +
    "fifty stations in year one, all in Morbi, ninety minutes from our workshop. Two hundred in year two, adding Surat and Rajkot. Five hundred " +
    "by year three — about two and a half crore in revenue. We start in Gujarat because we can drive to our customers, install, train and fix " +
    "problems in person. On impact — we are not removing jobs. The same worker stops staring at parts and starts running the machine."
  );
}

/* =========================================================
   SLIDE 8 — BUSINESS MODEL
   ========================================================= */
{
  const s = slide();
  chrome(s, "Business model", "Hardware sale + recurring revenue. Self-sustaining after the grant.", "07 / 12", 21.5);

  const LX = M, LW = 6.0;
  label(s, LX, 1.56, LW, "What we earn");
  table(s, LX, 1.88, [3.55, 2.45], [
    ["Revenue line", "Price"],
    ["Base station (one-time)", { text: "₹49,000", opt: { bold: true, color: TEAL } }],
    ["Conveyor + auto-reject add-on", { text: "₹18,000", opt: { bold: true, color: TEAL } }],
    ["Annual support + AI model updates", { text: "₹5,000 / year", opt: { bold: true, color: TEAL } }],
    ["Custom product category training", { text: "₹10,000 per category", opt: { bold: true, color: TEAL } }],
  ], { rowH: 0.44, fontSize: 11.5, alignRight: true });

  rich(s, LX, 4.38, LW, 0.9, [
    ["Route to market: ", { bold: true, color: TEAL }],
    ["Direct sales in Morbi and Surat first (we are local). Then through existing machinery dealers who already sell into these clusters. No distributor margin needed in Year 1.", { color: MUTED }],
  ], { fontSize: 11.5 });

  // right: payback visual
  const RX = 6.95, RW = 5.76;
  label(s, RX, 1.56, RW, "Why the MSME owner says yes");
  card(s, RX, 1.88, RW, 3.52);
  const IX = RX + 0.28, IW = RW - 0.56;
  s.addText("Payback in 2–4 months", {
    x: IX, y: 2.04, w: IW, h: 0.36, margin: 0, valign: "middle",
    fontFace: F, fontSize: 16, bold: true, color: TEAL,
  });
  label(s, IX, 2.52, IW, "Station cost (one-time)");
  s.addShape(pres.ShapeType.rect, { x: IX, y: 2.78, w: 4.9, h: 0.32, fill: { color: SLATE } });
  s.addText("₹49,000", {
    x: IX + 0.14, y: 2.78, w: 2.0, h: 0.32, margin: 0, valign: "middle",
    fontFace: F, fontSize: 12, bold: true, color: WHITE,
  });
  label(s, IX, 3.22, IW, "QC labour cost saved, per month");
  s.addShape(pres.ShapeType.rect, { x: IX, y: 3.48, w: 2.6, h: 0.32, fill: { color: TEAL } });
  s.addText("₹24,000–28,000", {
    x: IX + 0.14, y: 3.48, w: 2.4, h: 0.32, margin: 0, valign: "middle",
    fontFace: F, fontSize: 12, bold: true, color: "0F2231",
  });
  label(s, IX, 3.92, IW, "Break-even");
  s.addText("Month 2–4", {
    x: IX, y: 4.16, w: IW, h: 0.42, margin: 0, valign: "middle",
    fontFace: F, fontSize: 22, bold: true, color: WHITE,
  });
  s.addText("Then saves ₹2–3 lakh a year and eliminates rejection losses.", {
    x: IX, y: 4.68, w: IW, h: 0.55, margin: 0, valign: "top",
    fontFace: F, fontSize: 11.5, color: MUTED, lineSpacingMultiple: 1.12,
  });

  // bottom: unit economics
  label(s, M, 5.72, 6.0, "Unit economics");
  const chips = [
    ["BOM at 100 units", "₹25,000", WHITE],
    ["Selling price", "₹49,000", WHITE],
    ["Gross margin per unit", "₹24,000 (49%)", TEAL],
  ];
  const cw2 = 3.7, ag = 0.45;
  chips.forEach((c, i) => {
    const x = M + i * (cw2 + ag);
    card(s, x, 6.0, cw2, 0.88, ROW_A);
    label(s, x + 0.24, 6.13, cw2 - 0.48, c[0]);
    s.addText(c[1], {
      x: x + 0.24, y: 6.39, w: cw2 - 0.48, h: 0.38, margin: 0, valign: "middle",
      fontFace: F, fontSize: 15, bold: true, color: c[2],
    });
    if (i < chips.length - 1) {
      s.addText("→", {
        x: x + cw2, y: 6.0, w: ag, h: 0.88, margin: 0, align: "center", valign: "middle",
        fontFace: F, fontSize: 14, bold: true, color: TEAL,
      });
    }
  });

  s.addNotes(
    "50 sec. We sell the station, then earn every year from support, model updates and custom training. For the customer the maths is easy — two QC " +
    "workers cost about twenty-five thousand a month, so the box pays for itself in two to four months. That short payback is what makes a " +
    "cost-conscious MSME owner say yes. At a hundred-unit batch the BOM is about twenty-five thousand and we sell at forty-nine thousand — " +
    "forty-nine percent gross margin. The business is self-sustaining after the grant period."
  );
}

/* =========================================================
   SLIDE 9 — CURRENT STAGE (VERSION B)
   ========================================================= */
{
  const s = slide();
  chrome(s, "Where we are today", "Current stage: validated concept, build starting", "08 / 12");

  bullets(s, M, 1.6, CW, 2.4, [
    "Full system architecture and BOM complete, suppliers identified",
    "AI pipeline tested on a public defect image dataset — [x]% accuracy on [x] classes",
    "[x] MSME owners interviewed in [Morbi / Surat]; all confirmed manual inspection is their weak point",
    "Team has already built and shipped hardware products — see team slide",
    { text: "Grant funds go straight into the first physical prototype", opt: { bold: true, color: TEAL } },
  ], 14, WHITE, 13);

  const g = 0.23, pw = (CW - g) / 2;
  placeholder(s, M, 4.2, pw, 2.65, "PHOTO — BENCH SETUP / IMAGING CHAMBER");
  placeholder(s, M + pw + g, 4.2, pw, 2.65, "SCREENSHOT — MODEL OUTPUT (PASS / FAIL)");

  s.addNotes(
    "45 sec. To be straight with you — the architecture, the bill of materials and the software pipeline are done, and we have tested the model on " +
    "defect image datasets. What we have not built yet is the physical station, and that is exactly what this grant is for. What we do bring is a " +
    "team that has built hardware before, so this is not our first machine."
  );
}

/* =========================================================
   SLIDE 10 — 12-MONTH MILESTONE PLAN
   ========================================================= */
{
  const s = slide();
  chrome(s, "Milestones", "12-month milestone plan", "09 / 12");

  const q = [
    ["Months 1–3", "Alpha station built; dataset and training pipeline", "1 working unit, ≥90% accuracy on lab samples"],
    ["Months 4–6", "Beta v1 ×3 units; no-code training screen; phone dashboard", "3 units installed in 3 factories"],
    ["Months 7–9", "Field hardening; lighting loop; conveyor + reject add-on; electrical safety pre-check", "≥95% accuracy on 2 real product families, 30–60 parts/min"],
    ["Months 10–12", "10 units built; design registration and patent filing; manufacturing BOM frozen", "10 pilot or paying customers, BOM under ₹27,000"],
  ];
  const g = 0.28, cwid = (CW - 3 * g) / 4;
  const centers = q.map((_, i) => M + i * (cwid + g) + cwid / 2);

  s.addShape(pres.ShapeType.line, {
    x: centers[0], y: 2.12, w: centers[3] - centers[0], h: 0,
    line: { color: LINE, width: 1.25 },
  });
  q.forEach((it, i) => {
    const x = M + i * (cwid + g);
    s.addShape(pres.ShapeType.ellipse, {
      x: centers[i] - 0.09, y: 2.03, w: 0.18, h: 0.18, fill: { color: TEAL },
    });
    card(s, x, 2.45, cwid, 3.55);
    s.addShape(pres.ShapeType.rect, { x, y: 4.3, w: cwid, h: 1.7, fill: { color: PANEL_D } });
    label(s, x + 0.24, 2.63, cwid - 0.48, it[0], TEAL);
    s.addText(it[1], {
      x: x + 0.24, y: 2.92, w: cwid - 0.48, h: 1.3, margin: 0, valign: "top",
      fontFace: F, fontSize: 13.5, bold: true, color: WHITE, lineSpacingMultiple: 1.12,
    });
    label(s, x + 0.24, 4.45, cwid - 0.48, "Proof at the end");
    s.addText(it[2], {
      x: x + 0.24, y: 4.73, w: cwid - 0.48, h: 1.15, margin: 0, valign: "top",
      fontFace: F, fontSize: 12, color: TEAL, lineSpacingMultiple: 1.12,
    });
  });

  s.addNotes(
    "35 sec. Twelve months, four milestones, each one with something you can physically inspect at the end. First quarter, one working unit. " +
    "Second, three units inside real factories. Third, hardened in the field and measured. Fourth, ten units, IP filed and a manufacturing-ready cost."
  );
}

/* =========================================================
   SLIDE 11 — FUND UTILIZATION
   ========================================================= */
{
  const s = slide();
  chrome(s, "Fund utilization plan", "Requested: ₹15,00,000", "10 / 12");
  s.addText("MSME Innovative Scheme — released against milestones through AIC-GISC", {
    x: M, y: 1.32, w: CW, h: 0.3, margin: 0, valign: "middle",
    fontFace: F, fontSize: 12.5, color: MUTED,
  });

  const heads = [
    ["Prototype hardware — 10 stations across builds", 450000, "30%", "00B4D8"],
    ["Cameras, lenses, lighting, sensors, spares", 200000, "13%", "48CAE4"],
    ["AI development — dataset capture, annotation, edge optimisation, compute", 250000, "17%", "0077B6"],
    ["Enclosure design, tooling and fabrication", 180000, "12%", "023E8A"],
    ["Field pilots — installation, travel, on-site data collection", 120000, "8%", "90E0EF"],
    ["Testing — electrical safety and EMI/EMC pre-compliance", 100000, "7%", "0096C7"],
    ["IP — design registration and patent drafting/filing", 100000, "7%", "5C8AA6"],
    ["Dashboard app and cloud for 12 months", 70000, "5%", "34687E"],
    ["Contingency", 30000, "2%", "7FB3C8"],
  ];

  s.addChart(pres.ChartType.doughnut, [{
    name: "Fund utilization",
    labels: heads.map((h) => h[0]),
    values: heads.map((h) => h[1]),
  }], {
    x: 0.5, y: 1.72, w: 4.5, h: 4.2,
    holeSize: 62,
    chartColors: heads.map((h) => h[3]),
    dataBorder: { pt: 2, color: NAVY },
    showLegend: false, showTitle: false, showValue: false,
    chartArea: { fill: { color: NAVY } },
    plotArea: { fill: { color: NAVY } },
  });
  s.addText(
    [
      { text: "₹15,00,000", options: { fontSize: 17, bold: true, color: TEAL, breakLine: true } },
      { text: "TOTAL", options: { fontSize: 9.5, bold: true, color: DIM, charSpacing: 1.6 } },
    ],
    { x: 1.65, y: 3.47, w: 2.2, h: 0.7, margin: 0, align: "center", valign: "middle", fontFace: F }
  );

  const money = (v) => "₹" + v.toLocaleString("en-IN");
  const rows = [[{ text: "", opt: { fill: { color: NAVY } } }, "Head", "Amount", "%"]];
  heads.forEach((h) => {
    rows.push([
      { text: "", opt: { rowFill: h[3] } },
      h[0],
      { text: money(h[1]), opt: { bold: true } },
      { text: h[2], opt: { color: TEAL, bold: true } },
    ]);
  });
  rows.push([
    { text: "", opt: { rowFill: TEAL_D } },
    { text: "Total", opt: { rowFill: TEAL_D, bold: true } },
    { text: "₹15,00,000", opt: { rowFill: TEAL_D, bold: true } },
    { text: "100%", opt: { rowFill: TEAL_D, bold: true } },
  ]);
  table(s, 5.3, 1.75, [0.14, 4.62, 1.42, 0.85], rows, {
    rowH: 0.34, fontSize: 10, alignRight: true, alignFrom: 2, headFontSize: 9,
  });

  card(s, M, 6.08, CW, 0.85, TINT);
  s.addText(
    [
      { text: "No salaries, rent or land claimed. Every rupee goes into the prototype and its validation.", options: { fontSize: 13, bold: true, color: TEAL, breakLine: true } },
      { text: "After the grant: with 10 stations built and pilots running, the business sustains itself from unit sales — no second round of grant needed.", options: { fontSize: 11, color: WHITE } },
    ],
    { x: M + 0.26, y: 6.14, w: CW - 0.52, h: 0.72, margin: 0, valign: "middle", fontFace: F, lineSpacingMultiple: 1.15 }
  );

  s.addNotes(
    "45 sec. We are asking for the full fifteen lakh, drawn milestone by milestone through AIC-GISC. Thirty percent goes into building ten physical " +
    "stations, because units in real factories are what turn this from a drawing into a product. Another seventeen percent into the AI work and data " +
    "collection. We have deliberately claimed nothing for salaries or rent — the entire grant goes into hardware, validation and IP."
  );
}

/* =========================================================
   SLIDE 12 — TEAM
   ========================================================= */
{
  const s = slide();
  chrome(s, "The people building it", "Team", "11 / 12");

  const people = [
    ["Jenil Patel", "Applicant, Technical Lead",
      "Co-founder and CTO, Liquidus (metal 3D printing). [Degree, college]. Builds embedded systems and machine control. [One line on the most relevant thing he has built.]"],
    ["Preyansh Patel", "Product and Engineering",
      "MSc Advanced Engineering Design, Brunel University London. Ex Mercedes-Benz R&D, Switch Mobility, Lime London. Founder of Liquidus and of a hardware & AI prototyping studio in Ahmedabad."],
  ];
  const g = 0.31, cwid = (CW - g) / 2;
  people.forEach((p, i) => {
    const x = M + i * (cwid + g);
    card(s, x, 1.5, cwid, 3.5);
    s.addShape(pres.ShapeType.ellipse, {
      x: x + 0.42, y: 1.82, w: 1.25, h: 1.25,
      fill: { color: PANEL_D }, line: { color: DASH, width: 1.25, dashType: "dash" },
    });
    s.addText("PHOTO", {
      x: x + 0.42, y: 1.82, w: 1.25, h: 1.25, margin: 0, align: "center", valign: "middle",
      fontFace: F, fontSize: 9, bold: true, color: "728EA3", charSpacing: 1.2,
    });
    s.addText(p[0], {
      x: x + 1.88, y: 1.92, w: cwid - 2.3, h: 0.45, margin: 0, valign: "middle",
      fontFace: F, fontSize: 20, bold: true, color: WHITE,
    });
    s.addText(p[1], {
      x: x + 1.88, y: 2.4, w: cwid - 2.3, h: 0.32, margin: 0, valign: "middle",
      fontFace: F, fontSize: 12, color: TEAL,
    });
    s.addText(p[2], {
      x: x + 0.42, y: 3.32, w: cwid - 0.84, h: 1.45, margin: 0, valign: "top",
      fontFace: F, fontSize: 12, color: MUTED, lineSpacingMultiple: 1.18,
    });
  });

  card(s, M, 5.26, CW, 0.8, TINT);
  rich(s, M + 0.26, 5.42, CW - 0.52, 0.5, [
    ["Together: ", { bold: true, color: TEAL }],
    ["we have designed, built and debugged real machines — not slideware. Hardware, electronics, AI and CAD are all in-house.", { color: WHITE }],
  ], { fontSize: 12.5 });

  rich(s, M + 0.26, 6.35, CW - 0.52, 0.5, [
    ["Mentor / Host support: ", { bold: true, color: TEAL }],
    ["AIC-GISC Foundation, GTU — lab access, testing and mentoring.", { color: MUTED }],
  ], { fontSize: 12 });

  s.addNotes(
    "30 sec. We are two engineers who build machines. I handle the electronics and control side. My co-founder has a masters in advanced engineering " +
    "design from Brunel in London and has worked in R&D at Mercedes-Benz and Switch Mobility. We already run a hardware startup together, so the " +
    "workshop, the CAD, the electronics and the AI are all in-house. Thank you — I am happy to take questions."
  );
}

/* =========================================================
   B1 — COMPETITOR COMPARISON
   ========================================================= */
{
  const s = slide();
  chrome(s, "Backup", "Competitor comparison", "B1");

  table(s, M, 1.8, [3.3, 2.5, 6.293], [
    ["Option", "Price", "What it means for an MSME"],
    ["Cognex / Keyence", "₹5–20 lakh", "Vision engineer needed."],
    ["Chinese smart cameras", "₹1.5–3 lakh", "No local support; fixed rules, not learning."],
    ["Cloud AI vision services", "Monthly fee", "Needs internet, and factory data leaves the site."],
    [
      { text: "Dhrishti", opt: { rowFill: TEAL_D, bold: true } },
      { text: "₹49,000", opt: { rowFill: TEAL_D, bold: true } },
      { text: "Offline, and trained by the operator himself.", opt: { rowFill: TEAL_D, bold: true } },
    ],
  ], { rowH: [0.42, 0.85, 0.85, 0.85, 0.85], fontSize: 12 });

  card(s, M, 5.85, CW, 0.85, TINT);
  s.addText("No product under ₹1 lakh with AI and no-code training exists in India.", {
    x: M + 0.26, y: 5.85, w: CW - 0.52, h: 0.85, margin: 0, valign: "middle",
    fontFace: F, fontSize: 14, bold: true, color: TEAL,
  });
  s.addNotes("Backup — open only if the committee asks who else is in this space.");
}

/* =========================================================
   B2 — ACCURACY: HOW WE WILL PROVE IT
   ========================================================= */
{
  const s = slide();
  chrome(s, "Backup", "Accuracy: how we will prove it", "B2");

  bullets(s, M, 1.75, 7.55, 3.4, [
    "Held-out test set, never used in training",
    "Reported as two numbers, not one: how many bad pieces we catch (recall) and how many good pieces we wrongly reject (false positive rate)",
    "Adjustable threshold — a customer can choose “catch everything” mode and accept more false rejects",
  ], 14, WHITE, 18);

  const SX = 8.62, SW = 4.11;
  const stats = [["95%+", "Catch rate (recall)", TEAL], ["Under 5%", "False rejects", WHITE]];
  let y = 1.75;
  stats.forEach((st) => {
    card(s, SX, y, SW, 1.5);
    s.addText(st[0], {
      x: SX + 0.28, y: y + 0.24, w: SW - 0.56, h: 0.62, margin: 0, valign: "middle",
      fontFace: F, fontSize: 34, bold: true, color: st[2],
    });
    s.addText(st[1], {
      x: SX + 0.28, y: y + 0.9, w: SW - 0.56, h: 0.4, margin: 0, valign: "top",
      fontFace: F, fontSize: 11.5, color: MUTED,
    });
    y += 1.7;
  });
  s.addText("Target, measured on two real product families after field hardening.", {
    x: SX, y: 5.15, w: SW, h: 0.7, margin: 0, valign: "top",
    fontFace: F, fontSize: 11, color: MUTED, lineSpacingMultiple: 1.15,
  });

  card(s, M, 4.15, 7.55, 1.35, ROW_A);
  s.addText("The operator feedback loop exists because we expect the first weeks in a new factory to need correction. Every disagreement is logged and retrains the model.", {
    x: M + 0.26, y: 4.15, w: 7.03, h: 1.35, margin: 0, valign: "middle",
    fontFace: F, fontSize: 12, color: WHITE, lineSpacingMultiple: 1.18,
  });
  s.addNotes("Backup — open if asked how 95% will be demonstrated. Recall and false-reject rate are always reported separately.");
}

/* =========================================================
   B3 — RISKS
   ========================================================= */
{
  const s = slide();
  chrome(s, "Backup", "Risks and how we handle them", "B3");

  table(s, M, 1.75, [4.6, 7.493], [
    ["Risk", "Handling"],
    ["Ambient light changes through the day", "Closed chamber + automatic LED brightness correction"],
    ["Too few defect samples to train", "Image augmentation, plus an anomaly-detection fallback that learns from good pieces only"],
    ["Dust and heat in ceramic and textile plants", "Sealed enclosure, fanless design, filtered air path"],
    ["Missed defects damaging trust", "Recall-priority mode; every disagreement is logged and retrains the model"],
    ["Cheap copies", "Advantage is local service, the training workflow and cluster relationships — not the parts"],
  ], { rowH: [0.42, 0.88, 0.88, 0.88, 0.88, 0.88], fontSize: 12 });
  s.addNotes("Backup — open if asked about technical or commercial risk.");
}

/* =========================================================
   B4 — WHERE THIS DOES NOT APPLY
   ========================================================= */
{
  const s = slide();
  chrome(s, "Backup", "Where this does not apply — knowing our limits", "B4");

  const g = 0.31, cwid = (CW - g) / 2;
  card(s, M, 2.62, cwid, 3.2, ROW_A);
  label(s, M + 0.32, 2.92, cwid - 0.64, "Not for");
  bullets(s, M + 0.32, 3.32, cwid - 0.64, 1.5, [
    "Micron-level metrology",
    "Very high-speed web inspection",
    "Internal or subsurface defects",
  ], 14, WHITE, 14);
  s.addText("Those need laser or X-ray systems.", {
    x: M + 0.32, y: 4.92, w: cwid - 0.64, h: 0.4, margin: 0, valign: "top",
    fontFace: F, fontSize: 12, color: MUTED,
  });

  const RX = M + cwid + g;
  card(s, RX, 2.62, cwid, 3.2, TINT);
  label(s, RX + 0.32, 2.92, cwid - 0.64, "We handle", TEAL);
  s.addText("Visible surface and packaging defects", {
    x: RX + 0.32, y: 3.27, w: cwid - 0.64, h: 0.35, margin: 0, valign: "middle",
    fontFace: F, fontSize: 15, bold: true, color: TEAL,
  });
  bullets(s, RX + 0.32, 3.77, cwid - 0.64, 1.95, [
    "Cracks and chips",
    "Stains and colour shift",
    "Print and seal errors",
    "Missing components",
  ], 14, WHITE, 14);
  s.addNotes("Backup — open if asked about accuracy limits or metrology. Being explicit about limits builds credibility.");
}

/* =========================================================
   B5 — COST EVIDENCE
   ========================================================= */
{
  const s = slide();
  chrome(s, "Backup", "Cost evidence — live supplier listings", "B5");
  s.addText("Screenshots taken from Indian suppliers with the date visible.", {
    x: M, y: 1.34, w: CW, h: 0.3, margin: 0, valign: "middle",
    fontFace: F, fontSize: 12.5, color: MUTED,
  });

  const shots = ["SCREENSHOT — RASPBERRY PI 5", "SCREENSHOT — USB CAMERA MODULE", "SCREENSHOT — 7\" TOUCHSCREEN"];
  const g = 0.3, cwid = (CW - 2 * g) / 3;
  shots.forEach((t, i) => {
    placeholder(s, M + i * (cwid + g), 1.85, cwid, 3.6, t);
  });

  card(s, M, 5.78, CW, 0.9, TINT);
  s.addText("Prototype BOM ≈ ₹28,000–35,000  ·  at 100 units ≈ ₹24,000–27,000  ·  selling price ₹49,000", {
    x: M + 0.26, y: 5.78, w: CW - 0.52, h: 0.9, margin: 0, valign: "middle",
    fontFace: F, fontSize: 14, bold: true, color: TEAL,
  });
  s.addNotes("Backup — open immediately if a member challenges the ₹50,000 cost. A live listing settles the point.");
}

pres.writeFile({ fileName: "Dhrishti_MSME_Hackathon6_PitchDeck.pptx" }).then((f) => console.log("wrote", f));
