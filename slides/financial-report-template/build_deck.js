#!/usr/bin/env node
/**
 * Financial report template — 23-slide deck, dark + light theme.
 *
 * Reproduces the "Financial report Template" layout family (Helvetica-style
 * mono-chrome deck: hero statements, native charts in rounded cards, tables,
 * bento highlights, dot grids).  Every chart is a native chart, so the deck
 * stays editable after import into Google Slides.
 *
 * Usage:
 *   node build_deck.js            # writes financial-report-dark.pptx + -light.pptx
 *   node build_deck.js dark       # one theme only
 */
const path = require("path");
const pptxgen = require("pptxgenjs");

// ---------------------------------------------------------------- themes ---
const THEMES = {
  dark: {
    name: "dark",
    bg: "000000",
    card: "1C1C1E",
    cardAlt: "2C2C2E",
    title: "FFFFFF",
    sub: "8E8E93", // secondary title line ("Template", "Q1 – Q4")
    text: "D1D1D6",
    muted: "8E8E93",
    faint: "48484A",
    axis: "3A3A3C",
    grid: "2C2C2E",
    // series ramps – light → dark on a dark ground
    s1: "E5E5EA",
    s2: "AEAEB2",
    s3: "636366",
    s4: "3A3A3C",
    tableHead: "1C1C1E",
    tableTotal: "3A3A3C",
    tableTotalText: "FFFFFF",
    dot: "8E8E93",
    imgPlaceholderA: "C7C7CC",
    imgPlaceholderB: "8E8E93",
  },
  light: {
    name: "light",
    bg: "FFFFFF",
    card: "F5F5F7",
    cardAlt: "E5E5EA",
    title: "000000",
    sub: "8E8E93",
    text: "3A3A3C",
    muted: "8E8E93",
    faint: "C7C7CC",
    axis: "C7C7CC",
    grid: "E5E5EA",
    s1: "D1D1D6",
    s2: "AEAEB2",
    s3: "8E8E93",
    s4: "636366",
    tableHead: "F5F5F7",
    tableTotal: "8E8E93",
    tableTotalText: "FFFFFF",
    dot: "AEAEB2",
    imgPlaceholderA: "C7C7CC",
    imgPlaceholderB: "8E8E93",
  },
};

const FONT = "Arial";
const W = 10;
const H = 5.625;
const M = 0.35; // page margin
const QUARTERS9 = ["Q4 22", "Q1 23", "Q2 23", "Q3 23", "Q4 23", "Q1 24", "Q2 24", "Q3 24", "Q4 24"];
const QUARTERS4 = ["Q1 24", "Q2 24", "Q3 24", "Q4 24"];
const FOOTNOTE =
  "Source: company filings and internal reporting. All figures in this template are illustrative placeholders — replace them with reported values " +
  "before distribution. Non-GAAP measures are reconciled to the most directly comparable GAAP measures in the appendix.";

// --------------------------------------------------------------- helpers ---
function label(slide, T, text, opts = {}) {
  slide.addText(text, {
    x: M, y: 0.2, w: 6, h: 0.2,
    fontFace: FONT, fontSize: 7, color: T.muted,
    isTextBox: true, margin: 0, valign: "top",
    ...opts,
  });
}

function title(slide, T, line1, line2, opts = {}) {
  const runs = [{ text: line1, options: { color: T.title, breakLine: !!line2 } }];
  if (line2) runs.push({ text: line2, options: { color: T.sub } });
  slide.addText(runs, {
    x: M, y: 0.36, w: 6.2, h: line2 ? 0.95 : 0.5,
    fontFace: FONT, fontSize: 22, bold: false,
    isTextBox: true, margin: 0, valign: "top", lineSpacingMultiple: 0.95,
    ...opts,
  });
}

function hero(slide, T, text, opts = {}) {
  slide.addText(text, {
    x: M, y: 0.3, w: 6.6, h: 1.25,
    fontFace: FONT, fontSize: 30, bold: true, color: T.title,
    isTextBox: true, margin: 0, valign: "top", lineSpacingMultiple: 0.95,
    ...opts,
  });
}

function card(slide, T, x, y, w, h, color) {
  slide.addShape("roundRect", {
    x, y, w, h,
    fill: { color: color || T.card },
    rectRadius: 0.1,
    line: { color: color || T.card, width: 0 },
  });
}

function body(slide, T, text, x, y, w, h, opts = {}) {
  slide.addText(text, {
    x, y, w, h,
    fontFace: FONT, fontSize: 7.5, color: T.text,
    isTextBox: true, margin: 0, valign: "top", paraSpaceAfter: 6,
    ...opts,
  });
}

function footnote(slide, T) {
  slide.addText(FOOTNOTE, {
    x: 1.8, y: 5.28, w: 6.4, h: 0.3,
    fontFace: FONT, fontSize: 4, color: T.muted,
    isTextBox: true, margin: 0, valign: "top",
  });
}

function copyright(slide, T) {
  slide.addText([
    { text: "© Company", options: { breakLine: true } },
    { text: "Date" },
  ], {
    x: M, y: 5.12, w: 3, h: 0.36,
    fontFace: FONT, fontSize: 7, color: T.title,
    isTextBox: true, margin: 0, valign: "bottom",
  });
}

function legend(slide, T, items, x, y) {
  // items: [{text, color}]
  items.forEach((it, i) => {
    const yy = y + i * 0.19;
    slide.addShape("ellipse", { x, y: yy + 0.03, w: 0.1, h: 0.1, fill: { color: it.color }, line: { color: it.color, width: 0 } });
    slide.addText(it.text, {
      x: x + 0.17, y: yy, w: 2.2, h: 0.16,
      fontFace: FONT, fontSize: 6.5, color: T.text, isTextBox: true, margin: 0, valign: "middle",
    });
  });
}

