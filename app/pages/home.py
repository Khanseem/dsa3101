import base64
import itertools
import re
import tempfile
from datetime import datetime
from operator import attrgetter, itemgetter
from typing import Iterable

import dash
import dash_mantine_components as dmc
import plotly.express as px
from backend.api import gglapi_parse, num_highlighter
from dash import ALL, MATCH, Input, Output, State, callback, ctx, dcc, html
from dash_iconify import DashIconify
from pdf2image import convert_from_bytes, pdfinfo_from_bytes
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (ListFlowable, ListItem, Paragraph,
                                SimpleDocTemplate, Spacer)
from reportlab.platypus.doctemplate import inch
from reportlab.rl_config import defaultPageSize
from utils.classes import RubricEditData, RubricItem, RubricSchemeData
from utils.grading import marks_by_question

dash.register_page(__name__, path="/")

STUDENT_NUM_REGEX = ".*([a-zA-Z][0-9]{7}[a-zA-Z]).*"

GRADING_SUBMIT_MODAL_DEFAULT_CHILDREN = [
    dmc.Space(h=20),
    dmc.Group(
        children=[
            dmc.Button("Submit", id="grading-modal-submit-btn"),
            dmc.Button(
                "Close",
                color="red",
                variant="outline",
                id="grading-modal-close-btn",
            ),
        ],
        position="right",
    ),
]

RUBRIC_MATCH_MODAL_DEFAULT_CHILDREN = [
    dmc.Group(
        [
            dmc.Button(
                "Apply to all questions",
                color="blue",
                variant="outline",
                id="rubric-match-modal-all-qns-btn",
            ),
            dmc.Button(
                "Apply to current question only",
                color="blue",
                variant="outline",
                id="rubric-match-modal-current-qns-btn",
            ),
            dmc.Button(
                "Apply current edit only",
                color="blue",
                variant="filled",
                id="rubric-match-modal-current-btn",
            ),
        ],
        position="right",
    ),
]


layout = html.Div(
    children=[
        # Top bar alert banner
        dmc.Alert(
            id="top-alert",
            title="Error occurred!",
            color="red",
            duration=5000,
            hide=True,
            radius="md",
            style={"margin": "16px 16px 0px 16px"},
        ),
        # Top bar notification/hint banner
        dmc.Alert(
            "To get started, upload a script to grade and head to 'Add Rubric' to add a grading scheme!",
            id="top-hints",
            title="Getting Started",
            color="green",
            duration=8000,
            radius="md",
            style={"margin": "16px 16px 0px 16px"},
        ),
        dmc.Group(
            children=[
                # Button for uploading files
                dcc.Loading(
                    dcc.Upload(
                        className="upload-button",
                        id="upload-section",
                        children=dmc.Button(
                            "Drag and Drop or Click to select PDF",
                            style={"height": "60px", "margin-top": "31px"},
                        ),
                        style={
                            "lineHeight": "60px",
                            "borderWidth": "1px",
                            "textAlign": "center",
                            "margin": "10px",
                        },
                        multiple=True,
                    ),
                    fullscreen=True,
                ),
                # Student number input field
                dmc.TextInput(
                    id="student-number-input",
                    label="Student Number",
                    placeholder="e.g. A0000000X",
                    radius="md",
                    required=True,
                    size="xl",
                    style={
                        "margin": "16px",
                        "width": "300px",
                    },
                ),
                # Export grading button
                html.Div(
                    [
                        dmc.Button(
                            "Export grading to PDF",
                            id="export-grading-pdf-btn",
                            variant="light",
                            style={"height": "60px", "margin-top": "31px"},
                        ),
                        dcc.Download(id="grading-pdf-download"),
                    ]
                ),
            ],
        ),
        html.Hr(),
        dmc.Grid(
            children=[
                dmc.Col(
                    children=[
                        # Left file navigation bar
                        dmc.Navbar(
                            children=[
                                dmc.ScrollArea(
                                    id="files-scrollarea",
                                    offsetScrollbars=True,
                                    type="hover",
                                    scrollbarSize=10,
                                )
                            ],
                            id="files-navbar",
                            fixed=True,
                            height="100vh",
                            width={"base": 200},
                        )
                    ],
                    span=3,
                ),
                # COLUMN 2
                dmc.Col(
                    html.Div(
                        children=[
                            dmc.Group(
                                [
                                    # Main display metadata
                                    html.Div(
                                        [
                                            html.H2(id="annotate-name"),
                                            html.H2(id="annotate-datetime"),
                                        ],
                                    ),
                                    # Parser option
                                    dmc.LoadingOverlay(
                                        html.Div(
                                            dmc.Select(
                                                label="Type of parser",
                                                id="parser-select",
                                                disabled=True,
                                                value="0",
                                                data=[
                                                    {
                                                        "value": "0",
                                                        "label": "No parser",
                                                    },
                                                    {
                                                        "value": "1",
                                                        "label": "Google Parser",
                                                    },
                                                    {
                                                        "value": "2",
                                                        "label": "Google Parser with Solver",
                                                    },
                                                    {
                                                        "value": "3",
                                                        "label": "Number Highlighter",
                                                    },
                                                ],
                                                size="md",
                                                style={
                                                    "margin-left": "16px",
                                                    "width": 200,
                                                },
                                            ),
                                            id="loading-parser",
                                        ),
                                        loaderProps={
                                            "variant": "dots",
                                            "color": "blue",
                                            "size": "xl",
                                        },
                                    ),
                                ],
                            ),
                            # Main display for uploaded files, current page
                            dmc.LoadingOverlay(
                                dcc.Graph(
                                    id="annotate-active",
                                    config={
                                        "modeBarButtonsToAdd": [
                                            "drawopenpath",
                                            "drawrect",
                                            "eraseshape",
                                        ]
                                    },
                                    figure={
                                        "layout": {
                                            "template": None,
                                            "xaxis": {
                                                "showgrid": False,
                                                "showticklabels": False,
                                                "zeroline": False,
                                            },
                                            "yaxis": {
                                                "showgrid": False,
                                                "showticklabels": False,
                                                "zeroline": False,
                                            },
                                        }
                                    },
                                    style={"width": "100%", "height": "100%"},
                                ),
                                loaderProps={
                                    "variant": "dots",
                                    "color": "blue",
                                    "size": "xl",
                                },
                                style={"width": "100%", "height": "100%"},
                            ),
                            dmc.Col(
                                # Page navigation buttons for current file
                                dmc.Group(
                                    children=[
                                        dmc.Group(
                                            children=[
                                                dmc.Button(
                                                    "Previous",
                                                    id="prev-button",
                                                    variant="outline",
                                                ),
                                                dmc.Button("Next", id="next-button"),
                                            ]
                                        ),
                                        dmc.Button(
                                            "Submit final grading",
                                            id="submit-grading-btn",
                                            color="green",
                                        ),
                                    ],
                                    position="apart",
                                ),
                            ),
                        ],
                        id="annotate-section",
                        style={"width": "100%", "height": "150vh"},
                    ),
                    span=17,
                ),
                # Grading bar, wrapped in a navigation bar so it stays on user screen with scrolling
                dmc.Col(
                    dmc.Navbar(
                        id="grading-navbar",
                        children=dcc.Link(
                            dmc.Button(
                                "Add Rubric Scheme",
                                id="add-rubric-scheme-btn",
                                variant="light",
                                style={"width": 250},
                            ),
                            href="/rubric",  # href=dash.page_registry["pages.rubric"]["relative_path"]
                        ),
                        style={
                            "background-color": "rgb(246, 246 ,246)",
                            "border-radius": "10px",
                            "margin-right": "16px",
                            "padding": "16px 0px 0px 24px",
                        },
                        fixed=True,
                        position={"right": 0},
                        width={"base": 300},
                    ),
                    span=4,
                ),
            ],
            gutter="xl",
            justify="space-between",
            style={"width": "100%"},
            columns=24,
        ),
        # Modal for "Submit grading" button
        dmc.Modal(
            title="Confirm grading submission",
            id="grading-submit-modal",
            children=GRADING_SUBMIT_MODAL_DEFAULT_CHILDREN,
            centered=True,
            closeOnClickOutside=True,
            closeOnEscape=True,
        ),
        # Modal for applying matching rubric edits
        dmc.Modal(
            title="Matching rubric items found",
            id="rubric-match-modal",
            children=RUBRIC_MATCH_MODAL_DEFAULT_CHILDREN,
            centered=True,
            overflow="inside",
            padding="md",
            size="lg",
        ),
    ]
)


