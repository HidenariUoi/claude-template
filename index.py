import dash_design_kit as ddk
import pages

from dash import dcc, html, Input, Output, State, clientside_callback
from app import app, snap, PORTAL_URL
from schedules import delete_data  # noqa #schedule呼び出しのために必須
from multiprocessing.util import register_after_fork


def dispose_engine(engine):
    """dispose SqlAlchemy engine in register_after_fork"""
    engine.dispose()


server = app.server
celery_instance = snap.celery_instance
celery_instance.conf.timezone = "Asia/Tokyo"
register_after_fork(snap.store.db.engine, dispose_engine)


app.layout = ddk.App(
    show_editor=False,
    children=[
        ddk.Sidebar(
            id="sidebar",
            foldable=False,
            style={"maxWidth": "250px"},
            children=[
                dcc.Link(
                    href=app.get_relative_path("/"),
                    children=[
                        ddk.Logo(
                            src=app.get_relative_path("/assets/logo.jpg"),
                            style={"width": "250px", "height": "auto"},
                        ),
                    ],
                ),
                ddk.Title(
                    children=[
                        "〇〇計画最適化",
                        html.Br(),
                        "シミュレータ",
                    ],
                    style={"width": "250px"},
                ),
                ddk.Menu(
                    [
                        html.Div(
                            id="sidebar-fold-button",
                            children=[
                                ddk.Icon(
                                    id="sidebar-fold-button-icon",
                                    icon_name="angle-left",
                                    icon_color="#5fade2",
                                ),
                            ],
                            style={
                                "font-size": "25px",
                                "width": "100%",
                                "margin": "20px auto 20px auto",
                                "cursor": "pointer",
                                "text-align": "center",
                            },
                        ),
                        html.A(
                            "Application Portal",
                            href=PORTAL_URL,
                            target="_blank",
                            style={"white-space": "nowrap"},
                        ),
                        dcc.Link(
                            href=app.get_relative_path("/model"),
                            children=[
                                ddk.Icon(icon_name="flask"),
                                "計画作成",
                            ],
                            style={"white-space": "nowrap"},
                        ),
                        dcc.Link(
                            href=app.get_relative_path("/archive"),
                            children=[ddk.Icon(icon_name="archive"), "実行履歴"],
                            style={"white-space": "nowrap"},
                        ),
                        html.Div(id="admin-link"),
                    ]
                ),
                dcc.Store(id="sidebar-dummy"),
            ],
        ),
        ddk.SidebarCompanion(
            children=[
                dcc.Location(id="url"),
                html.Div(
                    id="content",
                    style={"minHeight": "100vh", "margin-bottom": "100px"},
                ),
            ],
        ),
    ],
)


@app.callback(Output("content", "children"), [Input("url", "pathname")])
def display_content(pathname):
    page_name = app.strip_relative_path(pathname)
    if not page_name:  # None or ''
        return pages.home.layout()
    elif page_name == "optimize":
        return pages.optimize.layout()
    elif page_name == "archive":
        return pages.archive.layout()
    elif page_name.startswith("snapshot-"):
        return pages.snapshot.layout(page_name)
    else:
        return "404"


clientside_callback(
    """
    function (click) {
        document.querySelector('#sidebar .sidebar--content').toggleAttribute('folded');
        var current_folded_state = document.querySelector('#sidebar #menu').getAttribute('data-folded');
        var new_folded_state = (current_folded_state === 'false') ? 'true' : 'false';
        document.querySelector('#sidebar #menu').setAttribute('data-folded', new_folded_state);
        return 'dummy';
    }
    """,
    Output("sidebar-dummy", "data"),
    Input("sidebar-fold-button", "n_clicks"),
    prevent_initial_call=True,
)
clientside_callback(
    """
    function (click, current_children) {
        return (current_children === 'angle-left') ? 'angle-right' : 'angle-left';
    }
    """,
    Output("sidebar-fold-button-icon", "icon_name"),
    Input("sidebar-fold-button", "n_clicks"),
    State("sidebar-fold-button-icon", "icon_name"),
    prevent_initial_call=True,
)


if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", use_reloader=True)