// quiet chart defaults shared by every native chart
function chartBase(T, extra = {}) {
  return {
    chartArea: { fill: { color: T.card }, roundedCorners: true },
    plotArea: { fill: { color: T.card } },
    catAxisLabelColor: T.muted,
    catAxisLabelFontSize: 6,
    catAxisLabelFontFace: FONT,
    valAxisLabelColor: T.muted,
    valAxisLabelFontSize: 6.5,
    valAxisLabelFontFace: FONT,
    catAxisLineShow: true,
    catAxisLineColor: T.axis,
    valAxisLineShow: false,
    valGridLine: { style: "none" },
    catGridLine: { style: "none" },
    showLegend: false,
    showTitle: false,
    dataLabelFontFace: FONT,
    dataLabelFontSize: 6.5,
    dataLabelColor: T.title,
    ...extra,
  };
}

// small bar chart in a card with a two-line header (used twice on two slides)
function miniBarCard(pres, slide, T, x, y, w, h, head, sub, labels, values, annotation) {
  card(slide, T, x, y, w, h);
  slide.addText([
    { text: head, options: { color: T.muted, breakLine: true } },
    { text: sub, options: { color: T.title, bold: true } },
  ], {
    x: x + 0.2, y: y + 0.15, w: w - 0.4, h: 0.4,
    fontFace: FONT, fontSize: 7.5, isTextBox: true, margin: 0, valign: "top",
  });
  if (annotation) {
    slide.addText(annotation, {
      x: x + w / 2, y: y + 0.55, w: w / 2 - 0.3, h: 0.2, align: "center",
      fontFace: FONT, fontSize: 7.5, color: T.muted, isTextBox: true, margin: 0,
    });
  }
  slide.addChart(pres.ChartType.bar, [{ name: sub, labels, values }], chartBase(T, {
    x: x + 0.1, y: y + 0.7, w: w - 0.2, h: h - 0.8,
    barDir: "col", barGapWidthPct: 45,
    chartColors: [T.s2],
    valAxisHidden: true,
    showValue: true, dataLabelPosition: "ctr", dataLabelColor: T.name === "dark" ? "FFFFFF" : "1C1C1E",
  }));
}

// ---------------------------------------------------------------- slides ---
const SLIDES = [];

// 1 · Cover
SLIDES.push((pres, T) => {
  const s = pres.addSlide();
  s.background = { color: T.bg };
  s.addText([
    { text: "Financial report", options: { color: T.title, breakLine: true } },
    { text: "Template", options: { color: T.sub } },
  ], {
    x: M, y: 0.3, w: 8, h: 1.7,
    fontFace: FONT, fontSize: 40, bold: true, isTextBox: true, margin: 0, valign: "top", lineSpacingMultiple: 0.95,
  });
  copyright(s, T);
  s.addNotes("Cover. Replace the grey second line with the reporting period (e.g. Q4 FY2024).");
});

// 2 · Disclaimer
SLIDES.push((pres, T) => {
  const s = pres.addSlide();
  s.background = { color: T.bg };
  s.addText("Disclaimer", {
    x: M, y: 0.3, w: 3, h: 0.3, fontFace: FONT, fontSize: 11, color: T.muted, isTextBox: true, margin: 0,
  });
  card(s, T, 3.75, 0.3, 5.9, 4.95);
  const sections = [
    ["Safe Harbor Statement",
      "This presentation includes forward-looking statements that are made pursuant to the safe harbor provisions of the Private Securities Litigation Reform Act of 1995. Forward-looking statements can often be identified by the use of terminology such as \"anticipates,\" \"expects,\" \"intends,\" \"plans,\" \"believes,\" \"seeks,\" \"estimates,\" \"could,\" \"should,\" \"will,\" \"may,\" \"project,\" \"forecast,\" and similar expressions. These statements reflect current expectations about future events and operating performance and speak only as of the date of this presentation. They are subject to risks, uncertainties, and other factors that could cause actual results to differ materially from those expressed or implied by the forward-looking statements."],
    ["Non-GAAP Financial Measures",
      "In this presentation, we may discuss non-GAAP financial measures. These measures are not prepared in accordance with Generally Accepted Accounting Principles (GAAP) and may differ from non-GAAP financial measures used by other companies. Non-GAAP financial measures should not be considered as a substitute for, or superior to, financial measures calculated in accordance with GAAP. A reconciliation of these non-GAAP financial measures to the most directly comparable GAAP measures is included in our SEC filings and on our investor relations website."],
    ["Industry and Market Data",
      "This presentation contains estimates and other statistical data made by independent parties and by us relating to market size and growth, as well as other industry data. This data involves a number of assumptions and limitations, and you are cautioned not to give undue weight to such estimates. While we believe these sources are reliable, we have not independently verified the accuracy or completeness of the information."],
    ["Third-Party Information",
      "Throughout this presentation, we may reference various third-party websites, data, or other information. We have not independently verified the accuracy or completeness of such information and make no representations about its accuracy or completeness."],
    ["Trademarks",
      "All trademarks, service marks, and trade names appearing in this presentation are the property of their respective owners."],
    ["Responsibility for Own Assessment",
      "By attending or receiving this presentation, you acknowledge that you are solely responsible for your own assessment of the market and our position in it, and that you will conduct your own independent analysis."],
    ["Contact Information",
      "For additional information, please refer to our investor relations website or contact our investor relations team."],
  ];
  const runs = [];
  sections.forEach(([h, p], i) => {
    runs.push({ text: h, options: { color: T.text, underline: { style: "sng" }, breakLine: true } });
    runs.push({ text: p, options: { color: T.muted, breakLine: i < sections.length - 1, paraSpaceAfter: 5 } });
  });
  s.addText(runs, {
    x: 3.95, y: 0.45, w: 5.5, h: 4.7, fontFace: FONT, fontSize: 4.6, isTextBox: true, margin: 0, valign: "top",
  });
  copyright(s, T);
});