def annotate_figure_default_layout() -> dict:
    """Default plotly.graph_objects.Figure configuration options."""
    return {
        "dragmode": "drawrect",
        "hovermode": False,
        "newshape": {"line": {"color": "red"}},
        "xaxis": {"showticklabels": False},
        "yaxis": {"showticklabels": False},
    }


def rubric_item_component(marks, desc, item_idx, editable=True):
    """Helper method to create a rubric item component within the rubric display.

    Takes in both a mark and description and generates a set of pre-defined
    components representing a rubric item. At present, this contains text
    displays for the mark and description as well as a edit button and a
    delete button.

    Args:
        marks: Mark (deduction) for this rubric item.
        desc: Description for this rubric item.
        item_idx: A unique index to attach to this rubric item for
            modification purposes later on (e.g. when performing edits).
        editable: Boolean representing whether the user should be able to
            edit this rubric item. Generates edit and delete buttons if True,
            no buttons otherwise.

    Returns:
        html.Div with its children being the components described above.
    """

    return html.Div(
        children=[
            dmc.Group(
                children=[
                    dmc.Title(
                        # Always assume that each rubric item is a mark _deduction_
                        # The only non-negative mark is the default "0" rubric item
                        # generated for each question
                        "-" + str(marks) if int(marks) > 0 else str(marks),
                        order=3,
                        style={
                            "color": "rgb(192, 33, 33)"
                            if int(marks) != 0
                            else "rgb(27, 127, 124)"
                        },
                        id={"type": "rubric-marks", "index": item_idx},
                    ),
                    dmc.Group(
                        children=[
                            # Edit rubric item button
                            dmc.ActionIcon(
                                DashIconify(icon="bytesize:edit", width=20),
                                class_name="rubric-edit-button",
                                id={"type": "rubric-edit", "index": item_idx},
                                radius="sm",
                                variant="hover",
                            ),
                            # Delete rubric item button
                            dmc.ActionIcon(
                                DashIconify(
                                    icon="entypo:squared-cross",
                                    width=20,
                                ),
                                class_name="rubric-delete-button",
                                id={
                                    "type": "rubric-delete",
                                    "index": item_idx,
                                },
                                radius="sm",
                                variant="hover",
                            ),
                        ]
                        if editable
                        else [],
                        align="flex-end",
                        position="right",
                        spacing="xs",
                    ),
                ],
                position="apart",
            ),
            # Rubric description
            dmc.Text(
                desc,
                id={"type": "rubric-desc", "index": item_idx},
            ),
        ],
        id={"type": "rubric-item", "index": item_idx},
        style={"margin": "0px 8px 16px 8px"},
    )


def render_page_fig(pages, page_idx, parser):
    """Helper method to convert PDF bytes to image and optionally parse it.

    Converts PDF bytes to a PIL.Image and optionally parses it through
    parser APIs provided by the backend.

    Args:
        pages: Bytestring representing the contents of the PDF file.
        page_idx: 0-based page index representing which page of the PDF to
            render.
        parser: Currently selected parser option.

    Returns:
        plotly.graph_objects.Figure representing rendered PDF page contents.
    """

    img = convert_from_bytes(
        # Page indexes in PDF form start from 1
        pages,
        first_page=page_idx + 1,
        last_page=page_idx + 1,
    )[0]

    # Optionally pass image through parsing backend
    if int(parser) == 1:
        img = gglapi_parse(img, False)
    elif int(parser) == 2:
        img = gglapi_parse(img, True)
    elif int(parser) == 3:
        img = num_highlighter(img)

    # Construct new Figure object with this new image
    fig = px.imshow(img)
    fig.update_layout(annotate_figure_default_layout())

    return fig


def get_file_render_info(files, file_idx, page_idx=0, parser=0):
    """Helper method to obtain data involved in displaying a file.

    Retrieves the correct file from the uploaded file store along with its
    metadata, rendering it.

    Args:
        files: dict mapping file indexes to a base64-encoded bytestring of a
            uploaded PDF file.
        file_idx: 0-based file index representing which file to render.
        page_idx: 0-based page index representing which page of the PDF to
            render.
        parser: Currently selected parser option.

    Returns:
        name: Pre-formatted string indicating name of file.
        uploaded: Pre-formatted string indicating upload time of file.
        fig: plotly.graph_objects.Figure object representing rendered PDF page
        contents.
    """

    file_idx = str(file_idx)
    name, upload_datetime, contents = itemgetter("name", "date", "contents")(
        files[file_idx]
    )
    decoded = base64.b64decode(contents)
    fig = render_page_fig(decoded, page_idx, parser)

    return f"Name: {name}", f"Uploaded on {upload_datetime}", fig


def process_pdf_upload(file_contents, names, dates):
    """Processes metadata from uploaded files and stores them in a dict.

    Args:
        file_contents: List of base64-encoded bytestrings from uploaded files.
        names: List of strings representing the names of uploaded files.
        dates: List of UNIX timestamps representing time of uploads for
            uploaded files.

    Returns:
        uploaded: dict mapping file indexes to a base64-encoded bytestring of a
            uploaded PDF file.
    """

    uploaded = {}
    if file_contents and names and dates:
        for idx, (contents, name, date) in enumerate(zip(file_contents, names, dates)):
            idx = str(idx)
            _, content_string = contents.split(",")

            uploaded[idx] = {}
            uploaded[idx]["name"] = name
            uploaded[idx]["contents"] = content_string
            uploaded[idx]["date"] = datetime.fromtimestamp(date).strftime(
                "%Y-%m-%d %H:%I:%S"
            )

    return uploaded


