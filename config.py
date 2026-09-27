from pathlib import Path

# ============================================================
# Model Configurations
# ============================================================
SAFETY_MODEL = "KoalaAI/Text-Moderation"
CODER_MODEL = "Qwen/Qwen2.5-Coder-1.5B-Instruct"

# ============================================================
# Safety Decision Thresholds
# ============================================================
REVIEW_THRESHOLD = 0.40
BLOCK_THRESHOLD = 0.70
ZERO_TOLERANCE_THRESHOLD = 0.30

# Zero-tolerance category set (e.g., S3 = CSAM / Child Safety)
ZERO_TOLERANCE = {"S3"}

# ============================================================
# File & Directory Paths
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"
AUDIT_LOG_PATH = RESULTS_DIR / "safety_audit.jsonl"
ACCEPTANCE_REPORT_PATH = RESULTS_DIR / "acceptance_report.txt"

# ============================================================
# Benchmark & Evaluation URLs / Dataset Config
# ============================================================
PAIR_URL = (
    "https://raw.githubusercontent.com/"
    "JailbreakBench/artifacts/main/"
    "attack-artifacts/PAIR/black_box/"
    "vicuna-13b-v1.5.json"
)

JBB_DATASET_NAME = "JailbreakBench/JBB-Behaviors"