// 3 · FY 2024 Highlights — bullet list + image placeholder
SLIDES.push((pres, T) => {
  const s = pres.addSlide();
  s.background = { color: T.bg };
  s.addText([
    { text: "FY 2024", options: { breakLine: true } },
    { text: "Highlights", options: { bold: true } },
  ], { x: M, y: 0.25, w: 3, h: 0.4, fontFace: FONT, fontSize: 8, color: T.title, isTextBox: true, margin: 0, valign: "top" });
  const items = [
    "Revenue grew +18% Y/Y to $525 million",
    "US revenue grew +23% Y/Y to $337 million",
    "US commercial revenue grew +26% Y/Y and +39% Q/Q to $107 million",
  ];
  s.addText(items.map((t, i) => ({
    text: t,
    options: { bullet: { code: "25B8" }, breakLine: i < items.length - 1, paraSpaceAfter: 10 },
  })), {
    x: M, y: 2.7, w: 4.3, h: 2.6, fontFace: FONT, fontSize: 11, color: T.title, isTextBox: true, margin: 0, valign: "bottom",
  });
  // image placeholder (replace with a product / office photo)
  s.addShape("roundRect", {
    x: 5.15, y: 0.25, w: 4.5, h: 5.1, rectRadius: 0.08,
    fill: { color: T.imgPlaceholderA }, line: { color: T.imgPlaceholderA, width: 0 },
  });
  s.addShape("roundRect", {
    x: 5.15, y: 2.8, w: 4.5, h: 2.55, rectRadius: 0.08,
    fill: { color: T.imgPlaceholderB, transparency: 55 }, line: { color: T.imgPlaceholderB, width: 0, transparency: 100 },
  });
  s.addNotes("Replace the grey block on the right with a full-bleed image.");
});

// 4 · Growth accelerated to 81% YoY — area chart
SLIDES.push((pres, T) => {
  const s = pres.addSlide();
  s.background = { color: T.bg };
  label(s, T, "Revenue");
  hero(s, T, "Growth accelerated to\n81% year-over-year");
  s.addChart(pres.ChartType.area, [{
    name: "Growth", labels: ["Q3 23", "Q4 23", "Q1 24", "Q2 24", "Q3 24", "Q4 24"], values: [10, 13, 14, 30, 23, 81],
  }], chartBase(T, {
    x: 0.1, y: 1.55, w: 9.8, h: 3.6,
    chartArea: { fill: { color: T.bg } }, plotArea: { fill: { color: T.bg } },
    chartColors: [T.s2], chartColorsOpacity: 45,
    lineSize: 0,
    valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 90,
    showValue: true, dataLabelPosition: "t", dataLabelFormatCode: '0" %"', dataLabelColor: T.muted,
  }));
  footnote(s, T);
});

// 5 · Net income of $343 million — column chart
SLIDES.push((pres, T) => {
  const s = pres.addSlide();
  s.background = { color: T.bg };
  label(s, T, "Net income");
  hero(s, T, "Net income\nof $343 million");
  s.addChart(pres.ChartType.bar, [{
    name: "Net income", labels: QUARTERS9, values: [115, 109, 184, 250, 274, 317, 301, 299, 343],
  }], chartBase(T, {
    x: 0.1, y: 1.35, w: 9.8, h: 3.8,
    chartArea: { fill: { color: T.bg } }, plotArea: { fill: { color: T.bg } },
    barDir: "col", barGapWidthPct: 60, chartColors: [T.s2],
    valAxisHidden: true,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '"$"0"M"',
  }));
  footnote(s, T);
});

// 6 · Revenue by User Geography — stacked column, 4 series
SLIDES.push((pres, T) => {
  const s = pres.addSlide();
  s.background = { color: T.bg };
  label(s, T, "Revenue");
  title(s, T, "Revenue by User Geography");
  const totals = [115, 109, 184, 250, 274, 317, 301, 299, 343];
  const split = [0.5, 0.25, 0.15, 0.1];
  const names = ["US & Canada", "Europe", "Asia-Pacific", "Rest of World"];
  const colors = [T.s1, T.s2, T.s3, T.s4];
  const data = names.map((n, i) => ({ name: n, labels: QUARTERS9, values: totals.map((t) => Math.round(t * split[i])) }));
  legend(s, T, names.map((n, i) => ({ text: n, color: colors[i] })), M, 0.9);
  s.addChart(pres.ChartType.bar, data, chartBase(T, {
    x: 0.1, y: 1.7, w: 9.8, h: 3.5,
    chartArea: { fill: { color: T.bg } }, plotArea: { fill: { color: T.bg } },
    barDir: "col", barGrouping: "stacked", barGapWidthPct: 60, chartColors: colors,
    valAxisHidden: true,
    showValue: true, dataLabelPosition: "ctr", dataLabelFormatCode: '"$"0"M"', dataLabelFontSize: 5,
    dataLabelColor: T.name === "dark" ? "FFFFFF" : "1C1C1E",
  }));
  // total labels above each stack
  const n = totals.length;
  const x0 = 0.55, span = 9.0;
  const maxV = 343;
  totals.forEach((t, i) => {
    const cx = x0 + (span / n) * (i + 0.5);
    const top = 1.7 + 0.12 + (3.5 - 0.5) * (1 - t / maxV) - 0.08;
    s.addText(`$${t}M`, {
      x: cx - 0.5, y: top - 0.2, w: 1, h: 0.2, align: "center",
      fontFace: FONT, fontSize: 7, color: T.title, bold: true, isTextBox: true, margin: 0,
    });
  });
  footnote(s, T);
});

