"""Creates harmless ORIGINAL sample notes. Never edits user documents."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "_DEMO_NOTES"
ROOT.mkdir(exist_ok=True)
examples = {
    "physics_notes.txt": """Physics — Basic Motion\n\nSpeed is distance traveled divided by elapsed time. Average speed = total distance / total time.\n\nVelocity differs from speed: velocity includes direction, while speed is a scalar.\n\nAcceleration is the rate at which velocity changes over time. SI unit: meters per second squared (m/s^2).\n\nNewton's first law: an object continues at rest or constant straight-line velocity unless acted on by a net external force.\n\nNewton's second law: net force equals mass multiplied by acceleration (F = m a).\n\nNewton's third law: for every action force there is an equal and opposite reaction force, acting on a different object.\n""",
    "biology_notes.txt": """Biology — Cells\n\nCells are the basic structural and functional units of living organisms.\n\nThe cell membrane helps regulate the movement of substances into and out of a cell.\n\nDNA carries hereditary information.\n\nMitochondria play a major role in ATP production through cellular respiration.\n\nPlant cells have a cell wall; animal cells lack a cell wall.\n\nPhotosynthesis converts light energy to chemical energy in plants and other photosynthetic organisms.\n""",
    "history_notes.md": """# History — Evidence and Sources\n\nPrimary sources are documents, objects or accounts created during the period being studied.\n\nSecondary sources analyze or interpret events using primary and other sources.\n\nHistorical interpretations may differ because sources are incomplete or evidence is assessed differently.\n\nAlways consider the source's origin, audience, purpose, and context.\n""",
}
for filename, text in examples.items():
    path = ROOT / filename
    if not path.exists():
        path.write_text(text, encoding="utf-8")
        print("Created", path)
    else:
        print("Already exists (not overwritten):", path)
print("Sample notes folder:", ROOT)
