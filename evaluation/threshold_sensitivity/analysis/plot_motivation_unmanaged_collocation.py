#!/usr/bin/env python3
from pathlib import Path
import matplotlib.pyplot as plt

jobs = [2, 3, 4]
throughput_gain = [1.25, 1.39, 1.40]
mean_slowdown = [1.60, 2.09, 2.44]
max_slowdown = [1.65, 2.15, 2.91]

out = Path("figures")
out.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.size": 9,
    "axes.labelsize": 9,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.fontsize": 7.8,
})

fig, ax = plt.subplots(figsize=(4.05, 1.85))

ax.plot(
    jobs,
    throughput_gain,
    marker="o",
    linestyle="-",
    linewidth=1.8,
    markersize=5.0,
    label="Throughput gain",
)
ax.plot(
    jobs,
    mean_slowdown,
    marker="^",
    linestyle="--",
    linewidth=1.8,
    markersize=5.0,
    label="Mean slowdown",
)
ax.plot(
    jobs,
    max_slowdown,
    marker="s",
    linestyle="-.",
    linewidth=1.8,
    markersize=4.8,
    label="Max slowdown",
)

for x, y in zip(jobs, throughput_gain):
    ax.annotate(
        f"{y:.2f}x",
        xy=(x, y),
        xytext=(0, 7),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=7.6,
    )

ax.set_xticks(jobs)
ax.set_xlabel("Colocated jobs")
ax.set_ylabel("Normalized factor")
ax.set_ylim(1.0, 3.1)
ax.grid(True, axis="y", linewidth=0.4, alpha=0.4)

ax.legend(
    frameon=False,
    loc="upper left",
    ncol=1,
    handlelength=2.2,
    borderaxespad=0.2,
    labelspacing=0.25,
)

fig.tight_layout(pad=0.15)

fig.savefig(out / "motivation_unmanaged_collocation.pdf", bbox_inches="tight")
fig.savefig(out / "motivation_unmanaged_collocation.png", dpi=300, bbox_inches="tight")
print(out / "motivation_unmanaged_collocation.pdf")
