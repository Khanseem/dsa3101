import dash
import dash_mantine_components as dmc
from dash import Input, Output, State, callback, dcc, html

from utils.classes import RubricSchemeData

dash.register_page(__name__, name="Add Rubric", path="/rubric")

layout = html.Div(
    [
        dmc.Title("Add Grading Scheme", order=1, style={"margin": "24px"}),
        dmc.Alert(
            "Sum of marks across questions do not add up to total marks. Please check marks allocation for each question.",
            id="rubric-error-alert",
            title="Grading incomplete!",
            color="red",
            duration=5000,
            hide=True,
            radius="md",
            style={"margin": "16px 16px 0px 16px"},
        ),
        dmc.Group(
            [
                html.Div(
                    [
                        dmc.NumberInput(
                            id="number-questions-input",
                            label="Number of questions",
                            value=1,
                            min=1,
                            size="lg",
                            step=1,
                            style={"margin-bottom": "16px", "width": 250},
                        ),
                        dmc.NumberInput(
                            id="overall-score-input",
                            label="Total score",
                            description="Total score for the assignment",
                            value=10,
                            min=1,
                            size="lg",
                            step=5,
                            style={"width": 250},
                        ),
                    ],
                    style={
                        "background-color": "rgba(230, 244, 255, 0.5)",
                        "border-radius": "10px",
                        "padding": "30px 0px 16px 24px",
                        "margin": "24px",
                        "height": "300px",
                        "width": "400px",
                    },
                ),
                dmc.Group(
                    [
                        html.Div(
                            [
                                dmc.Select(
                                    label="Question Number",
                                    id="question-select",
                                    value="1",
                                    data=[{"value": "1", "label": "1"}],
                                    maxDropdownHeight=200,
                                    size="lg",
                                    style={"margin-bottom": "16px", "width": 250},
                                ),
                                dmc.NumberInput(
                                    label="Question Score",
                                    description="Total marks for this question",
                                    id="question-score-input",
                                    value=1,
                                    min=1,
                                    size="lg",
                                    step=1,
                                    style={"width": 250},
                                ),
                            ],
                        ),
                        dmc.ScrollArea(
                            id="question-marks-allocation",
                            offsetScrollbars=True,
                            style={"height": "200px", "margin": "16px"},
                            scrollbarSize=8,
                            type="auto",
                        ),
                    ],
                    class_name="add-rubric-section",
                    style={
                        "background-color": "rgb(246, 246, 246)",
                        "border-radius": "10px",
                        "margin": "24px",
                        "padding": "16px 0px 16px 24px",
                        "height": "300px",
                        "width": "500px",
                    },
                ),
            ]
        ),
        html.Div(id="link-section"),
    ]
)


@callback(
    Output("rubric-error-alert", "hide"),
    Input("throw-error-btn", "n_clicks"),
    prevent_initial_call=True,
)
def check_rubric_data(n_clicks):
    """Callback to display alert banner.

    Triggers the alert banner when the 'Start grading' is clicked
    while the total marks allocation across all questions does not add up to
    the total score input.

    Args:
        n_clicks: Number of times this button has been clicked.

    Returns:
        hide: Boolean representing whether alert banner should be hidden.
    """

    if n_clicks:
        return False

    return dash.no_update


@callback(Output("link-section", "children"), Input("rubric-scheme-data", "data"))
def update_link_section(rubric_scheme_data: RubricSchemeData | None):
    """Auxiliary callback to update 'Start grading' button.

    We hot-swap the 'Start grading' button between two identical-looking ones.
    One triggers this callback, and the other that triggers
    `update_link_section` below. Both have different `id`s.

    We do this as some kind of a workaround to have the same Button (on the surface)
    perform two functionality depending on the state of the rubric scheme data.
    That is, we want the button to throw an error when the rubric scheme is
    invalid, and also to redirect the user to the homepage when it is valid.

    This is not really possible at the moment when wrapping `dcc.Link` around
    the Button component, since `dcc.Link` overrides any callback we may
    additionally attach to the Button component. So we use two different
    Buttons under-the-hood instead with the same UI appearance.

    Args:
        rubric_scheme_data: RubricSchemeData representing total marks for all
            questions and per-question marks.

    Returns:
        children: The Button component which either throws an alert or
            redirects users, depending on the rubric state.
    """

    if not rubric_scheme_data:
        return dash.no_update

    return (
        dcc.Link(
            dmc.Button(
                "Start grading",
                id="link-btn",
                color="green",
                style={"margin-left": "24px"},
            ),
            href="/",
        )
        if int(rubric_scheme_data["total"])
        == sum(rubric_scheme_data["questions"].values())
        else dmc.Button(
            "Start grading",
            id="throw-error-btn",
            color="green",
            style={"margin-left": "24px"},
        )
    )


@callback(
    Output("number-questions-input", "value"),
    Input("_pages_location", "pathname"),
    State("rubric-scheme-data", "data"),
)
def populate_number_of_questions_input(
    path, rubric_scheme_data: RubricSchemeData | None
):
    """Updates the number of questions input field.

    Checks the current rubric scheme to obtain the number of questions and
    populates the number of questions input with the total number.

    Note that this is mainly an auxiliary callback that re-populates the
    options in the input when switching between pages to reflect the previous
    input of the user. This will in turn chain the callback that updates the
    number of questions _dropdown_.

    Args:
        path: Pathname of the current page. Only included as a Input to trigger
            auto re-rendering of the dropdown when switching between pages.
        rubric_scheme_data: RubricSchemeData representing total marks for all
            questions and per-question marks.

    Returns:
        value: The number of questions to select through in the dropdown.
    """

    if path != dash.page_registry["pages.rubric"]["path"] or not rubric_scheme_data:
        return dash.no_update

    return len(rubric_scheme_data["questions"].keys())


