#!/usr/bin/env python3
# make_results_figs_pdf.py
# Generate IEEE Transaction-quality publication figures from out.csv with professional styling.
#
# Usage:
#   python make_results_figs_pdf.py --in /path/to/out.csv --outdir /path/to/figs \
#       --figw 6.5 --figh 4.0 --labelsize 10 --ticksize 9 --titlesize 11 --legendsize 9 \
#       --linewidth 1.5 --markersize 4.0 --grid --transparent --pad 0.05 --ieee-style
#
# Features:
# - IEEE Transaction-quality color schemes with accessibility considerations
# - Professional typography and spacing
# - Publication-ready styling with consistent visual hierarchy
# - Colorblind-friendly palettes
# - Enhanced line styles and markers for clarity
# - Optimized layouts for academic publications
#
# Figures created:
#     1) cdf_latency_by_node.pdf
#     2) box_latency_by_node.pdf
#     3) hist_latency.pdf
#     4) timeout_density.pdf
#     5) wifi_vs_timeout_scatter.pdf
#     6) heatmap_wifi_latency.pdf
#     7) corr_matrix.pdf
# - Also writes normalized CSVs:
#     out_normalized_per_node.csv, summary_by_node_normalized.csv
#
import argparse, numpy as np, pandas as pd, matplotlib
import matplotlib.pyplot as plt
from pathlib import Path
from matplotlib.patches import Rectangle


# IEEE-compliant color palettes for accessibility
IEEE_COLORS = {
    "primary": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"],
    "colorblind": ["#0173b2", "#de8f05", "#029e73", "#d55e00", "#cc78bc", "#ca9161"],
    "grayscale": ["#000000", "#404040", "#808080", "#c0c0c0", "#606060", "#a0a0a0"],
}


def set_ieee_style(args):
    """Set IEEE Transaction-quality styling parameters"""

    # Overleaf optimization: increase font sizes and DPI for better quality
    if args.overleaf:
        font_scale = 1.5  # 50% larger fonts for Overleaf
        dpi = max(600, args.dpi)  # Use higher DPI for Overleaf, but respect user input
        linewidth_scale = 1.3  # Thicker lines
        markersize_scale = 1.4  # Larger markers
    else:
        font_scale = 1.0
        dpi = args.dpi
        linewidth_scale = 1.0
        markersize_scale = 1.0

    # Use Times New Roman for IEEE compliance
    matplotlib.rcParams.update(
        {
            # Typography
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "font.size": args.labelsize * font_scale,
            "axes.titlesize": args.titlesize * font_scale,
            "axes.labelsize": args.labelsize * font_scale,
            "xtick.labelsize": args.ticksize * font_scale,
            "ytick.labelsize": args.ticksize * font_scale,
            "legend.fontsize": args.legendsize * font_scale,
            # Line and marker styling
            "lines.linewidth": args.linewidth * linewidth_scale,
            "lines.markersize": args.markersize * markersize_scale,
            "lines.markeredgewidth": 0.5 * linewidth_scale,
            "lines.markeredgecolor": "white",
            # Axis styling
            "axes.linewidth": 0.8 * linewidth_scale,
            "axes.edgecolor": "black",
            "axes.grid": args.grid,
            "grid.linewidth": 0.5 * linewidth_scale,
            "grid.alpha": 0.3,
            "grid.linestyle": "--",
            # Tick styling
            "xtick.major.width": 0.8 * linewidth_scale,
            "xtick.minor.width": 0.4 * linewidth_scale,
            "ytick.major.width": 0.8 * linewidth_scale,
            "ytick.minor.width": 0.4 * linewidth_scale,
            "xtick.direction": "in",
            "ytick.direction": "in",
            # Legend styling
            "legend.frameon": True,
            "legend.fancybox": False,
            "legend.shadow": False,
            "legend.framealpha": 0.9,
            "legend.edgecolor": "black",
            "legend.facecolor": "white",
            # Figure styling
            "figure.constrained_layout.use": False,
            "savefig.dpi": dpi,
            "savefig.bbox": "tight",
            "savefig.pad_inches": args.pad,
            # Color cycle for better contrast
            "axes.prop_cycle": matplotlib.cycler(
                color=(
                    IEEE_COLORS["colorblind"]
                    if args.colorblind
                    else IEEE_COLORS["primary"]
                )
            ),
        }
    )


