# MDD

MDD is a Python project that pulls commit and issue data from GitHub, normalizes it, 
and emits clean CSVs for downstream modeling.

---

## Project Structure

- `MDD/` : Source folder containing `repo_miner.py`.
- `requirements.txt` : Project dependencies.
- `.github/workflows/ci.yml` : GitHub Actions CI workflow.
- `data/` : CSV output directory (created by the scripts).

---

## Getting Started

1. Install dependencies:
   ```bash
   pip install -r requirements.txt

## Usage

### Fetch Commits
python -m src.repo_miner fetch-commits --repo microsoft/vscode --max 50 --out data/commits.csv

### Fetch Issues
python -m src.repo_miner fetch-issues --repo microsoft/vscode --state all --max 50 --out data/issues.csv

### Summarize Data
python -m src.repo_miner summarize --commits data/commits.csv --issues data/issues.csv


## Sample Output

**Top 5 Committers:**

| Author | Commits |
|--------|---------|
| Alice  | 20      |
| Bob    | 15      |
| Carol  | 10      |

**Issue Summary:**

- Close rate: 0.75  
- Average open duration: 12.3 days