def add_rubric_item(rubric_data, file_idx, question_num, item_idx, marks, description):
    """Updates the user-added rubric data store with a new RubricItem.

    Args:
        rubric_data: RubricData containing mark deductions for each question
            for each file.
        file_idx: 0-based file index representing currently rendered file.
        question_num: Question to add the rubric item for. Read from question
            select dropdown.
        item_idx: A unique index to attach to this rubric item for
            modification purposes later on (e.g. when performing edits).
        marks: Mark (deduction) for this rubric item.
        description: Description for this rubric item.

    Returns:
        rubric_data: The updated dict representing the user-added rubric data.
    """

    marks = -abs(int(marks.strip()))
    new_item = RubricItem(marks, description.strip(), item_idx, file_idx, question_num)

    # Note: dcc.Store data are JSON-serialized, and Python converts integer
    # keys to strings
    # To avoid surprises, just using string keys throughout
    file_idx = str(file_idx)
    question_num = str(question_num)
    if rubric_data:
        if file_idx in rubric_data:
            if question_num in rubric_data[file_idx]:
                rubric_data[file_idx][question_num].append(new_item)
            else:
                rubric_data[file_idx][question_num] = [new_item]
        else:
            rubric_data |= {file_idx: {question_num: [new_item]}}
    else:
        rubric_data = {file_idx: {question_num: [new_item]}}

    return rubric_data


def delete_rubric_item(rubric_data, file_idx, question_num, item_idx):
    """Updates the user-added rubric data store by deleting a RubricItem.

    Args:
        rubric_data: RubricData containing mark deductions for each question
            for each file.
        file_idx: 0-based file index representing currently rendered file.
        question_num: Question to delete the rubric item for from question
            select dropdown.
        item_idx: Unique index for the rubric item to be deleted.

    Returns:
        rubric_data: The updated dict representing the user-added rubric data.
    """

    # Note: dcc.Store data are JSON-serialized, and Python converts integer
    # keys to strings
    # To avoid surprises, just using string keys throughout
    file_idx = str(file_idx)
    question_num = str(question_num)
    rubric_data[file_idx][question_num] = [
        item
        for item in rubric_data[file_idx][question_num]
        if RubricItem.from_dict(item).item_idx != item_idx
    ]

    return rubric_data


def retrieve_file_student_num(student_num_file_map, file_idx):
    """Helper method to retrieve student number from file idx-student num map.

    Args:
        student_num_file_map: A dict containing the mapping of file indexes to
            student numbers.
        file_idx: 0-based file index representing currently rendered file.

    Returns:
        student_num: String of student number associated with current file.
    """

    # Note: dcc.Store data are JSON-serialized, and Python # converts integer
    # keys to strings
    # To avoid surprises, just using string keys throughout
    file_idx = str(file_idx)

    if not student_num_file_map or file_idx not in student_num_file_map:
        return ""

    return student_num_file_map[file_idx]


def mark_file_as_completed(completed_data, file_idx):
    """Helper method to add file index to store of files done marking.

    Args:
        completed_data: Set of IDs for files that have been marked as completed.
        file_idx: 0-based file index representing currently rendered file.

    Returns:
        completed_data: Updated set of IDs for files marked completed.
    """

    file_idx = str(file_idx)
    if completed_data:
        completed_data[file_idx] = 1
    else:
        completed_data = {file_idx: 1}

    return completed_data


def generate_rubric_match_modal_children(
    edit_data: RubricEditData, edit_student_num, edit_question_num, student_num_file_map
):
    """Helper method to generate the modal for applying edits to matched
    rubric items.

    Scans through the sequence of edits to be applied and generates the
    Components for them within the modal window.

    Args:
        edit_data: Intermediate data store containing the originally edited
            rubric item, as well as all found matching rubric items.
            Two rubric items are said to "match" if they have the same marks
            and description.
        edit_student_num: Currently populated student number.
        edit_question_num: Question number associated with the originally
            edited rubric item.
        student_num_file_map: A dict containing the mapping of file indexes to
            student numbers.

    Returns:
        List of Dash Components to populate the modal with.
    """

    rubric_desc = edit_data["new"][0]["description"]
    rubric_old_marks = edit_data["original_marks"]
    rubric_new_marks = edit_data["new"][0]["marks"]

    list_items = []
    for item in edit_data["matched_rubric_items"]:
        rubric_item = RubricItem.from_dict(item)
        student_num = student_num_file_map[str(rubric_item.file_idx)]
        question_num = rubric_item.question_num

        list_items.append((student_num, question_num))

    children = (
        [
            dmc.Text(
                "There are matching rubric items found in other scripts. Apply edits to them as well?"
            ),
            dmc.Space(h=20),
            # Original edited Rubric item is at the top and have changes bolded
            # for emphasis
            dcc.Markdown(
                f"""
                Changing rubric item **'{rubric_desc}'** marks from **{rubric_old_marks}** to **-{abs(int(rubric_new_marks))}**:
                - Student {edit_student_num}, Question {edit_question_num} **(current edit)**
                """,
                id="current-edit-md",
            ),
            # Generates a list item for every matching item
            dcc.Markdown(
                "\n".join(
                    f"- Student {student_num}, Question {question_num}"
                    for student_num, question_num in list_items
                ),
                style={"margin-top": "0px"},
            ),
            dmc.Space(h=10),
            dcc.Markdown(
                f"""
                Options:
                - **Apply to all questions**: This change will be applied across all scripts for matching criteria across all questions.
                - **Apply to current question only**: This change will be applied across all scripts, only for Question {edit_question_num}
                - **Apply current edit only**: This change will only be applied for the current script, only for Question {edit_question_num}
                """
            ),
            dmc.Space(h=20),
        ]
        + RUBRIC_MATCH_MODAL_DEFAULT_CHILDREN
    )

    return children


@callback(
    Output("parser-select", "disabled"),
    [Input("upload-store", "data"), Input("_pages_location", "pathname")],
)
def enable_parser_select(files, path):
    """Auxiliary callback to disable/enable parser select dropdown.

    If there are files uploaded, enable this dropdown. Otherwise, disable.

    Args:
        files: dict mapping file indexes to a base64-encoded bytestring of a
            uploaded PDF file.
        path: Pathname of the current page. Only included as a Input to trigger
            auto re-rendering when switching between pages.

    Returns:
        disabled: Boolean representing whether parser select dropdown should be
        enabled.
    """

    if path == dash.page_registry["pages.home"]["path"] and files:
        return False

    return dash.no_update


@callback(
    Output("upload-store", "data"),
    Input("upload-section", "contents"),
    [
        State("upload-section", "filename"),
        State("upload-section", "last_modified"),
    ],
    prevent_initial_call=True,
)
def upload_files(contents, names, dates):
    """Callback handling upload of files.

    Args:
        contents: List of base64-encoded bytestrings from uploaded files.
        names: List of strings representing the names of uploaded files.
        dates: List of UNIX timestamps representing time of uploads for
            uploaded files.

    Returns:
        files: dict mapping file indexes to a base64-encoded bytestring of a
            uploaded PDF file.
    """

    if contents and names and dates:
        return process_pdf_upload(contents, names, dates)

    return dash.no_update


