"""The code representing the layout and callbacks for the `Stats` page.

The code of the layout for the `Stats` page is registered under Dash's
multi-page app feature. The functions here are mainly involved in performing
updating the contents of the statistics tables and graph(s). The styling options
for each of these components are all set here as well.
"""

import statistics
from collections import Counter

import dash
import dash_mantine_components as dmc
import plotly.express as px
from dash import Input, Output, State, callback, dash_table, dcc, html
from dash.dash_table.Format import Format, Scheme
from utils.classes import RubricItem, RubricSchemeData
from utils.grading import marks_by_question, student_total_marks

dash.register_page(__name__)

FILTERED_STATS_COLUMNS = ["Rubric", "Marks", "Proportion of students"]
QUESTION_COLUMNS = ["Question", "Total", "Lowest", "Mean", "Highest"]
OVERALL_COLUMNS = [
    "Lowest",
    "Median",
    "Mean",
    "Highest",
    "25th Percentile",
    "75th Percentile",
]


def default_table_style_options(n_columns: int) -> dict:
    """Default styling options for statistics tables.

    This represents a sensible set of defaults for styling a Dash DataTable
    that displays arbitrary data. In this module, this is mainly used for
    the tables that display the grading statistics.

    Args:
        n_columns: Number of columns in the table.

    Returns:
        A dict with keys corresponding to the possible styling options
        outlined at https://dash.plotly.com/datatable/style.
    """

    return {
        "css": [
            {
                "selector": "table",
                "rule": "table-layout: fixed",
            }
        ],
        "style_cell": {
            "width": f"{n_columns}%",
            "textOverflow": "ellipsis",
            "overflow": "hidden",
        },
        "style_header": {
            "backgroundColor": "white",
            "fontWeight": "bold",
        },
        "style_data_conditional": [
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "rgba(200, 200, 200, 0.5)",
            }
        ],
    }


def pct_data_bars(column: str) -> list:
    """Styling option to generate filled percentage bars.

    Uses the `linear-gradient` CSS function and sets it in Dash DataTable's
    styling options to fill the background of the table cell according to
    the value in that cell.

    Args:
        column: Name of the column in the table to render the percentage bars for.

    Returns:
        A list of dicts, with each dict representing a conditional styling
        of the `column` passed as an argument.
        See https://dash.plotly.com/datatable/style#conditional-formatting
        for more information.
    """

    n_bins = 100
    bounds = [i * (1.0 / n_bins) for i in range(n_bins + 1)]
    ranges = [i / 100 for i in range(n_bins + 1)]
    styles = []
    for i in range(1, len(bounds)):
        min_bound = ranges[i - 1]
        max_bound = ranges[i]
        max_bound_percentage = bounds[i] * 100
        styles.append(
            {
                "if": {
                    "filter_query": (
                        "{{{column}}} >= {min_bound}"
                        + (
                            " && {{{column}}} < {max_bound}"
                            if (i < len(bounds) - 1)
                            else ""
                        )
                    ).format(column=column, min_bound=min_bound, max_bound=max_bound),
                    "column_id": column,
                },
                "background": (
                    """
                    linear-gradient(90deg,
                    #0074D9 0%,
                    #0074D9 {max_bound_percentage}%,
                    white {max_bound_percentage}%,
                    white 100%)
                """.format(
                        max_bound_percentage=max_bound_percentage
                    )
                ),
                "paddingBottom": 2,
                "paddingTop": 2,
            }
        )

    return styles


def color_marks(column="Marks"):
    """Styling option to color marks by their values.

    Changes the text color of a `Marks`-related column to red if it is
    less than 0, green otherwise. Intended for use with Dash DataTable.

    Args:
        column: Name of the column containing marks-related data.

    Returns:
        A list of dicts, with each dict representing conditional styling
        of the `column` passed as an argument.
        See https://dash.plotly.com/datatable/style#conditional-formatting
        for more information.
    """

    return [
        {
            "if": {
                "filter_query": "{{{column}}} < 0".format(column=column),
                "column_id": column,
            },
            "color": "rgb(192, 33, 33)",
        },
        {
            "if": {
                "filter_query": "{{{column}}} >= 0".format(column=column),
                "column_id": column,
            },
            "color": "rgb(27, 127, 124)",
        },
    ]