// 7 · Expenses as a Percentage of Revenue — stacked column in a card
SLIDES.push((pres, T) => {
  const s = pres.addSlide();
  s.background = { color: T.bg };
  label(s, T, "Financials");
  title(s, T, "Expenses as a Percentage of Revenue");
  card(s, T, M, 0.95, W - 2 * M, 4.35);
  const names = ["General & Administrative", "Marketing & Sales", "Research & Development", "Cost of Revenue"];
  const colors = [T.s4, T.s3, T.s2, T.s1];
  const series = [
    [5, 6, 6, 6, 6, 8, 8, 10, 8],
    [10, 11, 11, 11, 11, 13, 13, 13, 12],
    [12, 13, 19, 20, 19, 20, 25, 24, 22],
    [15, 18, 20, 20, 23, 25, 25, 28, 35],
  ];
  legend(s, T, names.map((n, i) => ({ text: n, color: colors[i] })), M + 0.2, 1.1);
  s.addChart(pres.ChartType.bar, names.map((n, i) => ({ name: n, labels: QUARTERS9, values: series[i] })), chartBase(T, {
    x: M + 0.1, y: 1.1, w: W - 2 * M - 0.2, h: 4.1,
    barDir: "col", barGrouping: "stacked", barGapWidthPct: 45, chartColors: colors,
    valAxisHidden: true,
    showValue: true, dataLabelPosition: "ctr", dataLabelFormatCode: '0" %"', dataLabelFontSize: 5,
    dataLabelColor: T.name === "dark" ? "FFFFFF" : "1C1C1E",
  }));
});

// 8 · E-commerce / Total revenue — line chart + text
SLIDES.push((pres, T) => {
  const s = pres.addSlide();
  s.background = { color: T.bg };
  label(s, T, "Financials");
  title(s, T, "E-commerce", "Total revenue");
  body(s, T, [
    { text: "Over the past four years, our e-commerce segment has demonstrated strong and consistent growth. Starting from $0 million in Year 0, we have successfully scaled our operations, achieving $90 million in total revenue by Year 4. This growth trajectory highlights the effectiveness of our strategic initiatives, including market expansion, product diversification, and enhanced customer engagement.", options: { breakLine: true } },
    { text: "Our sustained upward trend, depicted by the solid black line, outpaces initial projections, indicating that our investments in technology and marketing have yielded substantial returns. As we continue to innovate and expand our e-commerce offerings, we are confident that this momentum will carry forward, driving even greater value for our stakeholders." },
  ], M, 2.75, 2.75, 2.6);
  card(s, T, 3.6, 0.25, 6.05, 5.1);
  s.addChart(pres.ChartType.line, [
    { name: "Projection", labels: ["Year 0", "Year 1", "Year 2", "Year 3", "Year 4"], values: [15, 20, 30, 45, 90] },
    { name: "Total revenue", labels: ["Year 0", "Year 1", "Year 2", "Year 3", "Year 4"], values: [0, 22, 45, 68, 90] },
  ], chartBase(T, {
    x: 3.7, y: 0.4, w: 5.85, h: 4.8,
    chartColors: [T.s3, T.name === "dark" ? "FFFFFF" : "000000"],
    lineSize: 1.25, lineDataSymbol: "none",
    valAxisMinVal: 0, valAxisMaxVal: 90, valAxisMajorUnit: 22.5, valAxisLabelFormatCode: '"$"0"M"',
    catAxisLineShow: false,
  }));
});

// 9 · Best-selling products / US — radar chart + text
SLIDES.push((pres, T) => {
  const s = pres.addSlide();
  s.background = { color: T.bg };
  label(s, T, "Products");
  title(s, T, "Best-selling products", "US");
  body(s, T, [
    { text: "The radar chart highlights the performance of our top eight products in the US, showcasing the comparative market position across key categories. Each product is evaluated on the same scale, providing a clear view of where we lead and where growth opportunities remain.", options: { breakLine: true } },
    { text: "Products 3 and 7 outperform their categories, reflecting strong customer demand and targeted marketing efforts. Product 5 and Product 8 show room for improvement, and we are refining positioning and pricing to lift their contribution next year." },
  ], M, 2.75, 2.75, 2.6);
  card(s, T, 3.6, 0.25, 6.05, 5.1);
  s.addChart(pres.ChartType.radar, [{
    name: "Sales", labels: ["Product 1", "Product 2", "Product 3", "Product 4", "Product 5", "Product 6", "Product 7", "Product 8"],
    values: [30, 45, 80, 55, 20, 40, 90, 25],
  }], chartBase(T, {
    x: 4.0, y: 0.45, w: 5.3, h: 4.7,
    radarStyle: "standard", chartColors: [T.s1], lineSize: 1,
    valAxisHidden: true, valGridLine: { color: T.grid, size: 0.5 }, catGridLine: { color: T.grid, size: 0.5 },
    catAxisLabelFontSize: 6.5,
  }));
});