def set_style(args):
    if args.ieee_style:
        set_ieee_style(args)
    else:
        # Original styling for backward compatibility
        matplotlib.rcParams.update(
            {
                "font.size": args.labelsize,
                "axes.titlesize": args.titlesize,
                "axes.labelsize": args.labelsize,
                "xtick.labelsize": args.ticksize,
                "ytick.labelsize": args.ticksize,
                "legend.fontsize": args.legendsize,
                "lines.linewidth": args.linewidth,
                "lines.markersize": args.markersize,
                "figure.constrained_layout.use": False,
            }
        )


def new_fig(args, plot_type=None):
    """Create new figure with optimized dimensions for specific plot types"""
    # Apply column-width optimization if requested
    if args.column_width:
        # Standard single-column width for academic papers (typically 3.5-4 inches)
        fig_width = min(args.figw, 3.5)  # Cap at 3.5 inches for single column
        fig_height = args.figh
    elif plot_type in ["cdf", "box", "hist", "timeout"]:
        # Use more width for CDF, boxplot, histogram, and timeout density to better utilize space
        fig_width = args.figw * 1.2
        fig_height = args.figh
    else:
        fig_width = args.figw
        fig_height = args.figh

    return plt.figure(figsize=(fig_width, fig_height))


def wrap_title(title, max_length=25):
    """Wrap long titles to prevent overlap in narrow figures"""
    if len(title) <= max_length:
        return title
    
    words = title.split()
    lines = []
    current_line = ""
    
    for word in words:
        if len(current_line + " " + word) <= max_length:
            current_line += " " + word if current_line else word
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    return "\n".join(lines)


def save_fig(path, args):
    plt.savefig(
        path, bbox_inches="tight", pad_inches=args.pad, transparent=args.transparent
    )
    plt.close()


def ensure_round_idx(df: pd.DataFrame) -> pd.DataFrame:
    if "round_idx" not in df.columns or df["round_idx"].isna().all():
        if "vote_id" in df.columns:
            rid = df["vote_id"].astype(str).str.extract(r"_(\d+)_")[0]
            df["round_idx"] = pd.to_numeric(rid, errors="coerce")
        else:
            df["round_idx"] = np.nan
    return df


def normalize_by_participants(df: pd.DataFrame) -> pd.DataFrame:
    # latency from consensus or finalized_4of4 or bft
    lat = df.get("consensus_latency_ms")
    if "finalized_4of4_ms" in df:
        lat = lat.fillna(df["finalized_4of4_ms"])
    if "bft_time_ms" in df:
        lat = lat.fillna(df["bft_time_ms"])
    df["latency_ms"] = pd.to_numeric(lat, errors="coerce")

    # vote-level median latency (avoid per-file duplicates)
    vote_lat = (
        df.dropna(subset=["latency_ms"]).groupby("vote_id")["latency_ms"].median()
    )

    def split_parts(s):
        if pd.isna(s):
            return []
        return [p.strip() for p in str(s).split(",") if p.strip()]

    rows = []
    for _, r in df.iterrows():
        parts = split_parts(r.get("participants"))
        if not parts:
            parts = [r.get("node")]
        vlat = vote_lat.get(r.get("vote_id"), np.nan)
        for p in parts:
            rows.append(
                {
                    "vote_id": r.get("vote_id"),
                    "node": p,
                    "latency_ms": vlat,
                    "timeout": pd.to_numeric(r.get("timeout"), errors="coerce"),
                    "success": pd.to_numeric(r.get("success"), errors="coerce"),
                    "wifi_events": pd.to_numeric(r.get("wifi_events"), errors="coerce"),
                    "death_fix_count": pd.to_numeric(
                        r.get("death_fix_count"), errors="coerce"
                    ),
                    "force_cleanup_count": pd.to_numeric(
                        r.get("force_cleanup_count"), errors="coerce"
                    ),
                    "round_idx": r.get("round_idx"),
                    "file": r.get("file"),
                }
            )
    norm = (
        pd.DataFrame(rows)
        .dropna(subset=["node", "vote_id"])
        .drop_duplicates(subset=["vote_id", "node"])
    )
    return norm