def generate_statistics_table_children(id, title, columns, data=[]):
    """Helper function to generate a Dash DataTable with a title.

    Generates a Dash DataTable with a Title describing it.

    Args:
        id: String ID of the DataTable. Corresponds to the `id` HTML attribute
            used with Dash components.
        title: String to be passed to the Title component.
        columns: List of column names to be used as headers for the DataTable.
        data: List of Dict[string, string | number | boolean] representing the
            contents of the table.

    Returns:
        List of Dash components, one Title using Dash Mantime Components and
        the Dash DataTable.
    """

    return [
        dmc.Title(
            title,
            order=2,
            align="left",
            style={"margin-bottom": "10px"},
        ),
        dash_table.DataTable(
            data,
            id=id,
            columns=[{"name": i, "id": i} for i in columns],
            **default_table_style_options(len(columns)),
        ),
    ]


layout = html.Div(
    [
        dmc.Title("Statistics", order=1, style={"margin": "24px"}),
        dmc.Grid(
            [
                dmc.Col(
                    [
                        dmc.Group(
                            [
                                dmc.Title(
                                    "Score Distribution",
                                    order=2,
                                    align="left",
                                    style={
                                        "margin-bottom": "10px",
                                        "padding-left": "30px",
                                    },
                                ),
                                dmc.Select(
                                    label="Filter stats by question",
                                    id="filter-question-select",
                                    maxDropdownHeight=200,
                                    size="md",
                                    style={"margin-left": "16px", "width": 200},
                                ),
                            ]
                        ),
                        dcc.Graph(id="grades-histogram"),
                    ],
                    span=12,
                ),
                dmc.Col(
                    id="filtered-data-table",
                    span=12,
                    style={"margin-bottom": "24px", "padding": "0px 40px"},
                ),
                dmc.Col(
                    dmc.Group(
                        generate_statistics_table_children(
                            "question-data-table",
                            "Question Statistics",
                            QUESTION_COLUMNS,
                        ),
                        direction="column",
                    ),
                    span=6,
                    style={"padding": "0px 40px"},
                ),
                dmc.Col(
                    dmc.Group(
                        generate_statistics_table_children(
                            "overall-data-table",
                            "Overall Statistics",
                            OVERALL_COLUMNS,
                        ),
                        direction="column",
                    ),
                    span=6,
                    style={"padding": "0px 40px"},
                ),
            ],
            justify="center",
            style={"padding": "0px 40px"},
        ),
    ],
)


@callback(
    [
        Output("filter-question-select", "data"),
        Output("filter-question-select", "disabled"),
        Output("filter-question-select", "value"),
    ],
    Input("rubric-scheme-data", "data"),
)
def update_filter_options(rubric_scheme_data: RubricSchemeData | None):
    """Updates the question filter dropdown for the histogram Graph.

    Checks the current rubric scheme to obtain the number of questions and
    populates the filter dropdown with one option for each question.

    Args:
        rubric_scheme_data: RubricSchemeData representing total marks for all
            questions and per-question marks.

    Returns:
        data: List of dicts with a `value` and `label` key each for populating
            the filter dropdown.
        disabled: Boolean representing whether filter dropdown should be disabled.
        value: Current value of the filter dropdown.
    """

    if not rubric_scheme_data:
        return [], True, dash.no_update

    return (
        [
            {"value": "0", "label": "All"},
            *({"value": i, "label": i} for i in rubric_scheme_data["questions"].keys()),
        ],
        False,
        "0",
    )