@callback(
    [
        Output("annotate-name", "children"),
        Output("annotate-datetime", "children"),
        Output("annotate-active", "figure"),
        Output("loading-parser", "children"),
    ],
    [
        Input("upload-store", "data"),
        Input("page-index", "data"),
        Input("file-index", "data"),
        Input("parser-select", "value"),
    ],
    [
        State("upload-store", "data"),
        State("parser-select", "value"),
    ],
    prevent_initial_call=True,
)
def render_file(initial, page_idx, file_idx, parser_change, files, parser_current):
    """Callback that controls the rendering of the main display.

    Responds to changes in the data store containing upload files, or changes
    in the file and page indexes, which usually indicate that a new file
    or a new page needs to be rendered.

    Args:
        initial: dict mapping file indexes to a base64-encoded bytestring of a
            uploaded PDF file. (included as a subtlety with Dash callbacks.
            Mainly triggered only on initial file upload. Cannot use State since
            that would be None and not recorded as an input)
        page_idx: 0-based page index representing which page of the PDF to
            render.
        file_idx: 0-based file index representing which file to render.
        parser_change: Change in selected parser option. (Need to re-render
            current file and page using new parser).
        files: dict mapping file indexes to a base64-encoded bytestring of a
            uploaded PDF file. (included for when either the page or file index
            changes)
        parser_current: Currently selected parser option. (included for when
            either the page or file index changes)

    Returns:
        name_children: Children of title display for current file.
        datetime_children: Children of upload datetime display for current file.
        active_children: plotly.graph_objects.Figure for file to render.
        parser_children: Placeholder. Included as Output purely to trigger
            loading animation while new file/page is being rendered.
    """

    if ctx.triggered_id == "upload-store" and initial:
        # File gets uploaded initially -- render first of uploaded files
        return *get_file_render_info(initial, 0), dash.no_update
    elif ctx.triggered_id == "page-index" and page_idx is not None and files:
        # Page changes
        return (
            *get_file_render_info(files, file_idx, page_idx, parser=parser_current),
            dash.no_update,
        )
    elif ctx.triggered_id == "file-index" and file_idx is not None and files:
        # File changes
        return (
            *get_file_render_info(files, file_idx, parser=parser_current),
            dash.no_update,
        )
    elif ctx.triggered_id == "parser-select":
        return (
            *get_file_render_info(files, file_idx, page_idx or 0, parser_change),
            dash.no_update,
        )

    return dash.no_update


@callback(
    Output("page-index", "data"),
    [
        Input("prev-button", "n_clicks"),
        Input("next-button", "n_clicks"),
        Input("file-index", "data"),
    ],
    [
        State("page-index", "data"),
        State("file-index", "data"),
        State("upload-store", "data"),
    ],
    prevent_initial_call=True,
)
def change_page_index(
    _prev_btn_clicks,
    _next_btn_clicks,
    _file_idx_changed,
    current_page_idx,
    current_file_idx,
    files,
):
    """Changes current page index in data store on navigation button clicks or file change.

    Args:
        _prev_btn_clicks: Number of clicks of "Previous" page navigation button.
        _next_btn_clicks: Number of clicks of "Next" page navigation button.
        _file_idx_changed: New file index.
        current_page_idx: 0-based page index representing which page of the PDF to
            render.
        current_file_idx: 0-based file index representing which file to render.
        files: dict mapping file indexes to a base64-encoded bytestring of a
            uploaded PDF file.

    Returns:
        data: New page index to be stored in page-index data store.
    """

    # Initial load
    if current_page_idx is None:
        return 0

    # Change files -- reset to first page
    if ctx.triggered_id == "file-index":
        return 0

    if current_file_idx is None:
        return dash.no_update

    # TODO: this is super slow, shouldn't have to decode everytime?
    current_page_idx = int(current_page_idx)
    current_file_idx = str(current_file_idx)

    pages = base64.b64decode(files[current_file_idx]["contents"])
    max_pages = pdfinfo_from_bytes(pages)["Pages"]

    # Check if page index will be out of range with this button trigger
    # If so, no updates needed to be performed
    if (ctx.triggered_id == "prev-button" and current_page_idx - 1 < 0) or (
        ctx.triggered_id == "next-button" and current_page_idx + 1 >= max_pages
    ):
        return dash.no_update

    new_page_idx = (
        current_page_idx - 1
        if ctx.triggered_id == "prev-button"
        else current_page_idx + 1
    )

    return new_page_idx


@callback(
    Output("file-index", "data"),
    Input({"type": "file-link", "index": ALL}, "n_clicks"),
    State("upload-store", "data"),
    prevent_initial_call=True,
)
def change_file_index(_clicks, files):
    """Changes current file index on file change.

    Args:
        _clicks: Number of clicks for file link. (in left navigation bar)
        files: dict mapping file indexes to a base64-encoded bytestring of a
            uploaded PDF file.

    Returns:
        data: New file index to be stored in file-index data store.
    """

    if not ctx.triggered_id:
        return dash.no_update

    new_file_idx = str(ctx.triggered_id.index)

    if new_file_idx not in files:
        return dash.no_update

    return new_file_idx


@callback(
    Output("files-scrollarea", "children"),
    [
        Input("upload-store", "data"),
        Input("completed-data", "data"),
        Input("_pages_location", "pathname"),
    ],
)
def update_navbar(files, completed_data, path):
    """Updates file navigation bar on file upload or file mark completed.

    Args:
        files: dict mapping file indexes to a base64-encoded bytestring of a
            uploaded PDF file.
        completed_data: Set of IDs for files that have been marked as completed.
        path: Pathname of the current page. Only included as a Input to trigger
            auto re-rendering when switching between pages.

    Returns:
        children: Dash Components (one for each file) containing links to
            change between uploaded files and (optionally) a completed icon
            for files marked completed.
    """

    if path != dash.page_registry["pages.home"]["path"]:
        return dash.no_update

    if not files:
        return dash.no_update

    file_links = []
    for idx, file in enumerate(files.values()):
        link = html.A(
            file["name"],
            className="navbar-link",
            id={"type": "file-link", "index": idx},
            style={"color": "blue"},
        )

        if completed_data and str(idx) in completed_data:
            link = dmc.Group(
                children=[
                    link,
                    dmc.ThemeIcon(
                        DashIconify(icon="ic:round-check-box", width=16),
                        color="green",
                        variant="filled",
                        class_name="completed-btn",
                        size=20,
                    ),
                ],
                position="apart",
            )

        file_links.append(link)

    children = [
        dmc.Group(
            children=file_links,
            grow=True,
            position="left",
            spacing="sm",
            direction="column",
            style={
                "margin-bottom": 20,
                "margin-top": 20,
                "padding-left": 30,
                "padding-right": 20,
            },
        )
    ]

    return children