@callback(
    Output("overall-score-input", "value"),
    Input("_pages_location", "pathname"),
    State("rubric-scheme-data", "data"),
)
def populate_total_score_input(path, rubric_scheme_data: RubricSchemeData | None):
    """Updates the total score input field.

    Checks the current rubric scheme to obtain the total score input and
    populates the total score input field with this number.

    Note that this is mainly an auxiliary callback that re-populates the
    options in the input when switching between pages to reflect the previous
    input of the user.

    Args:
        path: Pathname of the current page. Only included as a Input to trigger
            auto re-rendering of the dropdown when switching between pages.
        rubric_scheme_data: RubricSchemeData representing total marks for all
            questions and per-question marks.

    Returns:
        value: The number of questions to select through in the dropdown.
    """

    if path != dash.page_registry["pages.rubric"]["path"] or not rubric_scheme_data:
        return dash.no_update

    return rubric_scheme_data["total"]


@callback(
    Output("question-marks-allocation", "children"), Input("rubric-scheme-data", "data")
)
def update_marks_allocation(rubric_scheme_data: RubricSchemeData | None):
    """Updates the live marks allocation display output.

    Uses the data in the current rubric scheme and displays a text breakdown
    of the current marks allocation by marks.

    e.g.
        Question 1: 10
        Question 2: 10
        Total: 20

    Args:
        rubric_scheme_data: RubricSchemeData representing total marks for all
            questions and per-question marks.

    Returns:
        children: A dmc.Group component populated with dmc.Text components
            containing the breakdown per question and in total.
    """

    if not rubric_scheme_data:
        return dash.no_update

    return dmc.Group(
        [
            dmc.Text(
                f"Question {question_num}: {marks}",
                class_name="marks-allocation-txt",
            )
            for question_num, marks in rubric_scheme_data["questions"].items()
        ]
        + [
            dmc.Text(
                f"Total: {sum(int(i) for i in rubric_scheme_data['questions'].values())}",
                class_name="marks-allocation-txt",
            )
        ],
        direction="column",
        grow=True,
        spacing="sm",
    )


@callback(Output("question-select", "data"), Input("number-questions-input", "value"))
def update_selected_question(n_questions):
    """Updates the dropdown selecting the current question.

    Populates the options for the currently selected question dropdown according
    to the number input by the user in the 'Number of questions' input field.

    Args:
        n_questions: Number of questions. This is a value input by the user in
            the 'Number of questions' input field.

    Returns:
        data: List of dicts with a `value` and `label` key each for populating
            the current question dropdown.
    """

    if not n_questions:
        return dash.no_update

    return [{"value": str(i), "label": str(i)} for i in range(1, n_questions + 1)]


@callback(
    Output("question-score-input", "value"),
    Input("question-select", "value"),
    State("rubric-scheme-data", "data"),
)
def update_question_score(question_num, rubric_scheme_data: RubricSchemeData | None):
    """Updates the current score input based on the selected question.

    Populates the input field representing the score allocated to the
    currently selected question. If the question has not been selected before,
    this field is automatically populated with a score of `1`.

    Args:
        question_num: The currently selected question according to the
            dropdown.
        rubric_scheme_data: RubricSchemeData representing total marks for all
            questions and per-question marks.

    Returns:
        value: The score value to populate the current score input field with.
    """

    question_num = str(question_num)
    if not rubric_scheme_data or question_num not in rubric_scheme_data["questions"]:
        return 1

    return rubric_scheme_data["questions"][question_num]


@callback(
    [
        Output("rubric-scheme-data", "data"),
        Output("question-score-input", "error"),
    ],
    [
        Input("number-questions-input", "value"),
        Input("question-select", "value"),
        Input("question-score-input", "value"),
        Input("overall-score-input", "value"),
    ],
    State("rubric-scheme-data", "data"),
)
def update_rubric_scheme(
    n_questions,
    question_num,
    score,
    overall_score,
    rubric_scheme_data: RubricSchemeData | None,
):
    """Updates the rubric scheme data based on all the input/dropdown fields.

    Main callback that takes in all input changes across the question and score
    options and updates the rubric scheme data.

    Args:
        n_questions: Number of questions. This is a value input by the user in
            the 'Number of questions' input field.
        question_num: The currently selected question according to the
            dropdown.
        score: The value in the score field for the currently seelcted question.
        overall_score: The value in the total score field, representing the
            total marks for the entire grading scheme.
        rubric_scheme_data: RubricSchemeData representing total marks for all
            questions and per-question marks.

    Returns:
        data: New state of the current rubric scheme.
        error: An error string that represents an invalid score input when
            trying to update the question score. The rubric scheme will not
            be updated if an error is thrown here.
    """

    if not rubric_scheme_data:
        rubric_scheme_data = {}

    if not question_num and not score and not overall_score:
        return dash.no_update

    question_num = str(question_num)

    if overall_score:
        rubric_scheme_data["total"] = int(overall_score)

    if n_questions:
        questions = rubric_scheme_data.setdefault("questions", {})

        for i in range(1, n_questions + 1):
            i = str(i)
            if i not in questions:
                questions[i] = 1

        to_delete = [i for i in questions.keys() if int(i) > n_questions]
        for i in to_delete:
            del questions[i]

    if question_num and score:
        questions = rubric_scheme_data.setdefault("questions", {})
        total_marks = (
            sum(i for qns, i in questions.items() if qns != question_num) + score
        )

        if "total" in rubric_scheme_data and total_marks > rubric_scheme_data["total"]:
            return (
                dash.no_update,
                "Sum of question scores exceeds total assignment score",
            )

        questions[question_num] = score

    return rubric_scheme_data, ""
