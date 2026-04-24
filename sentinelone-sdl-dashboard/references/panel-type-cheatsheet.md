# Panel Type Cheatsheet

| graphStyle | Panel | Query type | X axis | Notes |
|---|---|---|---|---|
| `line` | Line chart | filter+facet OR PowerQuery | time | Use `timebucket` + `transpose` for multi-series in PQ |
| `area` / `stacked` | Area chart | filter+facet OR PowerQuery | time | `stacked` = stacked area |
| `stacked_bar` / `bar` | Bar chart | PowerQuery | time OR grouped_data | Set `xAxis: "time"` or `xAxis: "grouped_data"` |
| `pie` | Pie chart | PowerQuery | — | Must return exactly 1 text + 1 numeric column |
| `donut` | Donut chart | PowerQuery | — | Same as pie; supports `dataLabelType: "PERCENTAGE"` |
| `table` | Table | PowerQuery | — | Default for PQ panels; add `showBarsColumn: "true"` for bar column |
| `number` | Gauge | PowerQuery | — | Single numeric value; supports `options.suffix`, `options.format` |
| `honeycomb` | Heatmap | PowerQuery | — | Needs text + numeric columns; use `columns` to alias names |
| `distribution` | Distribution | filter + facet field | value buckets | Uses `filter` + `facet` (not `query`); good for port/size distributions |
| `markdown` | Text | — | — | GitHub-flavored markdown; use `content` field |

## Key gotchas

- **Pie/Donut**: PowerQuery must return **exactly** one text column and one numeric column — nothing else. `| group count() by field` is the canonical pattern.
- **Number**: Reduce to a single row. `| group estimate_distinct(field)` or `| group count()` work. Adding `columns` to name the result cleanly is good practice.
- **Honeycomb**: Use `| columns LabelCol=text_field, ValueCol=numeric_field` to set the column names, then reference them in `honeyCombGroupBy` and thresholds.
- **Distribution**: Does NOT use `query` — use `filter` (search expression) and `facet` (the numeric field to distribute).
- **Breakdown graphs** (`breakdownFacet` property): Very slow, cannot be pre-cached. Use only for exploratory work, not production dashboards.
- **Time-series PQ charts**: Must use `timebucket()` in the `group by` clause. The timestamp column should be named `timestamp`. Use `transpose field on timestamp` for multi-series.
- **Stacked bar with time X-axis**: Set `xAxis: "time"` and `yScale: "linear"`.
- **Stacked bar with category X-axis**: Set `xAxis: "grouped_data"`.
- **Colors**: Use hex `"#FF0000"` in `color` (per-plot) or `valueColors` (for value-based coloring in S-25.3.6+).
- **Layout grid**: Total width = 60 units. Height: ~14 units ≈ half-page height. If you omit layout, the UI auto-positions.