@callback(
    Output("grading-navbar", "children"),
    [
        Input("rubric-scheme-data", "data"),
        Input("_pages_location", "pathname"),
    ],
)
def populate_grading_navbar(rubric_scheme_data: RubricSchemeData | None, path):
    """Generates question select dropdown and score display for grading section.

    Reads the previously user-defined grading scheme and populates the grading
    section with appropriate dropdowns and input fields for the user to start
    grading.

    This replaces the "Add Rubric Scheme" button which is populated by default
    when the user accesses the application for the first time.

    Args:
        rubric_scheme_data: RubricSchemeData representing total marks for all
            questions and per-question marks.
        path: Pathname of the current page. Only included as a Input to trigger
            auto re-rendering when switching between pages.

    Returns:
        children: List of Dash Components making up the grading fields.
    """

    if path != dash.page_registry["pages.home"]["path"] or not rubric_scheme_data:
        return dash.no_update

    return [
        dmc.Select(
            label="Question Number",
            id="question-grade-select",
            value="1",
            data=[
                {"value": i, "label": i} for i in rubric_scheme_data["questions"].keys()
            ],
            maxDropdownHeight=200,
            radius="md",
            size="lg",
            style={"margin-bottom": "16px", "width": 250},
        ),
        dmc.Group(
            children=[
                dmc.Group(
                    children=[
                        dmc.Text(
                            "Total score:",
                            size="xl",
                            weight=800,
                        ),
                        dmc.Text(
                            id="question-current-score",
                            size="xl",
                            weight=800,
                            underline=True,
                        ),
                        dmc.Text(
                            "of",
                            size="xl",
                            weight=800,
                        ),
                        dmc.Text(
                            rubric_scheme_data["questions"]["1"],
                            id="question-total-score",
                            size="xl",
                            weight=800,
                        ),
                    ],
                    noWrap=True,
                ),
            ],
            direction="column",
            position="apart",
            style={"padding": "8px 0px 8px 0px"},
        ),
        dmc.Stack(
            children=[rubric_item_component(0, "Correct", 0, False)],
            id="rubric-items-list",
            style={"padding": "8px 0px 8px 0px"},
        ),
        dmc.Group(
            id="add-rubric-input",
            children=[
                dmc.TextInput(
                    id="add-rubric-marks",
                    label="Enter marks deduction",
                    placeholder="e.g. (-) 1",
                    type="number",
                    required=True,
                ),
                dmc.TextInput(
                    id="add-rubric-description",
                    label="Enter rubric description",
                    placeholder="e.g. wrong sign used",
                    required=True,
                ),
                dmc.Button(
                    "Add rubric item",
                    id="add-rubric-button",
                    variant="light",
                ),
            ],
            direction="column",
            position="apart",
            style={"padding": "0px 0px 16px 0px"},
        ),
    ]


@callback(
    Output("question-total-score", "children"),
    Input("question-grade-select", "value"),
    State("rubric-scheme-data", "data"),
)
def update_total_score_display(
    question_num, rubric_scheme_data: RubricSchemeData | None
):
    """Updates the total score text based on selected question number.

    Args:
        question_num: Currently selected question number.
        rubric_scheme_data: RubricSchemeData representing total marks for all
            questions and per-question marks.
    """
    if not question_num or not rubric_scheme_data:
        return dash.no_update

    return rubric_scheme_data["questions"][question_num]


@callback(
    Output("question-grade-select", "value"),
    Input("file-index", "data"),
    prevent_initial_call=True,
)
def reset_selected_question_number(_file_idx):
    """Resets selected question number dropdown when changing files.

    Args:
        _file_idx: Index of changed file.

    Returns:
        value: 1 (default question selected)
    """

    return "1"


@callback(
    [
        Output("rubric-data", "data"),
        Output("add-rubric-marks", "value"),
        Output("add-rubric-description", "value"),
        Output("add-rubric-marks", "error"),
        Output("add-rubric-description", "error"),
    ],
    [
        Input("add-rubric-button", "n_clicks"),
        Input({"type": "rubric-delete", "index": ALL}, "n_clicks"),
        Input("rubric-item-edit-final-data", "data"),
    ],
    [
        State("add-rubric-marks", "value"),
        State("add-rubric-description", "value"),
        State("rubric-data", "data"),
        State("file-index", "data"),
        State("question-grade-select", "value"),
    ],
    prevent_initial_call=True,
)
def update_rubric_items(
    add_n_clicks,
    delete_n_clicks,
    edit_data: RubricEditData,
    marks,
    description,
    rubric_data,
    file_idx,
    question_num,
):
    """Monolithic callback updating rubric data across all files.

    Responds to addition, deletion or editing of rubric items.

    Args:
        add_n_clicks: Number of clicks of the "Add Rubric Item" button.
        delete_n_clicks: Number of clicks of the delete button for a rubric item.
        edit_data: Final dict of edits to apply to the rubric data store.
        marks: Current value in the rubric marks field (to be added).
        description: Current value in the rubric description field (to be added).
        rubric_data: RubricData containing mark deductions for each question
            for each file.
        file_idx: 0-based file index representing which file to render.
        question_num: Currently selected question number.

    Returns:
        data: Updated RubricData.
        marks_value: Either cleared out value for rubric marks field or
            no updates (if error).
        description_value: Either cleared out value for rubric description field
            or no updates (if error).
        marks_error: Error string, populated if user tries to add rubric item
            without a mark.
        description_error: Error string, populated if user tries to add rubric
            item without a description.
    """

    if ctx.triggered_id == "add-rubric-button" and add_n_clicks:
        # Add rubric item
        marks_err, description_err = (
            "",
            "",
        )

        if not marks:
            marks_err = "Marks cannot be 0"

        if not description:
            description_err = "Rubric description cannot be empty"

        if marks_err or description_err:
            return (
                dash.no_update,
                dash.no_update,
                dash.no_update,
                marks_err,
                description_err,
            )

        return (
            add_rubric_item(
                rubric_data, file_idx, question_num, add_n_clicks, marks, description
            ),
            "",
            "",
            "",
            "",
        )
    elif (
        isinstance(ctx.triggered_id, dict) and ctx.triggered_id.type == "rubric-delete"
    ):
        # NOTE: workaround to prevent accidental deletion of rubric items when changing
        # pages
        # This happens when changing pages and the Dash components representing the
        # rubric items are re-introduced into the layout
        # This triggers "rubric-delete" again, which we don't want
        # See https://dash.plotly.com/advanced-callbacks#when-dash-components-are-added-to-the-layout
        # for this caveat
        if not delete_n_clicks or (
            isinstance(delete_n_clicks, Iterable) and not any(delete_n_clicks)
        ):
            return dash.no_update

        # Delete rubric item
        return (
            delete_rubric_item(
                rubric_data, file_idx, question_num, ctx.triggered_id.index
            ),
            dash.no_update,
            dash.no_update,
            "",
            "",
        )
    elif ctx.triggered_id == "rubric-item-edit-final-data":
        # Apply resolved edits from edit rubric item workflow
        # This "rubric-item-edit-final-data" is an intermediate data store
        # populated after allowing the user to choose whether they want to apply
        # the change to a rubric item to all matching rubric items
        if not edit_data or (isinstance(edit_data, Iterable) and not any(edit_data)):
            return dash.no_update

        # Assume that all final edits are in "new" field of edit_data
        for edit in edit_data["new"]:
            new_rubric_item = RubricItem.from_dict(edit)
            for item in rubric_data[str(new_rubric_item.file_idx)][
                str(new_rubric_item.question_num)
            ]:
                if item["item_idx"] == new_rubric_item.item_idx:
                    item["marks"] = new_rubric_item.marks
                    item["description"] = new_rubric_item.description
                    break

        return (
            rubric_data,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
        )
    else:
        return dash.no_update


