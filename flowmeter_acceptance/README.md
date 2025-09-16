The flowmeter_acceptance tool was created to automate the partial commissioning and full acceptances of flowmeters by Leak Detection personnel. The repository here hosts:

1. flowmeter_main.py: Holds the background calculations for all commissioning checks
2. FM_Attempt_GUI.ui: Holds the design for the GUI
3. FM_GUI.py: Holds the code meant to render the GUI and provides its functionality by connecting to flowmeter_main.py
4. test_flowmeter_main.py: Holds several pytest functions meant to test flowmeter_main.py reliability
5. Tags.csv: Template for the tags to be assessed, L61 example on how to populate the csv

Running the script requires having the "start.exe" application in any directory, and an additional "Dependencies" folder, which includes files 1-3. Double-click on the 
application, and the GUI will appear (or run "start.exe" in a command window in the directory used). While the location of the "Tags.csv" (which holds the tag list to 
be assessed), lxx.dt and lxx.review can be located anywhere, for easy navigation, it is recommended to store it at the same level as "start.exe".
