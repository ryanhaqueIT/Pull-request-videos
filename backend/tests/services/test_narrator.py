"""Tests for the narration service."""

from hypothesis import given
from hypothesis import strategies as st

from services.narrator import generate_narration_script

SAMPLE_DIFF = """diff --git a/frontend/src/App.tsx b/frontend/src/App.tsx
index 1234567..abcdefg 100644
--- a/frontend/src/App.tsx
+++ b/frontend/src/App.tsx
@@ -10,3 +10,5 @@ function App() {
   return (
     <div className="app">
+      <h1>Hello World</h1>
+      <p>Welcome to the app</p>
     </div>
   );
"""


def test_generate_narration_from_diff() -> None:
    """Narration script is generated from a diff string."""
    script = generate_narration_script(SAMPLE_DIFF)
    assert len(script) > 0
    assert "1 files" in script or "1 file" in script or "App.tsx" in script


def test_generate_narration_empty_diff() -> None:
    """Empty diff produces a default narration."""
    script = generate_narration_script("")
    assert "walkthrough" in script.lower()


def test_generate_narration_counts_changes() -> None:
    """Narration mentions additions and deletions."""
    script = generate_narration_script(SAMPLE_DIFF)
    assert "adds" in script.lower() or "add" in script.lower()


@given(st.text(min_size=0, max_size=500))
def test_generate_narration_never_crashes(diff_text: str) -> None:
    """Property: generate_narration_script never raises for any input."""
    result = generate_narration_script(diff_text)
    assert isinstance(result, str)
    assert len(result) > 0