@callback(
    Output({"type": "rubric-item", "index": MATCH}, "children"),
    Input({"type": "rubric-edit", "index": MATCH}, "n_clicks"),
    [
        State({"type": "rubric-marks", "index": MATCH}, "children"),
        State({"type": "rubric-desc", "index": MATCH}, "children"),
    ],
    prevent_initial_call=True,
)
def edit_rubric_item(edit_n_clicks, rubric_marks, rubric_desc):
    """Enter edit mode for a rubric item.

    Replaces the text components for the rubric item with input Components
    instead for the user to perform edits when the edit button for a rubric
    item is clicked.

    Args:
        edit_n_clicks: Number of times the rubric item edit button is clicked.
        rubric_marks: Number of marks of the rubric item to be edited.
        rubric_desc: Description of the rubric item to be edited.

    Returns:
        children: List of Dash Components, including the input fields populated with
            the original values of the rubric item being edited.
    """

    if not edit_n_clicks or (
        isinstance(edit_n_clicks, Iterable) and not any(edit_n_clicks)
    ):
        return dash.no_update

    item_idx = ctx.triggered_id.index
    children = [
        dmc.Group(
            children=[
                dmc.TextInput(
                    value=rubric_marks.strip("+"),
                    # Store original value in placeholder
                    placeholder=rubric_marks.strip("+"),
                    style={"width": 60, "margin": "0px 0px 5px"},
                    type="number",
                    id={"type": "rubric-marks-edit", "index": item_idx},
                ),
                dmc.ActionIcon(
                    DashIconify(icon="bi:check-square", width=20),
                    class_name="rubric-edit-done-button",
                    id={"type": "rubric-edit-done", "index": item_idx},
                    radius="sm",
                    variant="hover",
                ),
            ],
            position="apart",
        ),
        dmc.TextInput(
            value=rubric_desc,
            # Store original value in placeholder
            placeholder=rubric_desc,
            style={"width": 200},
            id={"type": "rubric-desc-edit", "index": item_idx},
        ),
        # rubric-item-edit-data is an intermediate store for processing
        # matched rubric items, if any, based on the edited rubric data.
        # There is one of such store per rubric item being edited.
        # rubric-item-edit-final-data will be the final store that contains
        # all the updates we want to apply.
        # TODO: Slightly hacky/confusing, but for now used to implement the
        # indirection due to the modal popup when matched rubric items found
        dcc.Store(id={"type": "rubric-item-edit-data", "index": item_idx}),
    ]

    return children


@callback(
    Output({"type": "rubric-item-edit-data", "index": MATCH}, "data"),
    Input({"type": "rubric-edit-done", "index": MATCH}, "n_clicks"),
    [
        State({"type": "rubric-marks-edit", "index": MATCH}, "value"),
        # We stored the original value of the edited description in the
        # placeholder in `edit_rubric_item`
        State({"type": "rubric-marks-edit", "index": MATCH}, "placeholder"),
        State({"type": "rubric-desc-edit", "index": MATCH}, "value"),
        # We stored the original value of the edited description in the
        # placeholder in `edit_rubric_item`
        State({"type": "rubric-desc-edit", "index": MATCH}, "placeholder"),
        State("rubric-data", "data"),
        State("file-index", "data"),
        State("question-grade-select", "value"),
    ],
    prevent_initial_call=True,
)
def finish_edit_rubric_item(
    done_n_clicks,
    rubric_marks_edited,
    rubric_marks_original,
    rubric_desc_edited,
    rubric_desc_original,
    rubric_data,
    file_idx,
    question_num,
):
    """Exit edit mode for a rubric item.

    Triggered when the user clicks on the done/check button when in rubric edit
    mode, indicating completion of rubric edits. At this point, we want to
    check for matching rubric items based on the rubric item that has just
    been edited.

    Then, we output the list of possible edits to the intermediate
    `rubric-item-edit-data` store. This triggers the modal which goes displays
    these edits to the user, allowing them the option of whether they want to
    apply the original edit to all questions across all files, just this current question
    across all files, or just this single edit for this file.

    The need for the intermediate `rubric-item-edit-data` store is an
    additional layer of indirection meant to delay the final edits to the
    rubric data store while the user is still at the modal.

    Args:
        done_n_clicks: Number of clicks of the rubric item done button.
        rubric_marks_edited: New marks for the edited rubric item.
        rubric_marks_original: Original marks for the edited rubric item.
        rubric_desc_edited: New description for the edited rubric item.
        rubric_desc_original: Original description for the edited rubric item.
        rubric_data: RubricData containing mark deductions for each question
            for each file.
        file_idx: 0-based file index representing which file to render.
        question_num: Question number associated with rubric item being edited.

    Returns:
        edit_data: Intermediate RubricEditData structure containing list of
            possible rubric edits.
    """

    if not done_n_clicks or (
        isinstance(done_n_clicks, Iterable) and not any(done_n_clicks)
    ):
        return dash.no_update

    # Assume marks are deductions by default
    rubric_marks_edited = -abs(int(str(rubric_marks_edited).strip()))
    edits = {
        "new": [
            RubricItem(
                rubric_marks_edited,
                rubric_desc_edited,
                ctx.triggered_id.index,
                file_idx,
                question_num,
            )
        ]
    }

    # If there is no change to the values of the rubric item being edited,
    # simply return original rubric item
    if (
        rubric_marks_edited == rubric_marks_original
        and rubric_desc_edited == rubric_desc_original
    ):
        return edits

    file_idx = str(file_idx)
    question_num = str(question_num)
    # Find matching rubric items across all files and pages
    matched_rubric_items = []
    for f_idx, pages in rubric_data.items():
        for q_num, rubric_items in pages.items():
            for item in rubric_items:
                item = RubricItem.from_dict(item)
                # Two rubric items are said to "match" if they have the same marks
                # and description.
                if (
                    item.description == rubric_desc_original
                    and int(item.marks) == int(rubric_marks_original)
                    and not (str(f_idx) == file_idx and str(q_num) == question_num)
                ):
                    matched_rubric_items.append(item)

    # No matches found -- just return original rubric item
    if not matched_rubric_items:
        return edits

    # Matches found -- store list of possible matching rubric items in
    # separate field
    edits["original_marks"] = rubric_marks_original
    edits["matched_rubric_items"] = matched_rubric_items

    return edits


