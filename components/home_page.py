import dash_mantine_components as dmc
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

                        # Card Content - using default theme colors
                        dmc.Stack(
                            [
                                dmc.Title(
                                    "Welcome to UTC Dashboard,",
                                    order=2,
                                    fw=700,
                                    mb="md"
                                ),

                                dmc.Text(
                                    "his platform provides a suite of tools designed to assist with leak detection and survey data analysis.",
                                    size="lg",
                                    mb="sm"
                                ),

                                dmc.Text(
                                    "Use the sidebar to access available utilities such as survey point reduction, data visualization, and reporting features.",
                                    size="lg",
                                    mb="md"
                                ),

                                dmc.Divider(size="sm"),

                                dmc.Text(
                                    "Developed by: Frank Vejahati, PhD, P.Eng.",
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
                style={"minHeight": "70vh", "paddingTop": "1rem"}
            )
        ],
        size="lg",
        px="md"
    )