def per_node_summary(norm: pd.DataFrame) -> pd.DataFrame:
    return (
        norm.groupby("node")
        .agg(
            samples=("vote_id", "count"),
            mean_latency_ms=("latency_ms", "mean"),
            var_latency_ms2=("latency_ms", "var"),
            timeout_ratio=(
                "timeout",
                lambda x: pd.to_numeric(x, errors="coerce").fillna(0).mean(),
            ),
            wifi_events_mean=("wifi_events", "mean"),
        )
        .reset_index()
    )


def plot_cdf(norm: pd.DataFrame, outpath: Path, args):
    fig = new_fig(args, plot_type="cdf")
    ax = fig.add_subplot(111)

    # IEEE-quality line styles and markers
    line_styles = ["-", "--", "-.", ":"]
    markers = ["o", "s", "^", "D", "v", "<"]
    colors = IEEE_COLORS["colorblind"] if args.colorblind else IEEE_COLORS["primary"]

    for i, (node, g) in enumerate(norm.groupby("node")):
        x = np.sort(g["latency_ms"].dropna().values.astype(float))
        if len(x) == 0:
            continue
        y = np.arange(1, len(x) + 1) / len(x)

        # Use different styles for each node
        line_style = line_styles[i % len(line_styles)]
        marker = markers[i % len(markers)]
        color = colors[i % len(colors)]

        ax.plot(
            x,
            y,
            label=node,
            linestyle=line_style,
            marker=marker,
            color=color,
            linewidth=args.linewidth,
            markersize=args.markersize,
            markevery=max(1, len(x) // 20),
            markeredgewidth=0.5,
            markeredgecolor="white",
        )

    ax.set_xlabel("Consensus Latency (ms)", fontweight="bold")
    ax.set_ylabel("Cumulative Distribution Function", fontweight="bold")
    
    # Use title wrapping for narrow figures
    title = "Latency CDF by Node"
    if args.column_width:
        title = wrap_title(title, max_length=20)
    ax.set_title(title, fontweight="bold", pad=20)

    # Enhanced legend with better positioning
    if args.legend:
        legend = ax.legend(
            loc=args.legend_loc,
            frameon=True,
            fancybox=False,
            shadow=False,
            framealpha=0.9,
            edgecolor="black",
        )
        legend.get_frame().set_facecolor("white")

    # Professional grid styling
    if args.grid:
        ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.3, color="gray")
        ax.set_axisbelow(True)

    # Set axis limits for better presentation - optimize space usage
    ax.set_ylim(0, 1.02)  # Reduce top margin slightly

    # Set fixed x-axis range to include all metrics (0 to 7000 ms)
    ax.set_xlim(0, 7000)

    # Add minor ticks for better readability
    ax.minorticks_on()

    # Ensure tight layout to minimize whitespace
    plt.tight_layout(pad=0.1)

    save_fig(outpath, args)