@callback(
    [
        Output("rubric-match-modal", "children"),
        Output("rubric-match-modal", "opened"),
        Output("rubric-item-edit-final-data", "data"),
    ],
    [
        Input("rubric-match-modal-all-qns-btn", "n_clicks"),
        Input("rubric-match-modal-current-qns-btn", "n_clicks"),
        Input("rubric-match-modal-current-btn", "n_clicks"),
        Input({"type": "rubric-item-edit-data", "index": ALL}, "data"),
    ],
    [
        State("student-number-input", "value"),
        State("question-grade-select", "value"),
        State("student-num-file-data", "data"),
    ],
    prevent_initial_call=True,
)
def handle_matching_rubric_items_modal(
    all_btn,
    current_qns_btn,
    current_btn,
    edit_data,
    student_num,
    question_num,
    student_num_file_map,
):
    """Handles interactions within the modal to apply matching rubric edits.

    Either:
        - Generates children for the modal in response to `rubric-item-edit-data`
          being populated.
        - Closes the modal in response to any of the modal option buttons being
          selected by the user and populates `rubric-item-edit-final-data`
          with the final list of edits to be applied, depending on the option
          chosen.

    Args:
        all_btn: Number of clicks of the "All questions" option in the modal.
        current_qns_btn: Number of clicks of the "Current question" option in
            the modal.
        current_btn: Number of clicks of the "Current edit only" option in the
            modal.
        edit_data: Intermediate RubricEditData structure containing list of
            possible rubric edits.
        student_num: Current value in the student number input field.
        question_num: Currently selected question number.
        student_num_file_map: A dict containing the mapping of file indexes to
            student numbers.

    Returns:
        children: Dash Components to populate the modal with.
        opened: Boolean indicating whether the rubric edit modal should be
            closed or open.
        data: Final dict of edits to apply to the rubric data store.
    """

    # Property of pattern matching callback: since we match on ALL indexes,
    # Dash automatically assumes that we have more than one trigger source
    # and converts our data to a list.
    # The invariant we maintain is that we can only perform one edit process
    # at a time (i.e. the whole finish edit -> check for matching rubric items
    # -> finalize edits flow), hence can just take first element of this list
    if edit_data:
        edit_data = edit_data[0]

    # No matching items found -- no need to open modal
    if not edit_data or (edit_data and "matched_rubric_items" not in edit_data):
        return dash.no_update, False, edit_data

    if ctx.triggered_id == "rubric-match-modal-current-btn" and current_btn:
        # Only apply current edit
        return dash.no_update, False, edit_data
    elif ctx.triggered_id == "rubric-match-modal-all-qns-btn" and all_btn:
        # Apply rubric edit to all questions, all files
        new_marks = edit_data["new"][0]["marks"]

        for item in edit_data["matched_rubric_items"]:
            rubric_item = RubricItem.from_dict(item)
            edit_data["new"].append(
                RubricItem(
                    new_marks,
                    *attrgetter("description", "item_idx", "file_idx", "question_num")(
                        rubric_item
                    ),
                )
            )

        return dash.no_update, False, edit_data
    elif ctx.triggered_id == "rubric-match-modal-current-qns-btn" and current_qns_btn:
        # Apply rubric edit to only current question, all files
        new_marks = edit_data["new"][0]["marks"]

        for item in edit_data["matched_rubric_items"]:
            rubric_item = RubricItem.from_dict(item)
            if int(rubric_item.question_num) != int(question_num):
                continue

            edit_data["new"].append(
                RubricItem(
                    new_marks,
                    *attrgetter("description", "item_idx", "file_idx", "question_num")(
                        rubric_item
                    ),
                )
            )

        return dash.no_update, False, edit_data

    # Generate modal children on initial population of intermediate edit store
    return (
        generate_rubric_match_modal_children(
            edit_data, student_num, question_num, student_num_file_map
        ),
        True,
        dash.no_update,
    )


@callback(
    Output("rubric-items-list", "children"),
    [
        Input("rubric-data", "data"),
        Input("file-index", "data"),
        Input("question-grade-select", "value"),
    ],
    prevent_initial_call=True,
)
def render_rubric_items(rubric_data, file_idx, question_num):
    """Renders list of rubric items in response to rubric data changes.

    Args:
        rubric_data: RubricData containing mark deductions for each question
            for each file.
        file_idx: 0-based file index representing which file to render.
        question_num: Currently selected question number.

    Returns:
        children: List of Dash components, one for every RubricItem.
    """

    # Note: dcc.Store data are JSON-serialized, and Python converts integer
    # keys to strings
    # To avoid surprises, just using string keys throughout
    file_idx = str(file_idx)
    question_num = str(question_num)

    # Render default "0" rubric item for every question
    # Just to indicate to user that default mark for every question, without
    # any rubric items added, is full marks
    items = [rubric_item_component(0, "Correct", 0, False)]
    if (
        rubric_data
        and file_idx in rubric_data
        and question_num in rubric_data[file_idx]
    ):
        for item in rubric_data[file_idx][question_num]:
            item = RubricItem.from_dict(item)
            items.append(
                rubric_item_component(item.marks, item.description, item.item_idx)
            )

    return items


@callback(
    [
        Output("question-current-score", "children"),
        Output("question-current-score", "color"),
    ],
    [
        Input("rubric-items-list", "children"),
        State("rubric-scheme-data", "data"),
        State("question-grade-select", "value"),
    ],
    prevent_initial_call=True,
)
def update_current_score(
    rubric_items, rubric_scheme: RubricSchemeData | None, question_num
):
    """Computes the current score for the current question.

    Updates the current score in accordance to the rubric items
    associated with the question. If a new mark deduction (rubric item)
    is added, the score is re-computed and reflected in the grading section.

    Args:
        rubric_items: List of rendered RubricItem Dash components.
        rubric_scheme: RubricSchemeData representing total marks for all
            questions and per-question marks.
        question_num: Currently selected question number.

    Returns:
        children: New current score for the current question.
        color: Color for the current score (green if non-negative, red if
            negative).
    """

    if not rubric_scheme:
        return dash.no_update

    total_score = rubric_scheme["questions"][question_num]
    scores = [
        int(
            item["props"]["children"][0]["props"]["children"][0]["props"][
                "children"
            ].strip("+")
        )
        for item in rubric_items
    ]
    # Scores will be enforced to be negative
    score = total_score + sum(scores)

    return score, "dark" if score >= 0 else "red"


@callback(
    Output("student-num-file-data", "data"),
    [
        Input("student-number-input", "value"),
        Input("upload-store", "data"),
    ],
    [
        State("student-num-file-data", "data"),
        State("file-index", "data"),
    ],
)
def update_student_file_map(student_num, files, student_num_file_map, file_idx):
    """Updates file index to student number data store.

    Args:
        student_num: Current value in the student number input field.
        files: dict mapping file indexes to a base64-encoded bytestring of a
            uploaded PDF file.
        student_num_file_map: A dict containing the mapping of file indexes to
            student numbers.
        file_idx: 0-based file index representing which file to render.

    Returns:
        data: Updated dict containing mapping of file indexes to student
            numbers.
    """

    # Perform one-time population of student number, if can be extracted from
    # uploaded filenames
    if ctx.triggered_id == "upload-store":
        data = {}

        for file_idx, file in files.items():
            sn_match = re.search(STUDENT_NUM_REGEX, file["name"])
            if sn_match:
                data[file_idx] = {}
                data[file_idx] = sn_match.group(1).upper()

        return data

    if not student_num or not file_idx:
        return dash.no_update

    student_num_file_map[file_idx] = student_num

    return student_num_file_map