// 10 · GAAP Operating Profitability — line chart with markers
SLIDES.push((pres, T) => {
  const s = pres.addSlide();
  s.background = { color: T.bg };
  label(s, T, "Financials");
  title(s, T, "GAAP Operating\nProfitability", null, { h: 0.95 });
  s.addText("We achieved GAAP operating profitability from operations of $620 million.", {
    x: M, y: 1.4, w: 2.9, h: 0.8, fontFace: FONT, fontSize: 10, color: T.muted, isTextBox: true, margin: 0, valign: "top",
  });
  card(s, T, 3.6, 0.25, 6.05, 5.1);
  s.addChart(pres.ChartType.line, [
    { name: "Plan", labels: ["Q 1", "Q 2", "Q 3", "Q 4"], values: [220, 330, 450, 640] },
    { name: "GAAP operating profit", labels: ["Q 1", "Q 2", "Q 3", "Q 4"], values: [240, 300, 400, 620] },
  ], chartBase(T, {
    x: 3.7, y: 0.4, w: 5.85, h: 4.8,
    chartColors: [T.faint, T.name === "dark" ? "FFFFFF" : "000000"],
    lineSize: 1, lineDataSymbol: "circle", lineDataSymbolSize: 6,
    lineDataSymbolLineColor: T.name === "dark" ? "FFFFFF" : "000000",
    valAxisMinVal: 0, valAxisMaxVal: 700, valAxisMajorUnit: 175, valAxisLabelFormatCode: '"$"0"M"',
    catAxisLineShow: false,
  }));
});

// 11 · Investments — table
SLIDES.push((pres, T) => {
  const s = pres.addSlide();
  s.background = { color: T.bg };
  label(s, T, "Financials");
  title(s, T, "Investments");
  card(s, T, M, 0.95, W - 2 * M, 4.35);
  const head = ["Symbol", "Name", "Price", "Price Change", "% Change", "Shares", "Price Paid", "Cost Basis", "Market Value", "Gain"];
  const rows = [
    ["AAPL", "Apple Inc.", "151,45 USD", "2,73 USD", "-1,77 %", "100", "1 023,32 USD", "123937,86 USD", "188 398,25 USD", "64346,55 USD"],
    ["FB", "Facebook, Inc.", "333,20 USD", "3,79 USD", "1,21 %", "50", "1 023,32 USD", "51840,20 USD", "120 391,15 USD", "68840,45 USD"],
    ["NKE", "Nike, Inc.", "132,51 USD", "-2,42 USD", "-1,80 %", "20", "510,60 USD", "13563,79 USD", "25 388,66 USD", "12564,88 USD"],
    ["BTC", "Bitcoin", "70123,91 USD", "20120 USD", "20 %", "–", "54123,91 USD", "58132,51 USD", "158 390,31 USD", "64349,4 USD"],
    ["ETH", "Ethereum", "3623,91 USD", "1023,82 USD", "11,4 %", "", "3023,91 USD", "3023,91 USD", "25 389,66 USD", "12564,88 USD"],
    ["Portfolio", "", "", "", "", "", "", "187672,53 USD", "334 758,12 USD", "146083,79 USD"],
  ];
  const cell = (t, o = {}) => ({ text: t, options: { fontFace: FONT, fontSize: 5.5, color: T.text, align: "center", valign: "middle", margin: 0.03, ...o } });
  const table = [
    head.map((h) => cell(h, { bold: true, color: T.title })),
    ...rows.map((r, ri) => r.map((c, ci) => cell(c, {
      bold: ci === 0 || ri === rows.length - 1,
      color: ci === 0 || ri === rows.length - 1 ? T.title : T.text,
      align: ci === 0 || ci === 1 ? "left" : "center",
      border: ri === 0 ? [{ type: "solid", pt: 0.75, color: T.faint }, { type: "none" }, { type: "none" }, { type: "none" }] : undefined,
    }))),
  ];
  s.addTable(table, {
    x: M + 0.15, y: 1.05, w: W - 2 * M - 0.3, colW: [0.75, 1.05, 0.85, 0.85, 0.75, 0.6, 0.95, 1.05, 1.15, 1.0],
    rowH: [0.45, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62],
    border: { type: "none" }, fill: { color: T.card },
  });
});

// 12 · Customer count — two mini bar cards
SLIDES.push((pres, T) => {
  const s = pres.addSlide();
  s.background = { color: T.bg };
  miniBarCard(pres, s, T, M, 0.25, 4.5, 5.1, "Customer count", "Commercial", QUARTERS4, [8, 12, 17, 16]);
  miniBarCard(pres, s, T, 5.15, 0.25, 4.5, 5.1, "Customer count", "Total", QUARTERS4, [10, 15, 20, 20], "+100% YoY");
});

