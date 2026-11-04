# Adaptive Execution Timing for Offline First Quorum Coordination in LoRa Mesh Networks

Supporting validation data and analysis scripts for the accompanying preprint.

Repository: https://github.com/f2ka07/adaptive-timing-data/

This archive contains the USB serial traces, processed tables, and scripts used to generate the figures and tables for the reported **2,514-round** post-tuning validation window.

## Contents

```
data/
  traces/                         USB serial logs (COM4/5/24/25)
  figures/                        Generated PDF figures
  out.csv                         Parsed per-event table
  out_normalized_per_node.csv     Per-node latency table used for plots
  summary_by_node_normalized.csv  Per-node summary statistics
  recreated_rounds_from_spakchain.csv
  consensus_analysis.py           Log parser (logs -> out.csv)
  make_results_figs_pdf.py        Figure generator (out.csv -> PDFs)
```

### Nodes and serial ports

| Node | Port  |
|------|-------|
| A3   | COM24 |
| A4   | COM4  |
| A5   | COM5  |
| A6   | COM25 |

## Requirements

- Python 3.9+
- Packages: `pandas`, `numpy`, `matplotlib`, `scipy` (optional, for some styling paths)

```bash
pip install pandas numpy matplotlib scipy
```

## Reproduce the figures

From the repository root:

```bash
cd data
python make_results_figs_pdf.py --in out.csv --outdir figures --ieee-style
```

Useful variants:

```bash
# Larger fonts / higher DPI for LaTeX
python make_results_figs_pdf.py --in out.csv --outdir figures --ieee-style --overleaf

# Colorblind-friendly palette
python make_results_figs_pdf.py --in out.csv --outdir figures --ieee-style --colorblind
```

Outputs written to `--outdir`:

- `cdf_latency_by_node.pdf`
- `box_latency_by_node.pdf`
- `hist_latency.pdf`
- `timeout_density.pdf`
- `wifi_vs_timeout_scatter.pdf`
- `heatmap_wifi_latency.pdf`
- `corr_matrix.pdf`
- `out_normalized_per_node.csv`
- `summary_by_node_normalized.csv`

## Re-parse raw logs (optional)

To rebuild `out.csv` from the USB traces:

```bash
cd data
python consensus_analysis.py --logs_dir traces --out_csv out.csv
```

Then regenerate figures with `make_results_figs_pdf.py` as above.

## `out.csv` schema (main fields)

| Column | Description |
|--------|-------------|
| `vote_id` | Coordination round identifier |
| `file` / `port` | Source log and COM port |
| `consensus_latency_ms` | Round completion latency (ms) |
| `bft_time_ms` | Quorum (3/4) threshold time (ms) |
| `finalized_4of4_ms` | Full-participation finalisation time (ms) |
| `timeout` | First-deadline miss flag (0/1) |
| `success` | Success flag (0/1) |
| `participants` | Participant list when logged |
| `wifi_events` | Gateway Wi-Fi/UDP event count in the log window |
| `death_fix_count` / `force_cleanup_count` | Recovery/cleanup counters |

## Citation

If you use this dataset, please cite the accompanying publication:

>  Kagai, F.; Branch, P.; But, J.; Allen, R. Adaptive Execution Timing for Offline First Quorum Coordination in LoRa Mesh Networks. Telecom 2026, 7, 123. https://doi.org/10.3390/telecom7050123

## License

Unless otherwise noted, data and scripts in this repository are provided for research reproducibility associated with the manuscript above.