@callback(
    [
        Output("student-number-input", "error"),
        Output("student-number-input", "value"),
        Output("grading-submit-modal", "children"),
        Output("grading-submit-modal", "opened"),
        Output("completed-data", "data"),
    ],
    [
        Input("submit-grading-btn", "n_clicks"),
        Input("grading-modal-submit-btn", "n_clicks"),
        Input("grading-modal-close-btn", "n_clicks"),
        Input("file-index", "data"),
    ],
    [
        State("upload-store", "data"),
        State("student-number-input", "value"),
        State("student-num-file-data", "data"),
        State("completed-data", "data"),
    ],
    prevent_initial_call=True,
)
def modify_grading_fields(
    submit_btn_clicks,
    _modal_submit_btn,
    _modal_close_btn,
    file_idx,
    files,
    student_num,
    student_num_file_map,
    completed_data,
):
    """Updates student number input and other grading-related metadata fields.

    Args:
        submit_btn_clicks: Number of clicks for "Submit grading" button.
        _modal_submit_btn: Number of clicks for "Submit" button in
            confirm submission modal.
        _modal_close_btn: Number of clicks for "Close" button in
            confirm submission modal.
        file_idx: 0-based file index representing which file to render.
        files: dict mapping file indexes to a base64-encoded bytestring of a
            uploaded PDF file.
        student: Current value in the student number input field.
        student_num_file_map: A dict containing the mapping of file indexes to
            student numbers.
        completed_data: Set of IDs for files that have been marked as completed.

    Returns:
        error: Error string, if student number input missing and try to submit
            grading.
        value: Value to populate the student number input field with. Usually
            changes when switching between files or when files first uploaded.
            (auto extracted from filename)
        children: Dash Components generated for display in the confirm
            submission modal.
        opened: Boolean indicating whether confirm submission modal should be
            opened or closed.
        completed_data: Updated set of IDs for files that have been marked as
            completed.
    """

    if ctx.triggered_id == "grading-modal-submit-btn":
        return (
            "",
            student_num,
            GRADING_SUBMIT_MODAL_DEFAULT_CHILDREN,
            False,
            mark_file_as_completed(completed_data, file_idx),
        )
    elif ctx.triggered_id == "grading-modal-close-btn":
        return (
            "",
            student_num,
            GRADING_SUBMIT_MODAL_DEFAULT_CHILDREN,
            False,
            dash.no_update,
        )
    elif ctx.triggered_id == "file-index":
        return (
            "",
            retrieve_file_student_num(student_num_file_map, file_idx),
            dash.no_update,
            False,
            dash.no_update,
        )
    elif ctx.triggered_id == "upload-store":
        # Process first population of student number for first file
        for file_idx, file in files.items():
            sn_match = re.search(STUDENT_NUM_REGEX, file["name"])
            return (
                "",
                sn_match.group(1).upper() if sn_match else dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
            )
    # TODO: add case to populate fields when coming from page change
    elif ctx.triggered_id == "submit-grading-btn" and submit_btn_clicks:
        # "Submit final grading" flow after button click
        if not student_num:
            return (
                "Student number required",
                dash.no_update,
                dash.no_update,
                False,
                dash.no_update,
            )

        children = [
            dmc.Text(f"Confirm submission for student {student_num}?")
        ] + GRADING_SUBMIT_MODAL_DEFAULT_CHILDREN

        return (
            "",
            student_num,
            children,
            True,
            dash.no_update,
        )

    return dash.no_update


@callback(
    [
        Output("grading-pdf-download", "data"),
        Output("top-alert", "hide"),
        Output("top-alert", "children"),
    ],
    Input("export-grading-pdf-btn", "n_clicks"),
    [
        State("student-num-file-data", "data"),
        State("rubric-data", "data"),
        State("file-index", "data"),
        State("rubric-scheme-data", "data"),
    ],
    prevent_initial_call=True,
)
def export_grading_to_pdf(
    export_btn_clicks,
    student_num_file_map,
    rubric_data,
    file_idx,
    rubric_scheme_data: RubricSchemeData | None,
):
    """Callback to render and trigger download of PDF containing grading breakdown.

    Layouts the PDF file using the `reportlab` library and generates the download
    in the browser.

    Triggers top alert banner if there is no or invalid grading data found.

    Args:
        export_btn_clicks: Number of clicks of "Export grading to PDF" button.
        student_num_file_map: A dict containing the mapping of file indexes to
            student numbers.
        rubric_data: RubricData containing mark deductions for each question
            for each file.
        file_idx: 0-based file index representing which file to render.
        rubric_scheme_data: RubricSchemeData representing total marks for all
            questions and per-question marks.

    Returns:
        data: File contents of generated PDF file.
        hide: Whether to trigger top alert banner.
        children: Contents of top alert banner.
    """

    file_idx = str(file_idx)

    err = (
        not student_num_file_map
        or (file_idx is not None and file_idx not in student_num_file_map)
    ) or (not rubric_data or (file_idx is not None and file_idx not in rubric_data))

    if err:
        return (
            dash.no_update,
            False,
            "No grading data found, upload a file or start grading first.",
        )

    if not export_btn_clicks:
        return dash.no_update

    # Compute score breakdown
    student_num = student_num_file_map[file_idx]
    questions_marks = marks_by_question(
        rubric_data, rubric_scheme_data, student_num_file_map, student_num
    )

    def _main_page(canvas, doc):
        PAGE_WIDTH, PAGE_HEIGHT = defaultPageSize[0:2]

        canvas.saveState()
        canvas.setFont("Times-Bold", 16)
        canvas.drawCentredString(
            PAGE_WIDTH / 2.0, PAGE_HEIGHT - 2.0 * inch, "Grade Report"
        )
        canvas.setFont("Times-Roman", 14)
        if student_num:
            canvas.drawCentredString(
                PAGE_WIDTH / 2.0, PAGE_HEIGHT - 2.4 * inch, student_num
            )
        canvas.restoreState()

    with tempfile.NamedTemporaryFile() as f:
        doc = SimpleDocTemplate(f)
        flowables = [Spacer(1, 2 * inch)]
        stylesheet = getSampleStyleSheet()
        style = stylesheet["Normal"]
        heading = stylesheet["Heading3"]
        flowables.append(
            Paragraph(
                f"Total marks: {sum(itertools.chain.from_iterable(questions_marks.values()))}",
                heading,
            )
        )
        flowables.append(Spacer(1, 0.1 * inch))
        flowables.append(Paragraph("Breakdown:", heading))
        flowables.append(Spacer(1, 0.05 * inch))

        for question, marks in questions_marks.items():
            # For each question, generate the final mark
            list_items = [
                Paragraph(f"Question {question}: {sum(marks)}", style),
            ]

            # As well as the comments for each rubric critera/mark deduction, if any
            comments = [Paragraph("Comments:", style)]
            comments_sub = []
            for question_num, rubric_items in rubric_data[file_idx].items():
                q_num = int(question_num)
                if q_num != question:
                    continue

                comments_sub.extend(
                    f"{item['description']} ({item['marks']})" for item in rubric_items
                )

            comments.append(
                ListFlowable(
                    [ListItem(Paragraph(c, style)) for c in comments_sub],
                    bulletFontSize=5,
                    bulletType="bullet",
                    leftIndent=9,
                    start="square",
                )
            )

            list_items.append(comments)
            flowables.append(
                ListFlowable(list_items, bulletType="bullet", leftIndent=9)
            )
            flowables.append(Spacer(1, 0.1 * inch))

        doc.build(flowables, onFirstPage=_main_page)

        # `seek` necessary else PDF will be blank
        # Since we are in the same context manager and the canvas functions
        # above probably advance the IO cursor, need to seek to
        # start so that `send_file` reads bytes from the beginning
        f.seek(0)
        return (
            dcc.send_file(f.name, f"{student_num}.pdf" if student_num else "grade.pdf"),
            dash.no_update,
            dash.no_update,
        )
