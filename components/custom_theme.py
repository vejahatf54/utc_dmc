import json
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from components.theme_switch import theme_toggle

# Color mappings
colors = dmc.DEFAULT_THEME["colors"]
color_picker_value_mapping = {
    color: codes[5] for color, codes in colors.items() if color != "dark"}
theme_name_mapping = {codes[5]: color for color,
                      codes in colors.items() if color != "dark"}
size_name_mapping = {1: "xs", 2: "sm", 3: "md", 4: "lg", 5: "xl"}

# Color picker component
color_picker = dmc.Stack(
    [
        dmc.Text("Primary Color", size="xs", fw=500),
        dmc.ColorPicker(
            id="color-picker",
            size="sm",
            withPicker=False,
            swatches=list(color_picker_value_mapping.values()),
            swatchesPerRow=7,
            value=color_picker_value_mapping["green"],
        ),
    ]
)


def make_slider(title, id):
    """Create a slider component for theme customization."""
    return dmc.Stack(
        [
            dmc.Text(title, size="sm", fw=500),
            dmc.Slider(
                min=1,
                max=5,
                value=2,
                id=id,
                updatemode="drag",
                styles={"markLabel": {"display": "none"}},
                marks=[
                    {"value": 1, "label": "xs"},
                    {"value": 2, "label": "sm"},
                    {"value": 3, "label": "md"},
                    {"value": 4, "label": "lg"},
                    {"value": 5, "label": "xl"},
                ],
            ),
        ],
        mt="md",
    )


# Main customize theme component
customize_theme = dmc.Box(
    [
        dmc.ActionIcon(
            DashIconify(icon="emojione:artist-palette", width=24),
            id="modal-demo-button",
            variant="light",
            size="xl",
            radius="xl",
        ),
        dmc.Modal(
            id="modal-customize",
            size="sm",
            title=dmc.Group([
                DashIconify(icon="emojione:artist-palette", width=20),
                dmc.Text("Customize Theme", fw=600)
            ]),
            children=[
                dmc.Stack(
                    [
                        color_picker,
                        make_slider("Border Radius", "radius"),
                        make_slider("Shadow", "shadow"),
                        dmc.Divider(),
                        dmc.Group([
                            theme_toggle,
                            dmc.Text("Toggle light/dark mode",
                                     size="sm", c="dimmed")
                        ], justify="space-between")
                    ],
                    gap="md",
                    p="md",
                )
            ],
            zIndex=10000,
            centered=True,
            overlayProps={"backgroundOpacity": 0.3, "blur": 3},
        ),
    ]
)

# Combined theme controls component (only customize theme)
theme_controls = customize_theme