// 13 · FY 2024 Highlights — bento grid
SLIDES.push((pres, T) => {
  const s = pres.addSlide();
  s.background = { color: T.bg };
  s.addText([
    { text: "FY 2024", options: { breakLine: true } },
    { text: "Highlights", options: { bold: true } },
  ], { x: M, y: 0.25, w: 3, h: 0.4, fontFace: FONT, fontSize: 8, color: T.title, isTextBox: true, margin: 0, valign: "top" });

  const quoteCard = (x, y, w, h, quote, src, big, color, textColor) => {
    card(s, T, x, y, w, h, color);
    s.addText(quote, {
      x: x + 0.15, y: y + 0.15, w: w - 0.3, h: h - 0.55,
      fontFace: FONT, fontSize: big ? 8.5 : 7.5, bold: big, color: textColor, isTextBox: true, margin: 0, valign: "top",
    });
    if (src) s.addText(src, { x: x + 0.15, y: y + h - 0.32, w: w - 0.3, h: 0.2, fontFace: FONT, fontSize: 5.5, color: textColor, isTextBox: true, margin: 0, valign: "bottom" });
  };
  const statCard = (x, y, w, h, stat, color, textColor, size, arrow) => {
    card(s, T, x, y, w, h, color);
    s.addText((arrow ? "▲ " : "") + stat, {
      x: x + 0.15, y: y + 0.1, w: w - 0.3, h: 0.7,
      fontFace: FONT, fontSize: size, bold: size > 12, color: textColor, isTextBox: true, margin: 0, valign: "top",
    });
  };
  const dark = T.name === "dark";
  const cA = dark ? "AEAEB2" : "C7C7CC"; // light card (accent)
  const cB = dark ? "3A3A3C" : "E5E5EA"; // mid card
  const tA = dark ? "FFFFFF" : "1C1C1E";
  const tB = dark ? "FFFFFF" : "1C1C1E";
  // column 1 (bottom half)
  quoteCard(M, 1.95, 3.0, 3.4,
    "\"Company X forges a resilient platform for complex, critical AI use cases, offering seamless integration and scalability. This platform empowers enterprises to leverage advanced AI technologies swiftly and efficiently, ensuring they remain at the forefront of innovation in their industry.\"",
    "– Source", true, cA, tA);
  // column 2
  quoteCard(3.5, 0.25, 3.0, 1.6, "\"A New Era in AI: Company X's Breakthroughs Redefine Enterprise Solutions\"", "– TechCrunch", true, cB, tB);
  statCard(3.5, 2.0, 3.0, 1.6, "+10 new stores", cB, tB, 15);
  quoteCard(3.5, 3.75, 3.0, 1.6, "\"Company X Revolutionises AI Integration, Setting New Industry Standards\"", "– Bloomberg", true, cB, tB);
  // column 3
  statCard(6.65, 0.25, 3.0, 3.35, "74M units sold", cA, tA, 9);
  statCard(6.65, 3.75, 3.0, 1.6, "14M\nSubscribers", cA, tA, 15, true);
  s.addNotes("Bento grid: swap quotes / stats freely; keep the two accent (light) cards diagonal for balance.");
});

// 14 · Total revenue of $12.4 billion — horizontal stacked bar
SLIDES.push((pres, T) => {
  const s = pres.addSlide();
  s.background = { color: T.bg };
  label(s, T, "Revenue");
  hero(s, T, "Total revenue\nof $12.4 billion");
  body(s, T, "Company X had a successful year in 2022, generating $12.4 billion in revenue, which is a significant increase from the previous year's earnings. The company's focus on innovation led to the development of innovative and high-quality products that met the needs and demands of its target audience.",
    6.4, 0.3, 3.25, 1.2, { fontSize: 6.5, color: T.title });
  legend(s, T, [{ text: "E-commerce", color: T.s3 }, { text: "Retail", color: T.s1 }], M, 3.7);
  s.addChart(pres.ChartType.bar, [
    { name: "E-commerce", labels: ["Revenue"], values: [2.4] },
    { name: "Retail", labels: ["Revenue"], values: [10.0] },
  ], chartBase(T, {
    x: M - 0.05, y: 4.05, w: W - 2 * M + 0.1, h: 1.05,
    chartArea: { fill: { color: T.bg } }, plotArea: { fill: { color: T.bg } },
    barDir: "bar", barGrouping: "percentStacked", barGapWidthPct: 5, chartColors: [T.s3, T.s1],
    valAxisHidden: true, catAxisHidden: true, catAxisLineShow: false,
  }));
  footnote(s, T);
});

// 15 · We closed 78 deals — dot grids
SLIDES.push((pres, T) => {
  const s = pres.addSlide();
  s.background = { color: T.bg };
  label(s, T, "Deals");
  hero(s, T, "We closed 78 deals\nworth at least $1 million");
  const grid = (x, y, w, h, head, rowsSpec) => {
    card(s, T, x, y, w, h);
    s.addText(head, { x: x + 0.2, y: y + 0.15, w: w - 0.4, h: 0.25, fontFace: FONT, fontSize: 8.5, color: T.title, isTextBox: true, margin: 0 });
    const d = 0.2, pitch = 0.43;
    const rows = rowsSpec.length;
    const y0 = y + h - 0.3 - rows * pitch + (pitch - d) / 2;
    rowsSpec.forEach((count, r) => {
      for (let c = 0; c < count; c++) {
        s.addShape("ellipse", {
          x: x + 0.25 + c * pitch, y: y0 + r * pitch, w: d, h: d,
          fill: { color: T.dot }, line: { color: T.dot, width: 0 },
        });
      }
    });
  };
  grid(M, 1.9, 4.5, 3.45, "$1 –  $10 million", [10, 10, 10, 10, 10]);
  grid(5.15, 1.9, 4.5, 3.45, "$10 –  $100 million", [8, 10, 10]);
});

