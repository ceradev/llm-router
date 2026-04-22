from __future__ import annotations

from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.shortcuts import confirm, radiolist_dialog
from prompt_toolkit.validation import ValidationError, Validator

from packages.core.mock_router import Candidate


class _NonEmptyPromptValidator(Validator):
    def validate(self, document) -> None:  # type: ignore[override]
        if not document.text.strip():
            raise ValidationError(message="Prompt cannot be empty.", cursor_position=0)


def request_prompt_if_missing(prompt_value: str | None) -> str:
    if prompt_value and prompt_value.strip():
        return prompt_value.strip()
    return pt_prompt("Prompt > ", validator=_NonEmptyPromptValidator(), validate_while_typing=False).strip()


def choose_candidate_action(recommended: Candidate, alternatives: list[Candidate]) -> Candidate | None:
    values: list[tuple[str, str]] = [
        ("recommended", f"Accept recommendation ({recommended.name} | {recommended.provider})"),
    ]
    for idx, candidate in enumerate(alternatives, start=1):
        values.append((f"alt_{idx}", f"Use alternative {idx} ({candidate.name} | {candidate.provider})"))
    values.append(("cancel", "Cancel"))

    selected = radiolist_dialog(
        title="Routing Decision",
        text="Choose an action:",
        values=values,
    ).run()

    if selected is None or selected == "cancel":
        return None
    if selected == "recommended":
        return recommended

    selected_index = int(selected.split("_", maxsplit=1)[1]) - 1
    if 0 <= selected_index < len(alternatives):
        return alternatives[selected_index]
    return None


def confirm_execution(model_name: str, provider: str) -> bool:
    return confirm(f"Execute with {model_name} ({provider})?")