def plot_box(norm: pd.DataFrame, outpath: Path, args):
    fig = new_fig(args, plot_type="box")
    ax = fig.add_subplot(111)

    nodes = sorted(norm["node"].unique())
    data = [norm.loc[norm["node"] == n, "latency_ms"].dropna().values for n in nodes]
    colors = IEEE_COLORS["colorblind"] if args.colorblind else IEEE_COLORS["primary"]

    # Create boxplot with IEEE-quality styling
    bp = ax.boxplot(
        data,
        tick_labels=nodes,
        showfliers=False,
        patch_artist=True,
        boxprops=dict(linewidth=1.2, edgecolor="black"),
        whiskerprops=dict(linewidth=1.2, color="black"),
        capprops=dict(linewidth=1.2, color="black"),
        medianprops=dict(linewidth=2, color="red"),
    )

    # Color the boxes with professional colors
    for patch, color in zip(bp["boxes"], colors[: len(nodes)]):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax.set_xlabel("Node", fontweight="bold")
    ax.set_ylabel("Consensus Latency (ms)", fontweight="bold")
    
    # Use title wrapping for narrow figures
    title = "Latency Distribution per Node"
    if args.column_width:
        title = wrap_title(title, max_length=20)
    ax.set_title(title, fontweight="bold", pad=20)

    # Professional grid styling
    if args.grid:
        ax.grid(True, axis="y", linestyle="--", linewidth=0.5, alpha=0.3, color="gray")
        ax.set_axisbelow(True)

    # Set axis limits for better presentation - optimize space usage
    if len(data) > 0 and any(len(d) > 0 for d in data):
        # Calculate optimal y-axis limits based on visible boxplot elements
        # Since showfliers=False, we should focus on the main boxplot range

        # Get the whisker extents from the actual boxplot
        whisker_extents = []
        for d in data:
            if len(d) > 0:
                q1 = np.percentile(d, 25)
                q3 = np.percentile(d, 75)
                iqr = q3 - q1
                # Calculate whisker bounds (same as matplotlib boxplot)
                whisker_low = q1 - 1.5 * iqr
                whisker_high = q3 + 1.5 * iqr

                # Find actual data points within whisker bounds
                data_within_whiskers = d[(d >= whisker_low) & (d <= whisker_high)]
                if len(data_within_whiskers) > 0:
                    whisker_extents.extend(
                        [np.min(data_within_whiskers), np.max(data_within_whiskers)]
                    )

        if len(whisker_extents) > 0:
            y_min, y_max = np.min(whisker_extents), np.max(whisker_extents)
            y_range = y_max - y_min
            # Set y-axis with minimal margins
            ax.set_ylim(max(0, y_min - 0.02 * y_range), y_max + 0.02 * y_range)
        else:
            ax.set_ylim(bottom=0)
    else:
        ax.set_ylim(bottom=0)

    # Add minor ticks
    ax.minorticks_on()

    # Ensure tight layout to minimize whitespace
    plt.tight_layout(pad=0.1)

    save_fig(outpath, args)


def plot_hist(norm: pd.DataFrame, outpath: Path, args):
    fig = new_fig(args, plot_type="hist")
    ax = fig.add_subplot(111)

    vals = norm["latency_ms"].dropna().values.astype(float)
    color = (
        IEEE_COLORS["primary"][0]
        if not args.colorblind
        else IEEE_COLORS["colorblind"][0]
    )

    # Create histogram with IEEE-quality styling
    n, bins, patches = ax.hist(
        vals,
        bins=args.bins,
        edgecolor="black",
        linewidth=0.8,
        facecolor=color,
        alpha=0.7,
    )

    # Add subtle gradient to histogram bars
    for i, patch in enumerate(patches):
        patch.set_facecolor(color)
        patch.set_alpha(0.7 - 0.1 * (i % 2))  # Alternating opacity for subtle effect

    ax.set_xlabel("Consensus Latency (ms)", fontweight="bold")
    ax.set_ylabel("Frequency", fontweight="bold")
    
    # Use title wrapping for narrow figures
    title = "Histogram of Consensus Latency"
    if args.column_width:
        title = wrap_title(title, max_length=20)
    ax.set_title(title, fontweight="bold", pad=20)

    # Professional grid styling
    if args.grid:
        ax.grid(True, axis="y", linestyle="--", linewidth=0.5, alpha=0.3, color="gray")
        ax.set_axisbelow(True)

    # Set axis limits for better presentation - optimize space usage
    if len(vals) > 0:
        # Use percentiles to avoid extreme outliers affecting the axis range
        # Use 1st and 99th percentiles to focus on the main data distribution
        x_min = np.percentile(vals, 1)  # 1st percentile instead of min
        x_max = np.percentile(vals, 99)  # 99th percentile instead of max
        x_range = x_max - x_min

        # Only use full range if percentiles don't exclude much data
        full_range = np.max(vals) - np.min(vals)
        if x_range < 0.95 * full_range:  # If percentiles exclude >5% of range
            # Use percentiles with minimal margins
            ax.set_xlim(max(0, x_min - 0.02 * x_range), x_max + 0.02 * x_range)
        else:
            # Use full range with minimal margins
            ax.set_xlim(
                max(0, np.min(vals) - 0.02 * full_range),
                np.max(vals) + 0.02 * full_range,
            )

        # Set y-axis to start from 0 and go slightly above max bar height
        y_max = np.max(n)
        ax.set_ylim(0, y_max * 1.05)  # 5% margin above highest bar
    else:
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)

    # Add minor ticks
    ax.minorticks_on()

    # Ensure tight layout to minimize whitespace
    plt.tight_layout(pad=0.1)

    save_fig(outpath, args)