@callback(
    Output("filtered-data-table", "children"),
    Input("filter-question-select", "value"),
    State("rubric-data", "data"),
)
def populate_filtered_table(question_num, rubric_data):
    """Updates the data in the question-breakdown statistics table.

    Reads the currently selected question in the filter dropdown
    and updates the DataTable that displays question breakdown data.
    e.g. total marks, list of mark deductions, percentage of students
    making mistakes.

    Args:
        question_num: Current value of the filter dropdown.
        rubric_data: RubricData containing mark deductions for each question
            for each file.

    Returns:
        children: A Dash DataTable with the rows populated according to the
            values in `rubric_data`, filtered by `question_num` across all
            files.
    """

    if question_num == "0" or not rubric_data:
        return []

    records = []
    all_correct = 0
    total_students = len(rubric_data.keys())
    rubric_marks = {}
    rubric_count = Counter()

    for questions_rubric in rubric_data.values():
        # No deductions
        if (
            question_num not in questions_rubric
            or len(questions_rubric[question_num]) == 0
        ):
            all_correct += 1
            continue

        rubric_items = (
            RubricItem.from_dict(item) for item in questions_rubric[question_num]
        )
        for item in rubric_items:
            if item.description not in rubric_marks:
                rubric_marks[item.description] = item.marks

            rubric_count[item.description] += 1

    records.append(
        {
            "Rubric": "Correct",
            "Marks": "0",
            "Proportion of students": all_correct / total_students,
        }
    )

    for rubric_desc in rubric_marks.keys():
        records.append(
            {
                "Rubric": rubric_desc,
                "Marks": rubric_marks[rubric_desc],
                "Proportion of students": rubric_count[rubric_desc] / total_students,
            }
        )

    style = default_table_style_options(3)
    style["style_data_conditional"] += [
        {"if": {"column_id": "Proportion of students"}, "fontWeight": "bold"},
        {"if": {"column_id": "Marks"}, "fontWeight": "bold"},
    ]
    style["style_data_conditional"] += pct_data_bars("Proportion of students")
    style["style_data_conditional"] += color_marks("Marks")
    style["style_cell_conditional"] = [
        {"if": {"column_id": "Rubric"}, "textAlign": "left"},
    ]

    return dash.dash_table.DataTable(
        records,
        id="filtered-table-output",
        columns=[
            {"name": "Rubric", "id": "Rubric"},
            {
                "name": "Marks",
                "id": "Marks",
                "type": "numeric",
                "format": Format(precision=2, scheme=Scheme.decimal_integer),
            },
            {
                "name": "Proportion of students",
                "id": "Proportion of students",
                "type": "numeric",
                "format": dash_table.FormatTemplate.percentage(1),
            },
        ],
        **style,
    )


@callback(
    Output("question-data-table", "data"),
    [
        Input("rubric-data", "data"),
        Input("rubric-scheme-data", "data"),
        Input("student-num-file-data", "data"),
        Input("_pages_location", "pathname"),
    ],
    # TODO: consider if we only want to include statistics for scripts
    # marked "completed"?
    # State("completed-data", "data"),
)
def update_question_statistics(
    rubric_data,
    rubric_scheme_data: RubricSchemeData | None,
    student_num_file_map,
    _path,
):
    """Updates the table which displays overall statistics per question.

    Checks the current rubric scheme and set of mark deductions to determine the
    total marks, lowest, highest and mean mark for each question.

    Args:
        rubric_data: RubricData containing mark deductions for each question
            for each file.
        rubric_scheme_data: RubricSchemeData representing total marks for all
            questions and per-question marks.
        student_num_file_map: A dict containing the mapping of file indexes to
            student numbers.
        _path: Pathname of the current page. Only included as a Input to trigger
            auto re-rendering of the DataTable when switching between pages.

    Returns:
        data: List of Dict[string, string | number | boolean] representing the
            contents of the table.
    """

    if not rubric_data or not student_num_file_map:
        return dash.no_update

    records = []
    # Populate question and total scores
    for question, mark in rubric_scheme_data["questions"].items():
        records.append({"Question": question, "Total": mark})

    questions_marks = marks_by_question(
        rubric_data, rubric_scheme_data, student_num_file_map
    )
    for question, marks in questions_marks.items():
        idx = int(question) - 1
        stats = {
            "Lowest": min(marks),
            "Mean": statistics.mean(marks),
            "Highest": max(marks),
        }

        records[idx] |= stats
    records.append({"Total": rubric_scheme_data["total"]})

    return records


