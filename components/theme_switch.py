import dash_mantine_components as dmc
from dash import Input, Output, clientside_callback
from dash_iconify import DashIconify

theme_toggle = dmc.Switch(
    offLabel=DashIconify(
        icon="radix-icons:sun", width=15, color=dmc.DEFAULT_THEME["colors"]["yellow"][8]
    ),
    onLabel=DashIconify(
        icon="radix-icons:moon",
        width=15,
        color=dmc.DEFAULT_THEME["colors"]["yellow"][6],
    ),
    id="color-scheme-switch",
    persistence=True,
    persistence_type="local",
    color="grey",
    mt="md",
)

# Client-side callback for color scheme switching with full theme persistence
clientside_callback(
    """ 
    (switchOn) => {
       // Set the color scheme
       const colorScheme = switchOn ? 'dark' : 'light';
       document.documentElement.setAttribute('data-mantine-color-scheme', colorScheme);
       
       // Save theme settings to localStorage
       const themeSettings = {
           colorScheme: colorScheme,
           timestamp: Date.now()
       };
       
       // Get existing theme settings from localStorage
       try {
           const existingSettings = localStorage.getItem('dmc-theme-settings');
           if (existingSettings) {
               const parsed = JSON.parse(existingSettings);
               themeSettings.primaryColor = parsed.primaryColor;
               themeSettings.defaultRadius = parsed.defaultRadius;
               themeSettings.shadow = parsed.shadow;
           }
       } catch (e) {
           console.log('No existing theme settings found');
       }
       
       localStorage.setItem('dmc-theme-settings', JSON.stringify(themeSettings));
       
       return window.dash_clientside.no_update;
    }
    """,
    Output("color-scheme-switch", "id"),
    Input("color-scheme-switch", "checked"),
)

# Clientside callback to save theme customization settings to localStorage
clientside_callback(
    """
    (color, radius, shadow) => {
        // Save theme customization settings to localStorage
        const themeSettings = {
            primaryColor: color,
            defaultRadius: radius,
            shadow: shadow,
            timestamp: Date.now()
        };
        
        // Get existing settings (including color scheme) from localStorage
        try {
            const existingSettings = localStorage.getItem('dmc-theme-settings');
            if (existingSettings) {
                const parsed = JSON.parse(existingSettings);
                themeSettings.colorScheme = parsed.colorScheme;
            }
        } catch (e) {
            console.log('No existing theme settings found');
        }
        
        localStorage.setItem('dmc-theme-settings', JSON.stringify(themeSettings));
        
        return window.dash_clientside.no_update;
    }
    """,
    Output("color-picker", "id"),
    Input("color-picker", "value"),
    Input("radius", "value"), 
    Input("shadow", "value"),
)

# Clientside callback to restore theme settings from localStorage on page load
clientside_callback(
    """
    (pathname) => {
        // Restore theme settings from localStorage
        try {
            const savedSettings = localStorage.getItem('dmc-theme-settings');
            if (savedSettings) {
                const settings = JSON.parse(savedSettings);
                
                // Restore color scheme
                if (settings.colorScheme) {
                    document.documentElement.setAttribute('data-mantine-color-scheme', settings.colorScheme);
                }
                
                // Return settings to restore component values
                return [
                    settings.colorScheme === 'dark' ? true : false,  // theme switch
                    settings.primaryColor || '#51cf66',  // color picker default
                    settings.defaultRadius || 2,  // radius slider default
                    settings.shadow || 2  // shadow slider default
                ];
            }
        } catch (e) {
            console.log('Error loading theme settings:', e);
        }
        
        // Return defaults if no saved settings
        return [false, '#51cf66', 2, 2];
    }
    """,
    [Output("color-scheme-switch", "checked"),
     Output("color-picker", "value"),
     Output("radius", "value"),
     Output("shadow", "value")],
    Input("url", "pathname"),
)