def plot_timeout_density(norm: pd.DataFrame, outpath: Path, args):
    fig = new_fig(args, plot_type="timeout")
    ax = fig.add_subplot(111)

    # IEEE-quality line styles and markers
    line_styles = ["-", "--", "-.", ":"]
    markers = ["o", "s", "^", "D", "v", "<"]
    colors = IEEE_COLORS["colorblind"] if args.colorblind else IEEE_COLORS["primary"]

    ok = False
    for i, (node, g) in enumerate(norm.groupby("node")):
        g = g.sort_values("round_idx")
        if "round_idx" not in g or g["round_idx"].isna().all():
            continue
        y = (
            pd.to_numeric(g["timeout"], errors="coerce")
            .fillna(0)
            .rolling(window=max(5, args.window), min_periods=3)
            .mean()
        )
        x = g["round_idx"]
        if len(x) > 0:
            line_style = line_styles[i % len(line_styles)]
            marker = markers[i % len(markers)]
            color = colors[i % len(colors)]

            ax.plot(
                x,
                y,
                label=node,
                linestyle=line_style,
                marker=marker,
                color=color,
                linewidth=args.linewidth,
                markersize=args.markersize,
                markevery=max(1, len(x) // 15),
                markeredgewidth=0.5,
                markeredgecolor="white",
            )
            ok = True

    ax.set_xlabel("Round Index", fontweight="bold")
    ax.set_ylabel(f"Timeout Density (Rolling Window: {args.window})", fontweight="bold")
    
    # Use title wrapping for narrow figures
    title = "Timeout Density Over Rounds"
    if args.column_width:
        title = wrap_title(title, max_length=20)
    ax.set_title(title, fontweight="bold", pad=20)

    if ok and args.legend:
        legend = ax.legend(
            loc=args.legend_loc,
            frameon=True,
            fancybox=False,
            shadow=False,
            framealpha=0.9,
            edgecolor="black",
        )
        legend.get_frame().set_facecolor("white")

    if args.grid:
        ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.3, color="gray")
        ax.set_axisbelow(True)

    # Set axis limits for better presentation - optimize space usage
    if ok:
        # Get all y values to optimize y-axis limits
        all_y_values = []
        for node, g in norm.groupby("node"):
            g = g.sort_values("round_idx")
            if "round_idx" not in g or g["round_idx"].isna().all():
                continue
            y = (
                pd.to_numeric(g["timeout"], errors="coerce")
                .fillna(0)
                .rolling(window=max(5, args.window), min_periods=3)
                .mean()
            )
            if len(y) > 0:
                all_y_values.extend(y.dropna().values)

        if len(all_y_values) > 0:
            y_min, y_max = np.min(all_y_values), np.max(all_y_values)
            y_range = y_max - y_min
            ax.set_ylim(max(0, y_min - 0.05 * y_range), y_max + 0.05 * y_range)
        else:
            ax.set_ylim(bottom=0)
    else:
        ax.set_ylim(bottom=0)

    # Add minor ticks
    ax.minorticks_on()

    # Ensure tight layout to minimize whitespace
    plt.tight_layout(pad=0.1)

    save_fig(outpath, args)


def plot_scatter(norm: pd.DataFrame, outpath: Path, args):
    fig = new_fig(args)
    ax = fig.add_subplot(111)

    # IEEE-quality markers and colors
    markers = ["o", "s", "^", "D", "v", "<"]
    colors = IEEE_COLORS["colorblind"] if args.colorblind else IEEE_COLORS["primary"]

    plotted = False
    for i, (node, g) in enumerate(norm.groupby("node")):
        if "file" in g.columns:
            pf = (
                g.groupby("file")
                .agg(
                    timeout_rate=("timeout", "mean"), wifi_events=("wifi_events", "max")
                )
                .dropna()
            )
            if len(pf):
                marker = markers[i % len(markers)]
                color = colors[i % len(colors)]

                ax.scatter(
                    pf["wifi_events"],
                    pf["timeout_rate"],
                    label=node,
                    marker=marker,
                    color=color,
                    s=args.markersize * 20,
                    edgecolors="black",
                    linewidth=0.5,
                    alpha=0.8,
                )
                plotted = True

    ax.set_xlabel("Wi-Fi Latency (per consensus round)", fontweight="bold")
    ax.set_ylabel("Timeout Rate (per consensus round)", fontweight="bold")
    ax.set_title("Wi-Fi Disturbance vs Timeout Rate", fontweight="bold", pad=20)

    if plotted and args.legend:
        legend = ax.legend(
            loc=args.legend_loc,
            frameon=True,
            fancybox=False,
            shadow=False,
            framealpha=0.9,
            edgecolor="black",
        )
        legend.get_frame().set_facecolor("white")

    if args.grid:
        ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.3, color="gray")
        ax.set_axisbelow(True)

    # Set axis limits for better presentation
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)

    # Add minor ticks
    ax.minorticks_on()

    save_fig(outpath, args)