// shared 9-quarter table (Segment Results / Additional Metrics)
function quarterTable(pres, s, T, rowsSpec) {
  const cell = (t, o = {}) => ({ text: t, options: { fontFace: FONT, fontSize: 5.5, color: T.text, align: "center", valign: "middle", margin: 0.03, ...o } });
  const alt = (i) => (i % 2 === 0 ? "3 622,91 €" : "20 120,00 €");
  const table = [[cell("", {}), ...QUARTERS9.map((q) => cell(q, { color: T.muted }))]];
  rowsSpec.forEach((r) => {
    const isTotal = r.total;
    const vals = r.values || QUARTERS9.map((_, i) => alt(i));
    table.push([
      cell(r.name, { align: "left", bold: true, color: isTotal ? T.tableTotalText : T.title, fill: isTotal ? { color: T.tableTotal } : undefined }),
      ...vals.map((v) => cell(v, { color: isTotal ? T.tableTotalText : T.text, bold: isTotal, fill: isTotal ? { color: T.tableTotal } : undefined })),
    ]);
  });
  const rowH = [0.4, ...rowsSpec.map(() => 0.4)];
  s.addTable(table, {
    x: M + 0.1, y: 1.05, w: W - 2 * M - 0.2, colW: [1.3, ...QUARTERS9.map(() => (W - 2 * M - 0.2 - 1.3) / 9)],
    rowH, border: { type: "solid", pt: 0.5, color: T.grid }, fill: { color: T.card },
  });
}

// 16 · Segment Results — table
SLIDES.push((pres, T) => {
  const s = pres.addSlide();
  s.background = { color: T.bg };
  label(s, T, "Financials");
  title(s, T, "Segment Results");
  card(s, T, M, 0.95, W - 2 * M, 4.35);
  quarterTable(pres, s, T, [
    { name: "Product 1" }, { name: "Product 2" }, { name: "Product 3" },
    { name: "Total", total: true, values: QUARTERS9.map((_, i) => (i % 2 === 0 ? "10 868,73 €" : "60 360,00 €")) },
    { name: "Product family", values: QUARTERS9.map(() => "3 622,91 €") },
    { name: "Product family", values: QUARTERS9.map(() => "3 622,91 €") },
    { name: "Product family", values: QUARTERS9.map(() => "3 622,91 €") },
    { name: "Total", total: true, values: QUARTERS9.map((_, i) => (i % 2 === 0 ? "21 737,46 €" : "71 228,73 €")) },
  ]);
});

// 17 · Adjusted Gross Margin — dotted line
SLIDES.push((pres, T) => {
  const s = pres.addSlide();
  s.background = { color: T.bg };
  label(s, T, "Financials");
  title(s, T, "Adjusted Gross Margin");
  card(s, T, M, 0.95, W - 2 * M, 4.35);
  s.addChart(pres.ChartType.line, [{
    name: "Adjusted gross margin", labels: ["Q3 23", "Q4 23", "Q1 24", "Q2 24", "Q3 24", "Q4 24"], values: [80, 80, 80, 82, 80, 81],
  }], chartBase(T, {
    x: M + 0.1, y: 1.1, w: W - 2 * M - 0.2, h: 4.1,
    chartColors: [T.s2], lineSize: 1.5, lineDash: "sysDot", lineDataSymbol: "none", lineSmooth: true,
    valAxisHidden: true, valAxisMinVal: 74, valAxisMaxVal: 88,
    showValue: true, dataLabelPosition: "t", dataLabelFormatCode: '0" %"',
  }));
});

// 18 · Retail Results — pie + text
SLIDES.push((pres, T) => {
  const s = pres.addSlide();
  s.background = { color: T.bg };
  label(s, T, "Financials");
  title(s, T, "Retail", "Results");
  body(s, T, [
    { text: "The chart illustrates the distribution of revenue among our top retail partners, highlighting the significant contribution from Retailer 4, which accounts for the majority share. This strong performance underscores the effectiveness of our strategic partnerships and the impact of our targeted retail strategies.", options: { breakLine: true } },
    { text: "Retailer 1, 2, and 3 also show substantial contributions, reflecting a well-balanced portfolio across our retail channels. This diversification ensures stability and resilience, allowing us to capitalize on various market opportunities while mitigating risks associated with reliance on a single partner.", options: { breakLine: true } },
    { text: "As we continue to strengthen our relationships with these key retailers, we anticipate further growth in each segment, driving overall revenue and expanding our market reach." },
  ], M, 2.55, 2.75, 2.8);
  card(s, T, 3.6, 0.25, 6.05, 5.1);
  s.addChart(pres.ChartType.pie, [{
    name: "Retail", labels: ["Retailer 1", "Retailer 2", "Retailer 3", "Retailer 4"], values: [10, 14, 16, 60],
  }], chartBase(T, {
    x: 4.2, y: 0.4, w: 4.85, h: 4.35,
    chartColors: [T.s4, T.s3, T.s2, T.s1],
    showLegend: true, legendPos: "b", legendColor: T.title, legendFontSize: 7, legendFontFace: FONT,
    showValue: false, showPercent: false, showLabel: false,
    firstSliceAng: 0,
  }));
});

// 19 · Total sales Q1 – Q4 — stacked column + text
SLIDES.push((pres, T) => {
  const s = pres.addSlide();
  s.background = { color: T.bg };
  label(s, T, "Financials");
  title(s, T, "Total sales", "Q1 – Q4");
  body(s, T, "The bar chart illustrates our total sales progression from Q1 to Q4 across two key segments. We see a steady increase in revenue, with Segment 1 and Segment 2 both contributing to this upward trend. By Q4, total sales reached $440M, driven by strong performance across both segments. This consistent growth reflects the success of our strategies and the robust demand in the market.",
    M, 4.2, 2.75, 1.15, { fontSize: 6.5, color: T.muted });
  card(s, T, 3.6, 0.25, 6.05, 5.1);
  legend(s, T, [{ text: "Segment 1", color: T.s1 }, { text: "Segment 2", color: T.s2 }], 3.85, 0.4);
  s.addChart(pres.ChartType.bar, [
    { name: "Segment 1", labels: QUARTERS4, values: [120, 130, 200, 220] },
    { name: "Segment 2", labels: QUARTERS4, values: [140, 150, 200, 220] },
  ], chartBase(T, {
    x: 3.7, y: 0.85, w: 5.85, h: 4.35,
    barDir: "col", barGrouping: "stacked", barGapWidthPct: 40, chartColors: [T.s1, T.s2],
    valAxisHidden: true,
    showValue: true, dataLabelPosition: "ctr", dataLabelFormatCode: '"$"0"M"', dataLabelColor: T.name === "dark" ? "FFFFFF" : "1C1C1E",
  }));
});

