from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QApplication, QWidget, QFileDialog, QMessageBox
from PyQt5.QtCore import QDateTime
import sys
import os
import datetime
import Dependencies.flowmeter_main

class flowmeter(QtWidgets.QMainWindow):
    def __init__(self):
        '''
        Creates the GUI and instantaites several inputs using the "connect" 
            method to locate a file in the given directory
-------------------------------------
        Parameters:
            None
-------------------------------------
        Returns:
            GUI to:
                1. Add inputs from the working directory
                2. Include additional inputs from the user
                3. Check off any checks desired
                4. Assess the inputs based on the working calculations in the connected test file
        '''
        
        super(flowmeter, self).__init__()
        self.ui = uic.loadUi('Dependencies/FM_Attempt_GUI.ui', self)

        global cwd
        cwd = os.getcwd()

        # Buttons when clicked allow the user to select (in the same working directory)
        # the file and post path in LineEdit (called from functions below)
        self.rtu_file_button.clicked.connect(self.rtu_file_button_clicked)
        self.csv_tags_button.clicked.connect(self.csv_tags_button_clicked)
        self.review_file_button.clicked.connect(self.review_file_button_clicked)

        self.start_time_edit.setDate(datetime.datetime.now())
        self.end_time_edit.setDate(datetime.datetime.now())

        self.ok_push_button.clicked.connect(self.ok_push_button_clicked)
        self.cancel_push_button.clicked.connect(self.cancel_push_button_clicked)

        self.show()

    def rtu_file_button_clicked(self):
        '''
        Connects to the working directory, and isolates all rtuData files 
            (files with .dt extension), and copies the file path
-------------------------------------
        Parameters:
            None
-------------------------------------
        Returns:
            fileName: str
                The path of the file selected, and holds it in the LineEdit widget in the GUI
        '''
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        options |= QFileDialog.DontUseCustomDirectoryIcons
        file_name, _ = QFileDialog.getOpenFileName(self, "Choose File", cwd, "dt (*.dt)", options=options)
        if file_name:
            self.rtu_file_line_edit.setText(file_name)
        return file_name

    def csv_tags_button_clicked(self):
        '''
        Connects to the working directory, and isolates all csv files 
            (files with .csv extension), and copies the file path
-------------------------------------
        Parameters:
            None
-------------------------------------
        Returns:
            fileName: str
                The path of the file selected, and holds it in the LineEdit widget in the GUI
        '''
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        options |= QFileDialog.DontUseCustomDirectoryIcons
        file_name, _ = QFileDialog.getOpenFileName(self, "Choose File", cwd, "csv (*.csv)" , options=options)
        if file_name:
            self.csv_tags_line_edit.setText(file_name)
        return file_name
    
    def review_file_button_clicked(self):
        '''
        Connects to the working directory, and isolates all review files 
            (files with .review extension), and copies the file path
-------------------------------------
        Parameters:
            None
-------------------------------------
        Returns:
            fileName: str
                The path of the file selected, and holds it in the LineEdit widget in the GUI
        '''
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        options |= QFileDialog.DontUseCustomDirectoryIcons
        file_name, _ = QFileDialog.getOpenFileName(self, "Choose File", cwd, "review (*.review)" , options=options)
        if file_name:
            self.review_file_line_edit.setText(file_name)
        return file_name

    def ok_push_button_clicked(self):
        '''
        Once Ok is selected, all variables are initialized based on the text 
            from the user input, and sent to the test file with its given initialization
-------------------------------------
        Parameters:
            None
-------------------------------------
        Returns:
            error: Pop up
                Only appears if the rtuFile, csvTags_File and reviewFile is empty.
        '''

        if self.partial_commissioning_check_box.isChecked():
            self.reliability_check_1_check_box.setChecked(True)
            self.reliability_check_2_check_box.setChecked(True)
            self.reliability_check_3_check_box.setChecked(True)
            self.reliability_check_4_check_box.setChecked(True)
            self.tc_check_1_check_box.setChecked(True)
            self.tc_check_2_check_box.setChecked(True)
            self.robustness_check_1_check_box.setChecked(True)
            self.accuracy_check_1_check_box.setChecked(True)
            self.accuracy_check_3_check_box.setChecked(True)
        
        if self.full_acceptance_check_box.isChecked():
            self.reliability_check_1_check_box.setChecked(True)
            self.reliability_check_2_check_box.setChecked(True)
            self.reliability_check_3_check_box.setChecked(True)
            self.reliability_check_4_check_box.setChecked(True)
            self.tc_check_1_check_box.setChecked(True)
            self.tc_check_2_check_box.setChecked(True)
            self.robustness_check_1_check_box.setChecked(True)
            self.accuracy_check_1_check_box.setChecked(True)
            self.accuracy_check_2_check_box.setChecked(True)
            self.accuracy_check_3_check_box.setChecked(True)

        # Setting the rtuFile and csvTagsFile names, used in test file
        rtu_file = self.rtu_file_line_edit.text()
        csv_tags_file = self.csv_tags_line_edit.text()
        review_file = self.review_file_line_edit.text()
        threshold_FLAT = self.FLAT_line_edit.text()
        min_Q = self.minimum_line_edit.text()
        max_Q = self.maximum_line_edit.text()
        accuracy_range = self.accuracy_range_line_edit.text()

        # Setting timeStart and timeEnd
        time_start = self.start_time_edit.dateTime().toPyDateTime()
        time_end = self.end_time_edit.dateTime().toPyDateTime()

        # Named inputs read and used in test file
        csv_file = self.csv_file_line_edit.text()
        report_name = self.report_name_line_edit.text()

        if rtu_file != "" and csv_tags_file != "" and review_file != "":
            Dependencies.flowmeter_main.main(rtu_file = rtu_file if rtu_file != "" else None,
                        csv_tags_file = csv_tags_file if csv_tags_file != "" else None,
                        review_file = review_file if review_file != "" else None,
                        csv_file = csv_file if csv_file != "" else "csvFile",
                        report_name = report_name if report_name != "" else "report",
                        time_start = time_start.strptime(str(time_start), "%Y-%m-%d %H:%M:%S").strftime("%y/%m/%d %H:%M:%S"),
                        time_end = time_end.strptime(str(time_end), "%Y-%m-%d %H:%M:%S").strftime("%y/%m/%d %H:%M:%S"),
                        threshold_FLAT = int(threshold_FLAT) if threshold_FLAT != "" else 5,
                        min_Q = float(min_Q) if min_Q != "" else None,
                        max_Q = float(max_Q) if max_Q != "" else None,
                        accuracy_range = float(accuracy_range) if accuracy_range != "" else 1,
                        reliability_check_1 = self.reliability_check_1_check_box.isChecked(),
                        reliability_check_2 = self.reliability_check_2_check_box.isChecked(),
                        reliability_check_3 = self.reliability_check_3_check_box.isChecked(),
                        reliability_check_4 = self.reliability_check_4_check_box.isChecked(),
                        tc_check_1 = self.tc_check_1_check_box.isChecked(),
                        tc_check_2 = self.tc_check_2_check_box.isChecked(),
                        robustness_check_1 = self.robustness_check_1_check_box.isChecked(),
                        accuracy_check_1 = self.accuracy_check_1_check_box.isChecked(),
                        accuracy_check_2 = self.accuracy_check_2_check_box.isChecked(),
                        accuracy_check_3 = self.accuracy_check_3_check_box.isChecked())

        else:
            error_dialog = QMessageBox()
            error_dialog.setIcon(QMessageBox.Critical)
            error_dialog.setText("Please Review the Inputs")
            error_dialog.setInformativeText("Additional Information")
            error_dialog.setWindowTitle("Error")
            error_dialog.exec_()
            # Make the popup more descriptive
        sys.exit(app.exec_())


    def cancel_push_button_clicked(self):
        '''
        Exits the GUI
-------------------------------------
        Parameters:
            None
-------------------------------------
        Returns:
            None
        '''
        sys.exit(app.exec_())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = flowmeter()
    sys.exit(app.exec_())