@callback(
    Output("overall-data-table", "data"),
    [
        Input("rubric-data", "data"),
        Input("rubric-scheme-data", "data"),
        Input("_pages_location", "pathname"),
    ],
    # TODO: consider if we only want to include statistics for scripts
    # marked "completed"?
    # State("completed-data", "data"),
)
def update_overall_statistics(
    rubric_data,
    rubric_scheme_data: RubricSchemeData | None,
    _path,
):
    """Updates the table which displays overall statistics across all questions.

    Checks the current rubric scheme and mark deductions to compute the lowest,
    highest, median, mean mark for the whole assignment. Also computes the 25th
    and 75th quantile for the marks distribution across all files.

    Args:
        rubric_data: RubricData containing mark deductions for each question
            for each file.
        rubric_scheme_data: RubricSchemeData representing total marks for all
            questions and per-question marks.
        _path: Pathname of the current page. Only included as a Input to trigger
            auto re-rendering of the DataTable when switching between pages.

    Returns:
        data: List of Dict[string, string | number | boolean] representing the
            contents of the table.
    """

    if not rubric_data:
        return dash.no_update

    all_marks = student_total_marks(rubric_data, rubric_scheme_data)

    if len(all_marks) > 1:
        quantiles = statistics.quantiles(all_marks, method="inclusive")
        q25, q75 = (
            quantiles[0],
            quantiles[2],
        )
    else:
        q25, q75 = all_marks[0], all_marks[0]

    return [
        {
            "Lowest": min(all_marks),
            "Median": statistics.median(all_marks),
            "Mean": statistics.mean(all_marks),
            "Highest": max(all_marks),
            "25th Percentile": q25,
            "75th Percentile": q75,
        }
    ]


@callback(
    Output("grades-histogram", "figure"),
    [
        Input("rubric-data", "data"),
        Input("rubric-scheme-data", "data"),
        Input("student-num-file-data", "data"),
        Input("filter-question-select", "value"),
        Input("_pages_location", "pathname"),
    ],
)
def update_histogram(
    rubric_data,
    rubric_scheme_data: RubricSchemeData | None,
    student_num_file_map,
    filter_question_num,
    _path,
):
    """Updates the Graph histogram representing the distribution of total scores.

    Computes the total score for each file using the current rubric data and
    outputs them in the form of a histogram using Dash's dcc.Graph component.

    Args:
        rubric_data: RubricData containing mark deductions for each question
            for each file.
        rubric_scheme_data: RubricSchemeData representing total marks for all
            questions and per-question marks.
        student_num_file_map: A dict containing the mapping of file indexes to
            student numbers.
        filter_question_num: Current value of the question filter dropdown.
            Will selectively render question-specific total scores for the
            histogram if the value is anything other than `All`.
        _path: Pathname of the current page. Only included as a Input to trigger
            auto re-rendering of the DataTable when switching between pages.

    Returns:
        figure: plotly.graph_objects.Figure to update the main dcc.Graph with.
    """

    if not rubric_data or not student_num_file_map:
        return dash.no_update

    if filter_question_num and filter_question_num != "0":
        all_marks = marks_by_question(
            rubric_data, rubric_scheme_data, student_num_file_map
        )[int(filter_question_num)]
    else:
        all_marks = student_total_marks(rubric_data, rubric_scheme_data)
    fig = px.histogram(
        all_marks,
        opacity=0.8,
        # This cuts off last value
        # range_x=[0, max(all_marks)],
        labels={"value": "Marks"},
        text_auto=True,
        nbins=10,
    )
    fig.update_layout(
        {
            "xaxis": {"tickmode": "linear", "tick0": 0, "dtick": 1},
            "yaxis": {"tickmode": "linear", "tick0": 0, "dtick": 1},
        },
        bargap=0.2,
        showlegend=False,
    )

    return fig