def plot_heatmap(norm: pd.DataFrame, outpath: Path, args):
    fig = new_fig(args)
    ax = fig.add_subplot(111)

    if "file" in norm.columns:
        agg = (
            norm.groupby(["node", "file"])
            .agg(
                wifi_events=("wifi_events", "max"), latency_ms=("latency_ms", "median")
            )
            .dropna()
        )
    else:
        agg = norm.dropna(subset=["wifi_events", "latency_ms"])

    if len(agg) == 0:
        ax.text(
            0.5,
            0.5,
            "No data available",
            fontsize=args.titlesize,
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        save_fig(outpath, args)
        return

    wifi = agg["wifi_events"].values.astype(float)
    lat = agg["latency_ms"].values.astype(float)

    # Create bins with better resolution
    wb = np.linspace(np.nanmin(wifi), np.nanmax(wifi) + 1, 15)
    lb = np.linspace(np.nanmin(lat), np.nanmax(lat) + 1, 25)
    H, xedges, yedges = np.histogram2d(wifi, lat, bins=[wb, lb])

    # Use professional colormap
    cmap = plt.cm.viridis if not args.colorblind else plt.cm.plasma

    im = ax.imshow(
        H.T,
        origin="lower",
        aspect="auto",
        extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]],
        cmap=cmap,
        interpolation="nearest",
    )

    # Professional colorbar
    cb = fig.colorbar(im, ax=ax, shrink=0.8, aspect=20)
    cb.set_label("Count", fontweight="bold")
    cb.ax.tick_params(labelsize=args.ticksize)

    ax.set_xlabel("Wi-Fi Events (per file)", fontweight="bold")
    ax.set_ylabel("Latency (ms)", fontweight="bold")
    ax.set_title("Heatmap: Wi-Fi Events vs Latency", fontweight="bold", pad=20)

    # Add minor ticks
    ax.minorticks_on()

    save_fig(outpath, args)


def plot_corr(norm: pd.DataFrame, outpath: Path, args):
    fig = new_fig(args)
    ax = fig.add_subplot(111)

    cols = [
        c
        for c in [
            "latency_ms",
            "timeout",
            "wifi_events",
            "death_fix_count",
            "force_cleanup_count",
        ]
        if c in norm.columns
    ]

    # Clean column names for better display
    clean_cols = []
    for col in cols:
        if col == "latency_ms":
            clean_cols.append("Latency (ms)")
        elif col == "timeout":
            clean_cols.append("Timeout")
        elif col == "wifi_events":
            clean_cols.append("Wi-Fi Events")
        elif col == "death_fix_count":
            clean_cols.append("Recovery Count")
        elif col == "force_cleanup_count":
            clean_cols.append("Force Cleanup Count")
        else:
            clean_cols.append(col.replace("_", " ").title())

    cdf = norm[cols].copy().apply(pd.to_numeric, errors="coerce").dropna()

    if len(cdf) >= 3:
        C = np.corrcoef(cdf.values.T)

        # Use professional colormap for correlation matrix
        cmap = plt.cm.RdYlBu_r if not args.colorblind else plt.cm.RdBu_r

        im = ax.imshow(C, vmin=-1, vmax=1, cmap=cmap)

        # Professional colorbar
        cb = fig.colorbar(im, ax=ax, shrink=0.8, aspect=20)
        cb.set_label("Pearson Correlation Coefficient", fontweight="bold")
        cb.ax.tick_params(labelsize=args.ticksize)

        # Add correlation values as text
        for i in range(len(cols)):
            for j in range(len(cols)):
                text = ax.text(
                    j,
                    i,
                    f"{C[i, j]:.2f}",
                    ha="center",
                    va="center",
                    color="black" if abs(C[i, j]) < 0.5 else "white",
                    fontweight="bold",
                    fontsize=args.ticksize - 1,
                )

        ax.set_xticks(range(len(cols)))
        ax.set_yticks(range(len(cols)))
        ax.set_xticklabels(clean_cols, rotation=45, ha="right")
        ax.set_yticklabels(clean_cols)
        ax.set_title("Correlation Matrix", fontweight="bold", pad=20)

        # Add minor ticks
        ax.minorticks_on()

    else:
        ax.text(
            0.5,
            0.5,
            "Insufficient data for correlation analysis",
            fontsize=args.titlesize,
            ha="center",
            va="center",
            transform=ax.transAxes,
        )

    save_fig(outpath, args)