// 20 · Adjusted Free Cash Flow — two stacked columns in one card
SLIDES.push((pres, T) => {
  const s = pres.addSlide();
  s.background = { color: T.bg };
  label(s, T, "Financials");
  title(s, T, "Adjusted Free\nCash Flow", null, { h: 0.95 });
  s.addText("We closed Q1 2023 with $480 million in cash, cash equivalents, and U.S. Treasury securities, maintaining a debt-free position. As of March 31, 2023, we also had $150 million in undrawn credit facilities readily available.", {
    x: M, y: 1.4, w: 2.9, h: 1.6, fontFace: FONT, fontSize: 9.5, color: T.muted, isTextBox: true, margin: 0, valign: "top",
  });
  card(s, T, 3.6, 0.25, 6.05, 5.1);
  const half = (x, head, a, b) => {
    s.addText(head, { x: x + 0.15, y: 0.4, w: 2.7, h: 0.2, fontFace: FONT, fontSize: 6.5, color: T.muted, isTextBox: true, margin: 0 });
    s.addChart(pres.ChartType.bar, [
      { name: "Segment 1", labels: ["Q4 23", "Q4 24"], values: a },
      { name: "Segment 2", labels: ["Q4 23", "Q4 24"], values: b },
    ], chartBase(T, {
      x, y: 0.7, w: 2.95, h: 4.5,
      barDir: "col", barGrouping: "stacked", barGapWidthPct: 45, chartColors: [T.s1, T.s2],
      valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 34,
      showValue: true, dataLabelPosition: "ctr", dataLabelFormatCode: '"$"0"M"', dataLabelColor: T.name === "dark" ? "FFFFFF" : "1C1C1E",
    }));
  };
  half(3.65, "Cash from operations", [13, 14], [15, 16]);
  s.addShape("line", { x: 6.63, y: 0.45, w: 0, h: 4.7, line: { color: T.faint, width: 0.5, dashType: "sysDot" } });
  half(6.7, "Adjusted free cash flow", [12, 13], [14, 15]);
});

// 21 · US business performance — two mini bar cards
SLIDES.push((pres, T) => {
  const s = pres.addSlide();
  s.background = { color: T.bg };
  label(s, T, "Financials");
  title(s, T, "US business performance");
  miniBarCard(pres, s, T, M, 0.95, 4.5, 4.4, "US business performance", "Retail revenue growth", QUARTERS4, [8, 12, 17, 16]);
  miniBarCard(pres, s, T, 5.15, 0.95, 4.5, 4.4, "US business performance", "E-commerce revenue growth", QUARTERS4, [10, 15, 20, 20]);
});

// 22 · Appendix — section divider
SLIDES.push((pres, T) => {
  const s = pres.addSlide();
  s.background = { color: T.bg };
  s.addText("Appendix", {
    x: M, y: 0.3, w: 8, h: 0.8, fontFace: FONT, fontSize: 34, bold: true, color: T.title, isTextBox: true, margin: 0, valign: "top",
  });
});

// 23 · Additional Metrics and Notes — table with empty rows to fill
SLIDES.push((pres, T) => {
  const s = pres.addSlide();
  s.background = { color: T.bg };
  label(s, T, "Appendix");
  title(s, T, "Additional Metrics and Notes");
  card(s, T, M, 0.95, W - 2 * M, 4.35);
  quarterTable(pres, s, T, [
    { name: "Total RPO" }, { name: "Short-Term RPO" }, { name: "Long-Term RPO" }, { name: "Stock-Based Compensation" },
    { name: "", values: QUARTERS9.map(() => "") }, { name: "", values: QUARTERS9.map(() => "") },
    { name: "", values: QUARTERS9.map(() => "") }, { name: "", values: QUARTERS9.map(() => "") },
    { name: "", values: QUARTERS9.map(() => "") }, { name: "", values: QUARTERS9.map(() => "") },
  ]);
});

// ----------------------------------------------------------------- build ---
async function build(themeName, outDir) {
  const T = THEMES[themeName];
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.author = "namecode";
  pres.title = `Financial report template (${themeName})`;
  SLIDES.forEach((fn) => fn(pres, T));
  const out = path.join(outDir, `financial-report-${themeName}.pptx`);
  await pres.writeFile({ fileName: out });
  await repack(out); // pptxgenjs stores parts uncompressed; deflate them (≈6x smaller)
  console.log(`wrote ${out} (${SLIDES.length} slides)`);
}

async function repack(file) {
  const fs = require("fs");
  const JSZip = require("jszip");
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  const buf = await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE", compressionOptions: { level: 9 } });
  fs.writeFileSync(file, buf);
}

(async () => {
  const which = process.argv[2] ? [process.argv[2]] : Object.keys(THEMES);
  const outDir = process.argv[3] || __dirname;
  for (const t of which) await build(t, outDir);
})().catch((e) => { console.error(e); process.exit(1); });
