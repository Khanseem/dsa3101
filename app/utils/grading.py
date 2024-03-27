from utils.classes import RubricItem, RubricSchemeData


def marks_by_question(
    rubric_data,
    rubric_scheme_data: RubricSchemeData,
    student_num_file_map,
    student_num=None,
):
    """Collates the total marks obtained by every student per question.

    Args:
        rubric_data: RubricData containing mark deductions for each question
            for each file.
        rubric_scheme_data: RubricSchemeData representing total marks for all
            questions and per-question marks.
        student_num_file_map: A dict containing the mapping of file indexes to
            student numbers.
        student_num: Optional student number. Will only extract the marks for
            this student for every question if not None.

    Returns:
        marks_by_question: A Dict[int, List[int]] representing a mapping of
            question numbers to the list of total marks obtained for that
            question across every file.
    """

    marks_by_question = {}

    for file_idx, questions in rubric_data.items():
        if student_num and student_num_file_map[file_idx] != student_num:
            continue

        for question_num, total_marks in sorted(
            rubric_scheme_data["questions"].items(), key=lambda x: int(x[0])
        ):
            question = int(question_num)
            if question_num in questions:
                marks_deductions = sum(
                    int(RubricItem.from_dict(item).marks)
                    for item in questions[question_num]
                )
            else:
                marks_deductions = 0

            final_marks = total_marks + marks_deductions
            if question not in marks_by_question:
                marks_by_question[question] = [final_marks]
            else:
                marks_by_question[question].append(final_marks)

    return marks_by_question


def student_total_marks(
    rubric_data,
    rubric_scheme_data: RubricSchemeData,
    student_num_file_map=None,
    student_num=None,
):
    """Collates the total marks obtained by every student across all questions.

    Args:
        rubric_data: RubricData containing mark deductions for each question
            for each file.
        rubric_scheme_data: RubricSchemeData representing total marks for all
            questions and per-question marks.
        student_num_file_map: A dict containing the mapping of file indexes to
            student numbers.
        student_num: Optional student number. Will only extract the total marks
            for this student if not None.

    Returns:
        all_marks: A list containing the total marks obtained by students
            summed across all questions.
    """

    all_marks = []
    total_marks = rubric_scheme_data["total"]

    for file_idx, pages in rubric_data.items():
        if (
            student_num_file_map
            and student_num
            and student_num_file_map[file_idx] != student_num
        ):
            continue

        marks_deductions = sum(
            sum(int(RubricItem.from_dict(item).marks) for item in page)
            for page in pages.values()
        )
        final_marks = total_marks + marks_deductions

        all_marks.append(final_marks)

    return all_marks
