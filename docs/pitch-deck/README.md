# Dhrishti — MSME Idea Hackathon 6.0 pitch deck

`Dhrishti_MSME_Hackathon6_PitchDeck.pptx` — 16:9, 17 slides (12 main + 5 backup),
built from `MSME_Hackathon6_Idea4_PitchDeck_Content.md` (the `ON SLIDE` sections only).

## Deck map

| # | Slide | Notes |
|---|---|---|
| 1 | Title | Product name, subtitle, hackathon/theme tags |
| 2 | Problem & the gap | Split layout, comparison table, cost-gap bars |
| 3 | Our solution | Bullets + price card + 5-step training strip |
| 4 | How it works | **Empty placeholder for the block diagram image** |
| 5 | Innovation | Five numbered rows |
| 6 | Cost proof | BOM table, prototype-BOM row highlighted |
| 7 | Target market | Market table + Year 1/2/3 columns + impact |
| 8 | Business model | Revenue table + payback bars + unit economics |
| 9 | Current stage | Version B; two photo placeholders |
| 10 | 12-month plan | Four-block timeline, milestone + proof |
| 11 | Fund utilization | Donut chart (native) + table, ₹15,00,000 |
| 12 | Team | Two columns, photo placeholder circles |
| B1–B5 | Backup | Competitors, accuracy, risks, limits, cost evidence |

Speaker notes carry the `SAY` script and timing for each slide.

## To fill in before presenting

- Slide 4: paste the block diagram over the dashed placeholder.
- Slide 9: replace `[x]` values and drop in two photos.
- Slide 12: fill `[Degree, college]` and `[One line …]`.
- B5: paste the three supplier-listing screenshots.

## Rebuilding

```bash
npm install pptxgenjs
node build_deck.js
```

Design tokens live at the top of `build_deck.js`: navy `#1B2838`, teal `#00B4D8`,
red `#E63946` (slide 2 problem numbers only), Inter throughout.
