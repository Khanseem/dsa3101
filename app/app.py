import dash
import dash_bootstrap_components as dbc
from backend.api import setup_env
from dash import Dash, dcc, html

external_stylesheets = ["https://rsms.me/inter/inter.css", dbc.themes.BOOTSTRAP]


app = Dash(
    __name__,
    external_stylesheets=external_stylesheets,
    use_pages=True,
    suppress_callback_exceptions=True,
)

nav = html.Div(
    [
        dbc.Nav(
            [
                dbc.NavItem(
                    dbc.NavLink(
                        f"{page['name']}",
                        href=page["relative_path"],
                        active="exact",
                    )
                )
                for page in dash.page_registry.values()
            ],
            pills=True,
            style={"margin": "10px"},
        )
    ]
)


app.layout = html.Div(
    [
        nav,
        dash.page_container,
        # Stores uploaded data as a base64-encoded binary string
        dcc.Store(id="upload-store", storage_type="session"),
        # Stores the index of the currently displayed file
        dcc.Store(id="file-index"),
        # Stores the page index of the currently displayed filed
        dcc.Store(id="page-index"),
        # Store user-added rubric data on a per file, per question basis
        dcc.Store(id="rubric-data", storage_type="session"),
        # Store mapping of file indexes to student numbers
        dcc.Store(id="student-num-file-data", storage_type="session"),
        # Set of IDs for files that have been marked as completed
        dcc.Store(id="completed-data", storage_type="session"),
        # Stores rubric data edits to be applied
        dcc.Store(id="rubric-item-edit-final-data"),
        # Stores rubric scheme (total score + marks per question)
        dcc.Store(id="rubric-scheme-data", storage_type="session"),
    ]
)


if __name__ == "__main__":
    setup_env()
    app.run(host="0.0.0.0", port=8080, debug=False)
