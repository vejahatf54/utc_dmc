import re

# Read the file
with open('c:\\Temp\\python_projects\\DMC\\components\\csv_to_rtu_page.py', 'r') as f:
    content = f.read()

# Define replacements
replacements = [
    (r'DashIconify\(icon="tabler:help"', 'BootstrapIcon(icon="question-circle"'),
    (r'DashIconify\(icon="tabler:info-circle"', 'BootstrapIcon(icon="info-circle"'),
    (r'DashIconify\(icon="tabler:lightbulb"', 'BootstrapIcon(icon="lightbulb"'),
    (r'DashIconify\(icon="tabler:file-upload"', 'BootstrapIcon(icon="upload"'),
    (r'DashIconify\(icon="tabler:cloud-upload"', 'BootstrapIcon(icon="cloud-upload"'),
    (r'DashIconify\(icon="tabler:transform"', 'BootstrapIcon(icon="arrow-repeat"'),
    (r'DashIconify\(icon="tabler:file-export"', 'BootstrapIcon(icon="download"'),
    (r'DashIconify\(icon="tabler:file-spreadsheet"', 'BootstrapIcon(icon="file-earmark-spreadsheet"'),
    (r'DashIconify\(icon="tabler:x"', 'BootstrapIcon(icon="x"'),
    (r'DashIconify\(icon="tabler:alert-circle"', 'BootstrapIcon(icon="exclamation-circle"'),
]

# Apply all replacements
for old, new in replacements:
    content = re.sub(old, new, content)

# Write back
with open('c:\\Temp\\python_projects\\DMC\\components\\csv_to_rtu_page.py', 'w') as f:
    f.write(content)

print("Replacements completed!")
