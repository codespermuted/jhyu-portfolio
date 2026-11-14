"""Reanalyse frozen CSVs and execute the repository's CPU Monte Carlo code.

No model fitting on real data, network access, or edits to the source checkout.
Usage: python build-evidence.py --repo ./source --out ./runs
Requires the public checkout at COMMIT and the pinned packages in requirements.txt.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import sys
import subprocess
import xml.etree.ElementTree as ET

COMMIT = "33420b5a57bf720c09485a8cd5ee521954dc07e5"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--repo", required=True, type=Path, help="Public repository checkout at the pinned commit")
parser.add_argument("--out", type=Path, default=Path("runs"), help="Generated logs, data and media (default: runs)")
args = parser.parse_args()
REPO = args.repo.resolve()
WORK = args.out.resolve()
if not (REPO / ".git").exists():
    parser.error("--repo must be a git checkout; follow README.md first")
actual_commit = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
if actual_commit != COMMIT:
    parser.error(f"Expected source commit {COMMIT}; found {actual_commit}")
if subprocess.run(["git", "-C", str(REPO), "diff", "--quiet", "HEAD"], check=False).returncode:
    parser.error("Source has tracked modifications; use a clean checkout of the pinned commit")
WORK.mkdir(parents=True, exist_ok=True)
MEDIA = WORK / "media"
MEDIA.mkdir(exist_ok=True)
(WORK / ".cache").mkdir(exist_ok=True)
os.environ.update({"OPENBLAS_NUM_THREADS":"1", "OMP_NUM_THREADS":"1", "VECLIB_MAXIMUM_THREADS":"1",
                   "MPLCONFIGDIR":str(WORK / ".matplotlib-cache"), "MPLBACKEND":"Agg",
                   "XDG_CACHE_HOME":str(WORK / ".cache"),
                   "PYTHONDONTWRITEBYTECODE":"1", "PYTEST_ADDOPTS":"-p no:cacheprovider",
                   "PYTEST_DISABLE_PLUGIN_AUTOLOAD":"1"})
sys.dont_write_bytecode = True
commands = [
    (["-m", "experiments.verify_paper_numbers"], "norm-boundary-frozen-verification.log"),
    (["-m", "experiments.g7_prop1_verify"], "norm-boundary-proposition-verification.log"),
    (["-m", "pytest", "tests/test_theory.py", "-q"], "norm-boundary-theory-tests.log"),
]
for command, filename in commands:
    run = subprocess.run([sys.executable, *command], cwd=REPO, text=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         timeout=300, check=False, env=os.environ.copy())
    (WORK / filename).write_text(run.stdout)
    print("python " + " ".join(command) + f" -> exit {run.returncode}", flush=True)
    if run.returncode:
        raise SystemExit(f"Verification failed; inspect {filename} in --out")
theory_count = re.search(r"\b(\d+) passed\b", (WORK / "norm-boundary-theory-tests.log").read_text())
if not theory_count or int(theory_count.group(1)) != 14:
    raise SystemExit("Expected 14 passing theory tests; inspect norm-boundary-theory-tests.log")
sys.path.insert(0, str(REPO))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from experiments.g11_table import boot
from experiments import g7_prop1_verify as prop

INK, MUTED, PAPER = "#26342d", "#596653", "#f4f3ed"
RUST, GREEN, LINE = "#af432b", "#35695c", "#d2d7cc"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 12,
    "axes.edgecolor": LINE, "axes.labelcolor": INK,
    "text.color": INK, "xtick.color": MUTED, "ytick.color": INK,
    "axes.facecolor": PAPER, "figure.facecolor": PAPER,
    "axes.spines.top": False, "axes.spines.right": False,
    "svg.fonttype": "path", "svg.hashsalt": "norm-boundary-verified",
})


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_figure(fig, stem: str, title: str, description: str, width: int, height: int):
    svg = MEDIA / f"{stem}.svg"
    fig.savefig(svg, format="svg", metadata={"Title": title, "Description": description, "Date": None})
    fig.savefig(WORK / f"{stem}.png", dpi=100)
    plt.close(fig)
    # Intrinsic dimensions and accessible text; all plotted glyphs are paths.
    content = svg.read_text()
    content = re.sub(r'(<svg\b[^>]*\bwidth=")[^"]+("[^>]*\bheight=")[^"]+',
                     rf'\g<1>{width}\g<2>{height}', content, count=1)
    content = content.replace('<svg ', '<svg role="img" aria-label="' + title + '" ', 1)
    svg.write_text(content)
    ET.parse(svg)
    return {"src": f"/media/{stem}.svg", "width": width, "height": height,
            "sha256": digest(svg), "bytes": svg.stat().st_size}


frozen = pd.read_csv(REPO / "results/g11_footing.csv")
frozen = frozen[frozen.backbone == "linmix"]
cells = frozen.groupby(["dataset", "h", "arm", "footing"]).mse.mean().unstack(["arm", "footing"])
order = [(d, h) for d in ("gefcom_wind", "gefcom_solar") for h in (24, 96, 336)]
assert set(cells.index) == set(order), "Unexpected cell scope; do not silently drop rows."
cells = cells.loc[order]
footings = ["global", "window_floor", "scale"]
labels = ["Global z-score", "Window z-score (SD floor 0.1)", "Target-scale matched"]
delta = {ft: cells[("revin", ft)] - cells[("raw", ft)] for ft in footings}
stats = {ft: [float(v) for v in boot(delta[ft].values)] for ft in footings}
source_rows = frozen[(frozen.arm.isin(["raw", "revin"])) & frozen.footing.isin(footings)]
counts = source_rows.groupby(["dataset", "h", "arm", "footing"]).size()
assert set(counts) == {5}, "Expected five frozen seeds per arm and cell."

fig = plt.figure(figsize=(12.8, 8.6))
fig.text(.06, .954, "The sign changes with the scaling convention.", fontsize=23, weight="bold")
fig.text(.06, .912, "Frozen-result reanalysis  /  linear mixer  /  6 wind and solar cells  /  5 seeds per arm", fontsize=12, color=MUTED)
ax = fig.add_axes([.34, .51, .60, .33])
for j, (ft, label) in enumerate(zip(footings, labels)):
    mean, lo, hi = stats[ft]
    y = 2 - j
    color = RUST if mean > 0 else GREEN
    ax.errorbar(mean, y, xerr=[[mean-lo], [hi-mean]], fmt="o", color=color,
                ms=9, capsize=5, elinewidth=2, capthick=1.5, zorder=3)
    ax.text(mean, y + .21, f"{mean:+.3f}", ha="center", fontsize=15, weight="bold", color=color)
ax.set_yticks([2,1,0], labels)
ax.tick_params(axis="y", length=0, pad=15)
ax.set_ylim(-.5, 2.65)
ax.set_xlim(-.145, .085)
ax.set_xticks([-.12,-.08,-.04,0,.04,.08])
ax.axvline(0, color=INK, lw=1, zorder=1)
ax.grid(axis="x", color=LINE, lw=.7, zorder=0)
ax.spines["left"].set_visible(False)
ax.set_xlabel("RevIN MSE − RAW MSE  ·  global-z units", labelpad=12)
ax.text(0, 1.01, "RevIN lower error", transform=ax.transAxes, color=GREEN, fontsize=11)
ax.text(1, 1.01, "RevIN higher error", transform=ax.transAxes, ha="right", color=RUST, fontsize=11)

table_ax = fig.add_axes([.06,.145,.88,.26])
table_ax.set_axis_off()
row_labels = [f"{'Wind' if d.endswith('wind') else 'Solar'} · h={h}" for d,h in order]
rows = [[name] + [f"{delta[ft].loc[key]:+.3f}" for ft in footings]
        for name,key in zip(row_labels,order)]
table = table_ax.table(cellText=rows,
    colLabels=["GEFCom cell", "Global z", "Window z (floored)", "Target-scale"],
    colWidths=[.31,.23,.23,.23], bbox=[0,0,1,1], cellLoc="center", colLoc="center")
table.auto_set_font_size(False)
table.set_fontsize(12)
for (row,col), cell in table.get_celld().items():
    cell.set_edgecolor(LINE)
    cell.set_linewidth(.7)
    cell.set_facecolor("#e1e6db" if row == 0 else PAPER)
    if row == 0: cell.set_text_props(weight="bold", color=INK)
    elif col > 0: cell.set_text_props(color=RUST if float(rows[row-1][col]) > 0 else GREEN)
    else: cell.set_text_props(ha="left", color=INK)
fig.text(.06,.093,"Points: equal-cell means. Intervals: 95% cell bootstrap, 100,000 resamples, seed 0.",fontsize=11,color=MUTED)
fig.text(.06,.065,"Recomputed from g11_footing.csv; no forecasting model was retrained. Six cells do not establish a universal effect.",fontsize=11,color=MUTED)
fig.text(.06,.034,f"codespermuted/norm-boundary-ccai · {COMMIT[:12]} · repository's original aggregation and bootstrap code",fontsize=10,color=MUTED)
footing_asset = save_figure(fig,"norm-boundary-footing-reproduction",
    "Normalization effect changes sign with covariate scaling",
    "Frozen-result reanalysis. Linear mixer, six GEFCom Wind/Solar cells, five seeds per arm. RevIN minus RAW MSE: global +0.026, floored window -0.075, target-scale -0.030. No real-data training was rerun.",1280,860)

# Run the upstream synthetic implementation, unchanged, with its original N and seed.
rng = np.random.default_rng(0)
simulation = []
for values in prop.GRID:
    a,b,k,rho,vy,vg,my,mg,dist = values
    mc = prop.excesses(rng,a,b,k,rho,vy,vg,my,mg,dist)
    cf = prop.closed_forms(a,b,k,rho,vy,vg,mg)
    passed = [abs(got-want) <= prop.RTOL * max(abs(want),1e-3) for got,want in zip(mc,cf)]
    simulation.append({"parameters": dict(zip(["a","b","kappa","rho","variance_ybar","variance_g","mean_ybar","mean_g","distribution"],values)),
                       "monte_carlo_excess_mse": list(map(float,mc)),
                       "gaussian_formula_excess_mse": list(map(float,cf)),
                       "within_original_tolerance": list(map(bool,passed))})
gauss = [r for r in simulation if r["parameters"]["distribution"] == "gauss"]
assert all(all(r["within_original_tolerance"]) for r in gauss)
gauss_row, heavy_row = simulation[0], simulation[-1]
relative = [abs(m-c)/abs(c) for r in gauss for m,c in zip(r["monte_carlo_excess_mse"],r["gaussian_formula_excess_mse"]) if abs(c)>1e-3]
max_relative = float(max(relative))

fig = plt.figure(figsize=(12.8,7.6))
fig.text(.06,.948,"Check the assumptions, not just the equation.",fontsize=23,weight="bold")
fig.text(.06,.899,"Fresh synthetic execution  /  2,000,000 draws per case  /  seed 0  /  CPU only",fontsize=12,color=MUTED)
ax = fig.add_axes([.09,.25,.48,.54])
x = np.arange(2)
theory = [gauss_row["gaussian_formula_excess_mse"][0],heavy_row["gaussian_formula_excess_mse"][0]]
observed = [gauss_row["monte_carlo_excess_mse"][0],heavy_row["monte_carlo_excess_mse"][0]]
ax.bar(x-.17,theory,width=.30,color="#8b9c84",label="Gaussian closed form")
ax.bar(x+.17,observed,width=.30,color=RUST,label="Monte Carlo")
for xx,v in zip(x-.17,theory):ax.text(xx,v+.08,f"{v:.3f}",ha="center",fontsize=13)
for xx,v in zip(x+.17,observed):ax.text(xx,v+.08,f"{v:.3f}",ha="center",fontsize=13,color=RUST)
ax.set_xticks(x,["Gaussian inputs", "Heavy-tailed inputs (t8)"])
ax.set_ylim(0,3.35)
ax.set_ylabel("Affine RAW excess MSE above noise floor",labelpad=10)
ax.grid(axis="y",color=LINE,lw=.7)
ax.set_axisbelow(True)
ax.legend(loc="upper left",frameon=False,fontsize=11)
ax.spines["left"].set_visible(False)
fig.text(.65,.76,"21 / 21",fontsize=38,weight="bold",color=GREEN)
fig.text(.65,.697,"Gaussian checks within tolerance",fontsize=13,weight="bold")
fig.text(.65,.655,"7 parameter cells × 3 formulas\nOriginal 2% scaled tolerance\nIncludes a near-zero absolute check",fontsize=12,color=MUTED,linespacing=1.7,va="top")
fig.text(.65,.49,f"{max_relative:.2%}",fontsize=30,weight="bold",color=GREEN)
fig.text(.65,.435,"Largest relative error",fontsize=13,weight="bold")
fig.text(.65,.393,"Across nonzero Gaussian predictions",fontsize=11,color=MUTED)
fig.text(.65,.315,"The t8 mismatch is expected.",fontsize=13,weight="bold",color=RUST)
fig.text(.65,.282,"Its heavier tails violate the\nGaussian fourth-moment identity.",fontsize=12,color=MUTED,linespacing=1.5,va="top")
fig.text(.06,.143,"Displayed pair: same first two moments; a=0.7, b=1.2, κ=0.5, ρ=0.4, Var(ȳ)=2, Var(g)=3.",fontsize=11,color=MUTED)
fig.text(.06,.101,"These are generated samples, not real forecasting benchmarks. Upstream theory suite: 14 tests passed.",fontsize=11,color=MUTED)
fig.text(.06,.059,f"Original CPU implementation: experiments/g7_prop1_verify.py · {COMMIT[:12]} · fresh execution for this portfolio audit",fontsize=10,color=MUTED)
theory_asset = save_figure(fig,"norm-boundary-theory-reproduction",
    "Synthetic Monte Carlo checks verify Gaussian formulas and expose assumption limits",
    "Fresh synthetic execution of the public repository code. Seven Gaussian cells, three formulas each, pass the original tolerance. The heavy-tailed input example intentionally violates the Gaussian interaction formula. Not a real-data forecasting benchmark.",1280,760)

verification_log = (WORK / "norm-boundary-frozen-verification.log").read_text()
verification_checks = []
for line in verification_log.splitlines():
    match = re.match(r"^(OK|XX)\s+(.+?)\s+paper\s+([+-]?[\d.]+)\s+data\s+([+-]?[\d.]+)$",line)
    if match:
        status,name,expected,actual = match.groups()
        verification_checks.append({"name":name,"passed":status=="OK","expected_printed":float(expected),"actual_printed":float(actual)})
assert len(verification_checks) == 82 and all(c["passed"] for c in verification_checks)

evidence = {
    "repository":"https://github.com/codespermuted/norm-boundary-ccai", "commit":COMMIT,
    "created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
    "publication_status":"README identifies an anonymous workshop submission; acceptance and individual authorship/contribution were not independently verified.",
    "license":"MIT; source copyright Anonymous Author(s), names withheld for double-blind review.",
    "runtime":{"python":platform.python_version(),"system":platform.platform(),
               "packages":{p:importlib.metadata.version(p) for p in ["numpy","pandas","matplotlib","pytest"]},
               "thread_environment":{"OPENBLAS_NUM_THREADS":"1","OMP_NUM_THREADS":"1","VECLIB_MAXIMUM_THREADS":"1"}},
    "executed_upstream_commands":[
        {"command":"python -m experiments.verify_paper_numbers","exit_code":0,"kind":"frozen-result arithmetic reanalysis","passed":82,"total":82,"log":"norm-boundary-frozen-verification.log","note":"README says 68; current script also checks deployment variants and returns 82."},
        {"command":"python -m experiments.g7_prop1_verify","exit_code":0,"kind":"fresh synthetic Monte Carlo","draws_per_case":2000000,"log":"norm-boundary-proposition-verification.log"},
        {"command":"python -m pytest tests/test_theory.py -q","exit_code":0,"kind":"upstream theory tests","passed":14,"log":"norm-boundary-theory-tests.log"}],
    "frozen_verification_checks":verification_checks,
    "footing_reanalysis":{"kind":"existing frozen experimental results, reaggregated now; no retraining","source":"results/g11_footing.csv","sha256":digest(REPO/"results/g11_footing.csv"),"backbone":"linmix","seeds_per_arm_cell":5,"cells":6,"metric":"RevIN minus RAW test MSE, global-z units","bootstrap":{"samples":100000,"seed":0,"method":"repository experiments.g11_table.boot; percentile 95% cell bootstrap"},"equal_cell_means_and_95pct_ci":{ft:{"mean":v[0],"lower":v[1],"upper":v[2]} for ft,v in stats.items()},"cell_differences":[{"dataset":d,"horizon":h,**{ft:float(delta[ft].loc[(d,h)]) for ft in footings}} for d,h in order]},
    "synthetic_reproduction":{"kind":"newly generated synthetic data, upstream code executed unchanged","n_per_cell":prop.N,"seed":0,"gaussian_checks_passed":21,"gaussian_checks_total":21,"tolerance":"abs(got-want) <= 0.02 * max(abs(want), 0.001)","max_relative_error_nonzero_gaussian":max_relative,"rows":simulation},
    "artifacts":[footing_asset,theory_asset],
    "limitations":["No raw KMA/GEFCom data were downloaded; they are not redistributed in the repository.","No forecasting grid or neural-network training was rerun; no Torch, model weights, paid API or GPU used.","Frozen-result arithmetic consistency does not validate the provenance or original execution of 4,202 logged runs.","Synthetic checks validate the stated stylized model under its assumptions, not real-world predictive performance.","Repository records incomplete preregistration timestamps, fixed-thread dropout reproducibility limits, and lead-matching defects in selected data cells.","Source is an anonymous submission; describe acceptance and the user's individual contribution only after confirmation."]
}
(WORK/"norm-boundary-evidence.json").write_text(json.dumps(evidence,indent=2,ensure_ascii=False)+"\n")
(WORK/"norm-boundary-footing-values.csv").write_text(pd.DataFrame(evidence["footing_reanalysis"]["cell_differences"]).to_csv(index=False))
print(json.dumps({"frozen_checks":82,"theory_tests":14,"gaussian_checks":21,"max_relative_error":max_relative,"footing":stats,"artifacts":evidence["artifacts"]},indent=2))