def main():
    ap = argparse.ArgumentParser(
        description="Generate IEEE Transaction-quality publication figures from consensus data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate IEEE-quality figures with default settings (14pt labels, 16pt titles)
  python make_results_figs_pdf.py --in out.csv --outdir figs --ieee-style
  
  # Optimized for Overleaf/LaTeX (50% larger fonts, 600 DPI)
  python make_results_figs_pdf.py --in out.csv --outdir figs --ieee-style --overleaf
  
  # Custom size and styling for journal submission
  python make_results_figs_pdf.py --in out.csv --outdir figs --ieee-style \\
    --figw 7.0 --figh 4.5 --labelsize 16 --titlesize 18 --colorblind
  
  # High-resolution figures for presentation
  python make_results_figs_pdf.py --in out.csv --outdir figs --ieee-style \\
    --figw 8.0 --figh 6.0 --linewidth 2.0 --markersize 5.0 --dpi 600
        """,
    )

    # Input/Output
    ap.add_argument(
        "--in", dest="incsv", required=True, help="Input CSV file with consensus data"
    )
    ap.add_argument(
        "--outdir",
        required=True,
        help="Output directory for figures and normalized CSVs",
    )

    # IEEE Quality Styling Options
    ap.add_argument(
        "--ieee-style",
        action="store_true",
        default=True,
        help="Enable IEEE Transaction-quality styling (default: True)",
    )
    ap.add_argument(
        "--colorblind",
        action="store_true",
        help="Use colorblind-friendly color palette",
    )
    ap.add_argument(
        "--grayscale",
        action="store_true",
        help="Use grayscale color palette for print compatibility",
    )
    ap.add_argument(
        "--overleaf",
        action="store_true",
        help="Optimize for Overleaf/LaTeX with larger fonts and higher DPI",
    )
    ap.add_argument(
        "--column-width",
        action="store_true",
        help="Optimize for single-column layout (narrower figures)",
    )

    # Figure Dimensions
    ap.add_argument(
        "--figw", type=float, default=6.5, help="Figure width in inches (default: 6.5)"
    )
    ap.add_argument(
        "--figh", type=float, default=4.0, help="Figure height in inches (default: 4.0)"
    )
    ap.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Output DPI (default: 300, use 600 for Overleaf)",
    )

    # Typography
    ap.add_argument(
        "--labelsize", type=float, default=14, help="Axis label font size (default: 14)"
    )
    ap.add_argument(
        "--ticksize", type=float, default=12, help="Tick label font size (default: 12)"
    )
    ap.add_argument(
        "--titlesize", type=float, default=16, help="Title font size (default: 16)"
    )
    ap.add_argument(
        "--legendsize", type=float, default=12, help="Legend font size (default: 12)"
    )

    # Visual Elements
    ap.add_argument(
        "--linewidth", type=float, default=1.5, help="Line width (default: 1.5)"
    )
    ap.add_argument(
        "--markersize", type=float, default=4.0, help="Marker size (default: 4.0)"
    )
    ap.add_argument(
        "--bins", type=int, default=30, help="Number of histogram bins (default: 30)"
    )

    # Layout and Presentation
    ap.add_argument(
        "--grid",
        action="store_true",
        default=True,
        help="Show grid lines (default: True)",
    )
    ap.add_argument(
        "--legend",
        action="store_true",
        default=True,
        help="Show legend (default: True)",
    )
    ap.add_argument(
        "--legend-loc",
        dest="legend_loc",
        default="best",
        choices=[
            "best",
            "upper right",
            "upper left",
            "lower left",
            "lower right",
            "right",
            "center left",
            "center right",
            "lower center",
            "upper center",
            "center",
        ],
        help="Legend location (default: best)",
    )
    ap.add_argument(
        "--transparent",
        action="store_true",
        help="Save figures with transparent background",
    )
    ap.add_argument(
        "--pad",
        type=float,
        default=0.05,
        help="Tight bbox padding in inches (default: 0.05)",
    )

    # Analysis Parameters
    ap.add_argument(
        "--window",
        type=int,
        default=20,
        help="Rolling window for timeout density (default: 20)",
    )

    args = ap.parse_args()

    # Apply color palette based on options
    if args.grayscale:
        IEEE_COLORS["primary"] = IEEE_COLORS["grayscale"]
        IEEE_COLORS["colorblind"] = IEEE_COLORS["grayscale"]

    set_style(args)

    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(args.incsv)

    # Map ports->nodes
    port_to_node = {"COM24": "A3", "COM4": "A4", "COM5": "A5", "COM25": "A6"}
    df["node"] = df["port"].map(port_to_node).fillna(df["port"])

    # Coerce numerics
    for c in [
        "success",
        "timeout",
        "consensus_latency_ms",
        "bft_time_ms",
        "wifi_events",
        "death_fix_count",
        "force_cleanup_count",
        "slot_interval_ms",
        "round_idx",
    ]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = ensure_round_idx(df)

    # Normalize
    norm = normalize_by_participants(df)
    norm = norm[norm["node"].isin(["A3", "A4", "A5", "A6"])]
    # Save normalized CSVs
    norm.to_csv(out_dir / "out_normalized_per_node.csv", index=False)
    summary = per_node_summary(norm)
    summary.to_csv(out_dir / "summary_by_node_normalized.csv", index=False)

    # Figures (PDF, cropped)
    plot_cdf(norm, out_dir / "cdf_latency_by_node.pdf", args)
    plot_box(norm, out_dir / "box_latency_by_node.pdf", args)
    plot_hist(norm, out_dir / "hist_latency.pdf", args)
    plot_timeout_density(norm, out_dir / "timeout_density.pdf", args)
    plot_scatter(norm, out_dir / "wifi_vs_timeout_scatter.pdf", args)
    plot_heatmap(norm, out_dir / "heatmap_wifi_latency.pdf", args)
    plot_corr(norm, out_dir / "corr_matrix.pdf", args)

    print(f"✓ IEEE-quality figures written to {out_dir}")
    print(f"✓ Generated {len([f for f in out_dir.glob('*.pdf')])} PDF figures:")
    for fig_file in sorted(out_dir.glob("*.pdf")):
        print(f"  - {fig_file.name}")
    print(f"✓ Generated normalized CSV files:")
    print(f"  - out_normalized_per_node.csv")
    print(f"  - summary_by_node_normalized.csv")

    # Show current settings
    dpi_used = 600 if args.overleaf else args.dpi
    actual_labelsize = args.labelsize * (1.5 if args.overleaf else 1.0)
    actual_titlesize = args.titlesize * (1.5 if args.overleaf else 1.0)
    print(f"\n📊 Current settings:")
    print(f"  - DPI: {dpi_used}")
    print(f"  - Figure size: {args.figw}×{args.figh} inches")
    print(
        f"  - Font sizes: {actual_labelsize:.1f}pt labels, {actual_titlesize:.1f}pt titles"
    )

    print("\n💡 Tips for further customization:")
    print("  - Use --overleaf for optimized Overleaf/LaTeX quality")
    print("  - Use --colorblind for accessible color schemes")
    print("  - Use --grayscale for print-friendly figures")
    print("  - Adjust --figw/--figh for different aspect ratios")
    print("  - Use --dpi 600 for higher resolution (recommended for Overleaf)")
    print("  - Use --linewidth/--markersize for presentation figures")
    if args.overleaf:
        print("  - Overleaf mode: 50% larger fonts, 600 DPI, thicker lines")
    else:
        print("  - Standard mode: 300 DPI, standard fonts")


if __name__ == "__main__":
    main()
