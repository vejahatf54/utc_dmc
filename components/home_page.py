import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import html


def create_home_page():
    """Create a home page matching the LDUTC project design"""
    return dmc.Container(
        [
            dmc.Center(
                dmc.Card(
                    [
                        dmc.CardSection(
                            # Home Image - centered
                            dmc.Center(
                                html.Img(
                                    src="/assets/homeimage.png",
                                    style={
                                        "width": "100%",
                                        "maxWidth": "750px",
                                        "height": "auto",
                                        "borderRadius": "16px",
                                        "boxShadow": "0 4px 24px rgba(0,0,0,0.12)",
                                    },
                                    alt="Home Image"
                                )
                            ),
                            withBorder=True,
                            inheritPadding=True,
                            py="md"
                        ),

                        # Card Content - matching LDUTC exactly
                        dmc.Stack(
                            [
                                dmc.Title(
                                    "Welcome to UTC Dashboard,",
                                    order=2,
                                    fw=700,
                                    mb="md"
                                ),

                                dmc.Text(
                                    "This platform provides a suite of tools designed to assist with data analysis and visualization.",
                                    size="lg",
                                    mb="sm"
                                ),

                                dmc.Text(
                                    "Use the sidebar to access available utilities such as data processing, visualization, and reporting features.",
                                    size="lg",
                                    mb="md"
                                ),

                                dmc.Divider(size="sm"),

                                dmc.Text(
                                    "Built with Dash Mantine Components",
                                    size="sm",
                                    c="dimmed",
                                    mb=0
                                ),
                            ],
                            gap="sm",
                            p="xl"
                        )
                    ],
                    shadow="lg",
                    radius="lg",
                    withBorder=True,
                    className="home-hero-card",
                    style={"maxWidth": "900px", "width": "100%"}
                ),
                style={"minHeight": "80vh", "paddingTop": "2rem"}
            )
        ],
        size="xl",
        px="md"
    )
