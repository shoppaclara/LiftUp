# Prerequisites
To run this application, the following are required:
- Python 3.x
- A code editor or terminal (Visual Studio Code or Sublime recommended)
- The Pillow library for image handling

# Required Python Libraries:
- tkinter
- json
- os
- datetime
- PIL (Pillow - must be installed separately)
All but PIL should come with a default Python 3 installation.
To install pillow, run: pip install pillow

# Files required:
The following files must all be present in the same folder before running the application. These files can be downloaded from the Required-Files branch of this repository. 
- liftup_main.py
The main Python file for the application. It contains all application logic, class
definitions, and the Tkinter main loop that launches the graphical user interface.
- workoutLogs.json
Stores logged workout sessions. This file may be empty initially, but it must exist
before running the application. If downloaded, it comes with pre-existing
complete workout logs.
- workoutPlans.json
Stores user-created workout plans. This file may also be empty but must exist. If
downloaded from here and not made, it comes with pre-existing complete
workout plans.
- logo_image.png
Image asset used within the application interface.

# Folder Creation
If a required file is missing, the application will fail to start.
Create a new folder on your computer (e.g., LiftUp), and place all required files directly inside
the folders. Do not place the files in subfolders.
