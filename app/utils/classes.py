from dataclasses import dataclass
from typing import Dict, List, TypedDict

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class RubricItem:
    """A single rubric grading item.

    Attributes:
        marks: (Negative) integer number of marks deducted for this rubric item.
        description: Brief description of this rubric item.
        item_idx: Unique identifier for this item.
        file_idx: The index of the file this rubric item is associated with.
        question_num: The question number this rubric item is associated with.
    """

    marks: int
    description: str
    item_idx: int
    file_idx: int
    question_num: int


class RubricSchemeData(TypedDict):
    """Grading scheme for the current assignment, applied across all files.

    Attributes:
        total: Total number of marks for the entire assignment.
        questions: Mapping from question number to number of marks allocated
            for that question.
    """

    total: int
    questions: Dict[int, int]


class RubricEditData(TypedDict):
    """Set of edits to apply to existing rubric items.

    This is primarily populated and used when a user "finishes editing".
    It is used as a preliminary data structure to apply edits to the
    final state of `rubric-data` in the main data store.

    Note that "rubric item that was originally edited" refers to the rubric
    item which the user first clicked on the "edit button" in the application.

    Attributes:
        new: (Final) list of rubric items to modify. First entry in list
            should be the rubric item that was originally edited, remaining
            entries represent possibly matched rubric items which the user
            has opted to edit as well.
        original_marks: Marks of the rubric item that was originally edited.
            If None, means no matching rubric items found. Mainly used in
            the modal which displays possible rubric item edits, to remind the
            user what was the original value and what the user is trying to
            change that value to.
        matched_rubric_items: Intermediate list of rubric items that have
            the same marks and description as the rubric item that was
            originally edited. If None, means no rubric items with the same
            marks and description was found.
    """

    # Final rubric items to edit
    new: List[RubricItem]
    # Marks of the originally edited rubric item
    original_marks: int | None
    # Intermediate, matched rubric items
    matched_rubric_items: List[RubricItem] | None
