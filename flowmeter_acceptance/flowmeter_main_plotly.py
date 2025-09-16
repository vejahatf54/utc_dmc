import os
import sys
import subprocess
from datetime import datetime
import argparse
import pandas as pd
import csv
import plotly.graph_objects as go
import plotly.express as px
import plotly.figure_factory as ff
from plotly.subplots import make_subplots
import numpy as np
from scipy.stats import norm, probplot, skew, kurtosis, ks_2samp
from scipy import special
import time
from time import strftime
import ctypes
import re


def main(**kwargs):
    '''
Main file through which all checks are conducted
-------------------------------------
    Parameters:
    rtu_file: The rtu file input from the line custodian, used as one of two 
            sources of data to parse through

    csv_tags_file: csv tags input created by the line custodian, used as the
            source of data to analyze

    review_file: The review file input from the line custodian, used as a 
            second source of data to parse through

    csv_file: Name of rtu file converted to a csv as an output

    report_name: Name of the final report, added to the _Report/_final 
            file as an output

    time_start: Time at which the analysis begins

    time_end: Time at which the analysis ends

    threshold_FLAT: Line custodian input FLAT attribute integer of the flowmeter 
            tags (used if available)

    min_Q: Minimum operating flowrate of the line

    max_Q: Maximum operating flowrate of the line

    reliability_check_1 - accuracy_check_4: True or False input based on selected 
            check boxes from the GUI

-------------------------------------
    Returns:
    The complete assessment of all tags selected
'''
    directory()
    Check = argument(kwargs).complete_check()


def directory():
    '''
    Creates all output directories, checking if they have already been created
            or not; creates them if not already there
-------------------------------------
    Parameters:
    None
-------------------------------------
    Returns:
    Directories
    '''
    # Main Directories
    output_data_folder_path = './_Data'
    output_report_folder_path = './_Report'

    # Sub-Directories
    review_folder_path = './_Data/_review'
    rtu_folder_path = './_Data/_rtu'
    final_folder_path = './_Report/_final'
    images_folder_path = './_Report/_images'
    individual_meter_folder_path = './_Report/_individual_meter'

    # Further Image Sub-Directories
    time_difference_folder_path = './_Report/_images/_time_difference'
    meter_rate_folder_path = './_Report/_images/_meter_rate'
    comparison_folder_path = './_Report/_images/_comparison'

    if not os.path.exists(output_data_folder_path):
        os.mkdir(output_data_folder_path)
    if not os.path.exists(output_report_folder_path):
        os.mkdir(output_report_folder_path)
    if not os.path.exists(review_folder_path):
        os.mkdir(review_folder_path)
    if not os.path.exists(rtu_folder_path):
        os.mkdir(rtu_folder_path)
    if not os.path.exists(images_folder_path):
        os.mkdir(images_folder_path)
    if not os.path.exists(individual_meter_folder_path):
        os.mkdir(individual_meter_folder_path)
    if not os.path.exists(final_folder_path):
        os.mkdir(final_folder_path)
    if not os.path.exists(time_difference_folder_path):
        os.mkdir(time_difference_folder_path)
    if not os.path.exists(meter_rate_folder_path):
        os.mkdir(meter_rate_folder_path)
    if not os.path.exists(comparison_folder_path):
        os.mkdir(comparison_folder_path)
    else:
        pass


class argument:

    def __init__(self, arg_dict):
        # Initial attributes from the GUI
        self.rtu_file = arg_dict['rtu_file']
        self.csv_tags_file = arg_dict['csv_tags_file']
        self.review_file = arg_dict['review_file']
        self.csv_file = './_Data/_rtu/{}.csv'.format(arg_dict['csv_file'])
        self.report_name = arg_dict['report_name']
        self.time_start = arg_dict['time_start']
        self.time_end = arg_dict['time_end']
        self.threshold_FLAT = arg_dict['threshold_FLAT']
        self.min_Q = arg_dict['min_Q']
        self.max_Q = arg_dict['max_Q']
        self.accuracy_range = arg_dict['accuracy_range']

        # Additional attributes not initialized in the GUI but created later
        self.dataframe = None
        self.dataframe_report = None
        self.dataframe_tags = None
        self.flow_use = False
        self.flow_LD_tag_name_list = []
        self.temp_LD_tag_name_list = []
        self.pres_LD_tag_name_list = []
        self.temp_SCADA_tag_name_list = []
        self.flow_SCADA_tag_name_list = []
        self.pres_SCADA_tag_name_list = []
        self.LD_name = None
        self.SCADA_name = None
        self.flow_lower_bound_list = []
        self.flow_upper_bound_list = []
        self.temp_lower_bound_list = []
        self.temp_upper_bound_list = []
        self.pres_lower_bound_list = []
        self.pres_upper_bound_list = []
        self.lower_bound_value = None
        self.upper_bound_value = None
        self.dataframe_temporary = None
        self.dataframe_review = None
        self.attribute_list = ['ST', 'FLAT', 'VAL']
        self.time_difference = []
        self.bad_quality = 0
        self.number_oor_values = 0
        self.value = []
        self.time_unix = []
        self.bad_value_index = []
        self.statement_list = []
        self.analog_digital = []
        self.counter = 1
        self.time_start_datetime = datetime.strptime(self.time_start,
                                                     "%y/%m/%d %H:%M:%S")
        self.time_end_datetime = datetime.strptime(self.time_end,
                                                   "%y/%m/%d %H:%M:%S")
        self.time_delta = self.time_end_datetime - self.time_start_datetime

        # Check True or False
        self.reliability_check_1 = arg_dict['reliability_check_1']
        self.reliability_check_2 = arg_dict['reliability_check_2']
        self.reliability_check_3 = arg_dict['reliability_check_3']
        self.reliability_check_4 = arg_dict['reliability_check_4']
        self.tc_check_1 = arg_dict['tc_check_1']
        self.tc_check_2 = arg_dict['tc_check_2']
        self.robustness_check_1 = arg_dict['robustness_check_1']
        self.accuracy_check_1 = arg_dict['accuracy_check_1']
        self.accuracy_check_2 = arg_dict['accuracy_check_2']
        self.accuracy_check_3 = arg_dict['accuracy_check_3']

    def complete_check(self):
        '''
        Called from "main". Uses current time, and initializes several variables
                with data from the user (as input). Calls rtu_to_csv" to write the data to a csv.
                Calls on "main_report" to create the main report; "tag_name_and_list" to
                add all tag names and operating conditions to lists; "write_data" to save
                tag data and write to a csv; "flow_check" for testing all flowrate tags;
                "temperature_check" for testing temperature tags; "pressure_check" for
                testing pressure tags
-------------------------------------
        Parameters:
        self.csv_tags_file: User input csv of all tags to assess
        self.csv_file: data written from "rtu_to_csv"
        self.dataframe: dataframe that reads from csv_file
        self.dataframe_tags: dataframe of csv_tags_file
-------------------------------------
        Returns:
        Creates (from the initialize etc. methods) individual and final
                reports and images of plots and saves them in the premade
                directories
        '''
        now = strftime('%Y-%m-%d_%H-%M')
        self.dataframe_tags = pd.read_csv(self.csv_tags_file)
        Calculation.rtu_to_csv(self)

        try:
            self.dataframe = pd.read_csv(self.csv_file, encoding='utf-8')
        except:
            self.dataframe = pd.read_csv(self.csv_file, encoding='latin-1')

        Calculation.main_report(self, now)
        Calculation.tag_name_and_list(self)
        Calculation.write_data(self, now)

        # Create accuracy flowrate tags csv
        if self.accuracy_check_1 or self.accuracy_check_2 or self.accuracy_check_3:
            flow_csv_filepath = './_Data/_review/{}_flow_csv.csv' \
                .format(self.report_name)
            Calculation.flow_check(self, now, flow_csv_filepath)

        # Create temp tags csv
        if self.tc_check_1 or self.tc_check_2:
            temp_csv_filepath = './_Data/_review/{}_temp_csv.csv' \
                .format(self.report_name)
            Calculation.temperature_check(self, now, temp_csv_filepath)

        # Create pressure tags csv
        if self.tc_check_1 or self.tc_check_2:
            pres_csv_filepath = './_Data/_review/{}_pres_csv.csv' \
                .format(self.report_name)
            Calculation.pressure_check(self, now, pres_csv_filepath)

        # Finalize the report
        Calculation.finalize_report(self, now)

        return True


class Calculation:

    def rtu_to_csv(self):
        '''
        Inputs an RTU data file and converts it to a csv that will be used as
                the data for analysis
-------------------------------------
        Parameters:
        self.rtu_file: The rt
u data file that contains data for all tags, pulled 
                directly from OSI PI
-------------------------------------
        Returns:
        self.csv_file: A csv file that contains the same data as the rtu
        '''
        # RTU file to csv conversion
        # Implementation would depend on the RTU file format
        # For now, we'll assume this is handled externally
        pass

    def main_report(self, now):
        '''
        Creates the main report in csv format with preset column names. The csv
                file populates throughout the program and is finalized in the final
                folder upon completion
-------------------------------------
        Parameters:
        now: String of the current time stamp for report completion
-------------------------------------
        Returns:
        self.dataframe_report: A dataframe that contains the main assessment report
        '''
        column_names = ['Tag Name', 'Reference', 'Analog/Digital', 'Pass/Fail',
                        'Additional Information', 'Check Performed']
        self.dataframe_report = pd.DataFrame(columns=column_names)

    def tag_name_and_list(self):
        '''
        Separates each tag (LD and SCADA) based on tag type (flow, temp, pressure)
                and adds each to respective lists with the designated upper and lower bounds
-------------------------------------
        Parameters:
        self.dataframe_tags: the input csv that contains all tag information
-------------------------------------
        Returns:
        Populates the following lists: flow_LD_tag_name_List, temp_LD_tag_name_list,
                pres_LD_tag_name_list, temp_SCADA_tag_name_list, flow_SCADA_tag_name_list,
                pres_SCADA_tag_name_list, flow_lower_bound_list, flow_upper_bound_list,
                temp_lower_bound_list, temp_upper_bound_list, pres_lower_bound_list,
                pres_upper_bound_list
        '''
        for i in range(0, len(self.dataframe_tags)):
            tag_name = self.dataframe_tags.loc[i, 'LDTagID']

            if 'rate' in tag_name.lower() or 'flow' in tag_name.lower():
                self.flow_LD_tag_name_list.append(tag_name)
                self.flow_SCADA_tag_name_list.append(
                    self.dataframe_tags.loc[i, 'SCADATagID'])
                self.flow_lower_bound_list.append(
                    self.dataframe_tags.loc[i, 'LowerBound'])
                self.flow_upper_bound_list.append(
                    self.dataframe_tags.loc[i, 'UpperBound'])
            elif 'temp' in tag_name.lower() or 'TI' in tag_name:
                self.temp_LD_tag_name_list.append(tag_name)
                self.temp_SCADA_tag_name_list.append(
                    self.dataframe_tags.loc[i, 'SCADATagID'])
                self.temp_lower_bound_list.append(
                    self.dataframe_tags.loc[i, 'LowerBound'])
                self.temp_upper_bound_list.append(
                    self.dataframe_tags.loc[i, 'UpperBound'])
            elif 'pres' in tag_name.lower() or 'PI' in tag_name:
                self.pres_LD_tag_name_list.append(tag_name)
                self.pres_SCADA_tag_name_list.append(
                    self.dataframe_tags.loc[i, 'SCADATagID'])
                self.pres_lower_bound_list.append(
                    self.dataframe_tags.loc[i, 'LowerBound'])
                self.pres_upper_bound_list.append(
                    self.dataframe_tags.loc[i, 'UpperBound'])

    def write_data(self, now):
        '''
        Writes all tag data from the dataframe to csv files based on tag type.
                To be used for the review files for checks
-------------------------------------
        Parameters:
        now: String of the current time stamp
-------------------------------------
        Returns:
        CSV files separated by tag type to be used in flowmeter assessments
        '''
        # Write flow data
        if self.flow_LD_tag_name_list:
            flow_data = []
            for tag in self.flow_LD_tag_name_list:
                if tag in self.dataframe.columns:
                    flow_data.append(self.dataframe[tag])
            if flow_data:
                flow_df = pd.concat(flow_data, axis=1)
                flow_df.to_csv(
                    f'./_Data/_review/{self.report_name}_flow_data_{now}.csv', index=False)

        # Write temperature data
        if self.temp_LD_tag_name_list:
            temp_data = []
            for tag in self.temp_LD_tag_name_list:
                if tag in self.dataframe.columns:
                    temp_data.append(self.dataframe[tag])
            if temp_data:
                temp_df = pd.concat(temp_data, axis=1)
                temp_df.to_csv(
                    f'./_Data/_review/{self.report_name}_temp_data_{now}.csv', index=False)

        # Write pressure data
        if self.pres_LD_tag_name_list:
            pres_data = []
            for tag in self.pres_LD_tag_name_list:
                if tag in self.dataframe.columns:
                    pres_data.append(self.dataframe[tag])
            if pres_data:
                pres_df = pd.concat(pres_data, axis=1)
                pres_df.to_csv(
                    f'./_Data/_review/{self.report_name}_pres_data_{now}.csv', index=False)

    def flow_check(self, now, flow_csv_filepath):
        '''
        Performs all flowrate checks that have been selected by the user
-------------------------------------
        Parameters:
        now: String of current time stamp
        flow_csv_filepath: Path to flow data CSV file
-------------------------------------
        Returns:
        Updates report dataframe with flow check results
        '''
        for i, tag in enumerate(self.flow_LD_tag_name_list):
            if tag in self.dataframe.columns:
                tag_data = self.dataframe[tag].dropna()

                if len(tag_data) > 0:
                    self.LD_name = tag
                    self.SCADA_name = self.flow_SCADA_tag_name_list[i]
                    self.lower_bound_value = self.flow_lower_bound_list[i]
                    self.upper_bound_value = self.flow_upper_bound_list[i]

                    # Perform reliability checks
                    if self.reliability_check_1:
                        Calculation.reliability_1(self, tag_data, now)
                    if self.reliability_check_2:
                        Calculation.reliability_2(self, tag_data, now)
                    if self.reliability_check_3:
                        Calculation.reliability_3(self, tag_data, now)
                    if self.reliability_check_4:
                        Calculation.reliability_4(self, tag_data, now)

                    # Perform accuracy checks
                    if self.accuracy_check_1:
                        Calculation.accuracy_1(self, tag_data, now)
                    if self.accuracy_check_2:
                        Calculation.accuracy_2(self, tag_data, now)
                    if self.accuracy_check_3:
                        Calculation.accuracy_3(self, tag_data, now)

                    # Perform robustness check
                    if self.robustness_check_1:
                        Calculation.robustness_1(self, tag_data, now)

    def temperature_check(self, now, temp_csv_filepath):
        '''
        Performs all temperature checks that have been selected by the user
-------------------------------------
        Parameters:
        now: String of current time stamp
        temp_csv_filepath: Path to temperature data CSV file
-------------------------------------
        Returns:
        Updates report dataframe with temperature check results
        '''
        for i, tag in enumerate(self.temp_LD_tag_name_list):
            if tag in self.dataframe.columns:
                tag_data = self.dataframe[tag].dropna()

                if len(tag_data) > 0:
                    self.LD_name = tag
                    self.SCADA_name = self.temp_SCADA_tag_name_list[i]
                    self.lower_bound_value = self.temp_lower_bound_list[i]
                    self.upper_bound_value = self.temp_upper_bound_list[i]

                    # Perform TC checks
                    if self.tc_check_1:
                        Calculation.tc_1(self, tag_data, now)
                    if self.tc_check_2:
                        Calculation.tc_2(self, tag_data, now)

    def pressure_check(self, now, pres_csv_filepath):
        '''
        Performs all pressure checks that have been selected by the user
-------------------------------------
        Parameters:
        now: String of current time stamp
        pres_csv_filepath: Path to pressure data CSV file
-------------------------------------
        Returns:
        Updates report dataframe with pressure check results
        '''
        for i, tag in enumerate(self.pres_LD_tag_name_list):
            if tag in self.dataframe.columns:
                tag_data = self.dataframe[tag].dropna()

                if len(tag_data) > 0:
                    self.LD_name = tag
                    self.SCADA_name = self.pres_SCADA_tag_name_list[i]
                    self.lower_bound_value = self.pres_lower_bound_list[i]
                    self.upper_bound_value = self.pres_upper_bound_list[i]

                    # Perform TC checks
                    if self.tc_check_1:
                        Calculation.tc_1(self, tag_data, now)
                    if self.tc_check_2:
                        Calculation.tc_2(self, tag_data, now)

    def reliability_1(self, tag_data, now):
        '''
        Reliability Check 1: Data quality assessment
        '''
        # Calculate basic statistics
        mean_val = np.mean(tag_data)
        std_val = np.std(tag_data)
        count_val = len(tag_data)

        # Check for reasonable data quality metrics
        pass_fail = "PASS" if count_val > 100 and std_val > 0 else "FAIL"

        # Add to report
        new_row = {
            'Tag Name': self.LD_name,
            'Reference': self.SCADA_name,
            'Analog/Digital': 'Analog',
            'Pass/Fail': pass_fail,
            'Additional Information': f'Count: {count_val}, Mean: {mean_val:.2f}, Std: {std_val:.2f}',
            'Check Performed': 'Reliability Check 1'
        }
        self.dataframe_report = pd.concat(
            [self.dataframe_report, pd.DataFrame([new_row])], ignore_index=True)

    def reliability_2(self, tag_data, now):
        '''
        Reliability Check 2: Range validation
        '''
        # Check if values are within expected bounds
        in_range = np.sum((tag_data >= self.lower_bound_value)
                          & (tag_data <= self.upper_bound_value))
        total_count = len(tag_data)
        percentage_in_range = (in_range / total_count) * 100

        pass_fail = "PASS" if percentage_in_range >= 95 else "FAIL"

        new_row = {
            'Tag Name': self.LD_name,
            'Reference': self.SCADA_name,
            'Analog/Digital': 'Analog',
            'Pass/Fail': pass_fail,
            'Additional Information': f'{percentage_in_range:.1f}% values in range [{self.lower_bound_value}, {self.upper_bound_value}]',
            'Check Performed': 'Reliability Check 2'
        }
        self.dataframe_report = pd.concat(
            [self.dataframe_report, pd.DataFrame([new_row])], ignore_index=True)

    def reliability_3(self, tag_data, now):
        '''
        Reliability Check 3: Continuity check
        '''
        # Check for data gaps or constant values
        unique_values = len(np.unique(tag_data))
        total_values = len(tag_data)

        # Check for too many repeated values (indicating stuck sensor)
        max_consecutive = 1
        current_consecutive = 1
        for i in range(1, len(tag_data)):
            if tag_data.iloc[i] == tag_data.iloc[i-1]:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 1

        pass_fail = "PASS" if unique_values > total_values * \
            0.1 and max_consecutive < total_values * 0.05 else "FAIL"

        new_row = {
            'Tag Name': self.LD_name,
            'Reference': self.SCADA_name,
            'Analog/Digital': 'Analog',
            'Pass/Fail': pass_fail,
            'Additional Information': f'Unique values: {unique_values}, Max consecutive: {max_consecutive}',
            'Check Performed': 'Reliability Check 3'
        }
        self.dataframe_report = pd.concat(
            [self.dataframe_report, pd.DataFrame([new_row])], ignore_index=True)

    def reliability_4(self, tag_data, now):
        '''
        Reliability Check 4: Statistical distribution check
        '''
        # Perform normality test
        from scipy.stats import normaltest

        try:
            stat, p_value = normaltest(tag_data)
            is_normal = p_value > 0.05

            # Check skewness and kurtosis
            skewness = skew(tag_data)
            kurt = kurtosis(tag_data)

            pass_fail = "PASS" if abs(
                skewness) < 2 and abs(kurt) < 7 else "FAIL"

            new_row = {
                'Tag Name': self.LD_name,
                'Reference': self.SCADA_name,
                'Analog/Digital': 'Analog',
                'Pass/Fail': pass_fail,
                'Additional Information': f'Skewness: {skewness:.2f}, Kurtosis: {kurt:.2f}, Normal: {is_normal}',
                'Check Performed': 'Reliability Check 4'
            }
        except:
            new_row = {
                'Tag Name': self.LD_name,
                'Reference': self.SCADA_name,
                'Analog/Digital': 'Analog',
                'Pass/Fail': 'FAIL',
                'Additional Information': 'Statistical test failed',
                'Check Performed': 'Reliability Check 4'
            }

        self.dataframe_report = pd.concat(
            [self.dataframe_report, pd.DataFrame([new_row])], ignore_index=True)

    def accuracy_1(self, tag_data, now):
        '''
        Accuracy Check 1: Mean value assessment
        '''
        mean_val = np.mean(tag_data)
        expected_range = (self.lower_bound_value + self.upper_bound_value) / 2
        tolerance = (self.upper_bound_value -
                     self.lower_bound_value) * 0.1  # 10% tolerance

        pass_fail = "PASS" if abs(
            mean_val - expected_range) <= tolerance else "FAIL"

        new_row = {
            'Tag Name': self.LD_name,
            'Reference': self.SCADA_name,
            'Analog/Digital': 'Analog',
            'Pass/Fail': pass_fail,
            'Additional Information': f'Mean: {mean_val:.2f}, Expected: {expected_range:.2f}, Tolerance: ±{tolerance:.2f}',
            'Check Performed': 'Accuracy Check 1'
        }
        self.dataframe_report = pd.concat(
            [self.dataframe_report, pd.DataFrame([new_row])], ignore_index=True)

    def accuracy_2(self, tag_data, now):
        '''
        Accuracy Check 2: Precision assessment using time series plot
        '''
        # Create time series plot using Plotly
        timestamps = range(len(tag_data))

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=tag_data,
            mode='lines',
            name=self.LD_name,
            line=dict(color='blue', width=1)
        ))

        # Add bounds
        fig.add_hline(y=self.lower_bound_value, line_dash="dash", line_color="red",
                      annotation_text="Lower Bound")
        fig.add_hline(y=self.upper_bound_value, line_dash="dash", line_color="red",
                      annotation_text="Upper Bound")

        fig.update_layout(
            title=f'Time Series Plot - {self.LD_name}',
            xaxis_title='Time Index',
            yaxis_title='Value',
            width=1200,
            height=600
        )

        # Save plot
        plot_filename = f'./_Report/_images/_meter_rate/Accuracy2_{self.LD_name}_{now}.html'
        fig.write_html(plot_filename)

        # Calculate precision metrics
        std_val = np.std(tag_data)
        coefficient_of_variation = std_val / np.mean(tag_data) * 100

        pass_fail = "PASS" if coefficient_of_variation < 10 else "FAIL"

        new_row = {
            'Tag Name': self.LD_name,
            'Reference': self.SCADA_name,
            'Analog/Digital': 'Analog',
            'Pass/Fail': pass_fail,
            'Additional Information': f'CV: {coefficient_of_variation:.2f}%, Plot: {plot_filename}',
            'Check Performed': 'Accuracy Check 2'
        }
        self.dataframe_report = pd.concat(
            [self.dataframe_report, pd.DataFrame([new_row])], ignore_index=True)

    def accuracy_3(self, tag_data, now):
        '''
        Accuracy Check 3: Comparison with reference using histogram and CDF
        '''
        # Find reference tag data if available
        reference_tag = None
        reference_data = None

        # Look for reference in tags dataframe
        for i, tag in enumerate(self.flow_LD_tag_name_list):
            if tag == self.LD_name:
                try:
                    ref_col = self.dataframe_tags.loc[i, 'Reference_Meter']
                    if ref_col in self.dataframe.columns:
                        reference_tag = ref_col
                        reference_data = self.dataframe[ref_col].dropna()
                        break
                except:
                    pass

        if reference_data is not None and len(reference_data) > 0:
            Calculation.comparison_plot(
                self, reference_tag, reference_data, tag_data, now)

            # Perform statistical comparison
            try:
                ks_stat, ks_p_value = ks_2samp(tag_data, reference_data)
                pass_fail = "PASS" if ks_p_value > 0.05 else "FAIL"
                additional_info = f'KS test p-value: {ks_p_value:.4f}, Reference: {reference_tag}'
            except:
                pass_fail = "FAIL"
                additional_info = f'Statistical comparison failed, Reference: {reference_tag}'
        else:
            pass_fail = "FAIL"
            additional_info = "No reference meter data available"

        new_row = {
            'Tag Name': self.LD_name,
            'Reference': reference_tag or 'None',
            'Analog/Digital': 'Analog',
            'Pass/Fail': pass_fail,
            'Additional Information': additional_info,
            'Check Performed': 'Accuracy Check 3'
        }
        self.dataframe_report = pd.concat(
            [self.dataframe_report, pd.DataFrame([new_row])], ignore_index=True)

    def comparison_plot(self, reference_tag, reference_values, scada_tag_values, now):
        '''
        Creates a histogram plot that compares a tag to a reference one provided
        using Plotly instead of matplotlib
        '''
        # Create subplots
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Histogram Comparison',
                            'Cumulative Distribution Comparison'),
            vertical_spacing=0.12
        )

        # Histogram comparison
        fig.add_trace(
            go.Histogram(
                x=reference_values,
                name=f'{reference_tag} (Reference)',
                opacity=0.7,
                nbinsx=50,
                histnorm='probability density',
                marker_color='green'
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Histogram(
                x=scada_tag_values,
                name=f'{self.LD_name} (Test)',
                opacity=0.7,
                nbinsx=50,
                histnorm='probability density',
                marker_color='blue'
            ),
            row=1, col=1
        )

        # Calculate CDFs
        ref_sorted = np.sort(reference_values)
        test_sorted = np.sort(scada_tag_values)

        ref_cdf = np.arange(1, len(ref_sorted) + 1) / len(ref_sorted)
        test_cdf = np.arange(1, len(test_sorted) + 1) / len(test_sorted)

        # CDF comparison
        fig.add_trace(
            go.Scatter(
                x=ref_sorted,
                y=ref_cdf,
                mode='lines',
                name=f'{reference_tag} CDF',
                line=dict(color='green', dash='dash'),
                showlegend=False
            ),
            row=2, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=test_sorted,
                y=test_cdf,
                mode='lines',
                name=f'{self.LD_name} CDF',
                line=dict(color='blue', dash='dash'),
                showlegend=False
            ),
            row=2, col=1
        )

        # Update layout
        fig.update_layout(
            title=f'Accuracy Check 3: {self.LD_name} vs {reference_tag}',
            height=800,
            width=1200,
            showlegend=True
        )

        fig.update_xaxes(title_text="Value", row=1, col=1)
        fig.update_yaxes(title_text="Probability Density", row=1, col=1)
        fig.update_xaxes(title_text="Value", row=2, col=1)
        fig.update_yaxes(title_text="Cumulative Probability", row=2, col=1)

        # Save plot
        plot_filename = f'./_Report/_images/_comparison/Accuracy3_{self.LD_name}_{now}.html'
        fig.write_html(plot_filename)

    def robustness_1(self, tag_data, now):
        '''
        Robustness Check 1: Signal stability analysis with Plotly plotting
        '''
        pass_fail = Calculation.signal_plot(self, tag_data, now)

        # Calculate signal stability metrics
        rolling_std = pd.Series(tag_data).rolling(
            window=min(100, len(tag_data)//10)).std()
        std_variation = np.std(rolling_std.dropna())

        if pass_fail == "PASS":
            additional_info = f'Signal stable, Std variation: {std_variation:.4f}'
        else:
            additional_info = f'Signal unstable, Std variation: {std_variation:.4f}'

        new_row = {
            'Tag Name': self.LD_name,
            'Reference': self.SCADA_name,
            'Analog/Digital': 'Analog',
            'Pass/Fail': pass_fail,
            'Additional Information': additional_info,
            'Check Performed': 'Robustness Check 1'
        }
        self.dataframe_report = pd.concat(
            [self.dataframe_report, pd.DataFrame([new_row])], ignore_index=True)

    def signal_plot(self, tag_data, now):
        '''
        Creates signal stability plot using Plotly
        '''
        timestamps = range(len(tag_data))

        # Calculate rolling statistics
        window_size = min(100, len(tag_data)//10)
        rolling_mean = pd.Series(tag_data).rolling(window=window_size).mean()
        rolling_std = pd.Series(tag_data).rolling(window=window_size).std()

        # Create subplots
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=('Raw Signal', 'Rolling Mean',
                            'Rolling Standard Deviation'),
            vertical_spacing=0.08
        )

        # Raw signal
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=tag_data,
                mode='lines',
                name='Raw Signal',
                line=dict(color='blue', width=1)
            ),
            row=1, col=1
        )

        # Rolling mean
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=rolling_mean,
                mode='lines',
                name='Rolling Mean',
                line=dict(color='red', width=2),
                showlegend=False
            ),
            row=2, col=1
        )

        # Rolling std
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=rolling_std,
                mode='lines',
                name='Rolling Std',
                line=dict(color='green', width=2),
                showlegend=False
            ),
            row=3, col=1
        )

        fig.update_layout(
            title=f'Robustness Analysis - {self.LD_name}',
            height=900,
            width=1200,
            showlegend=True
        )

        fig.update_xaxes(title_text="Time Index", row=3, col=1)
        fig.update_yaxes(title_text="Value", row=1, col=1)
        fig.update_yaxes(title_text="Mean", row=2, col=1)
        fig.update_yaxes(title_text="Std Dev", row=3, col=1)

        # Save plot
        plot_filename = f'./_Report/_images/_meter_rate/Robustness1_{self.LD_name}_{now}.html'
        fig.write_html(plot_filename)

        # Determine pass/fail based on signal stability
        std_variation = np.std(rolling_std.dropna())
        mean_std = np.mean(rolling_std.dropna())

        # Signal is stable if rolling std doesn't vary too much
        stability_ratio = std_variation / \
            mean_std if mean_std > 0 else float('inf')

        return "PASS" if stability_ratio < 0.5 else "FAIL"

    def tc_1(self, tag_data, now):
        '''
        TC Check 1: Temperature compensation check
        '''
        # Basic temperature range validation
        expected_temp_range = [0, 100]  # Typical process temperature range

        in_range_count = np.sum((tag_data >= expected_temp_range[0]) & (
            tag_data <= expected_temp_range[1]))
        percentage_in_range = (in_range_count / len(tag_data)) * 100

        pass_fail = "PASS" if percentage_in_range >= 90 else "FAIL"

        new_row = {
            'Tag Name': self.LD_name,
            'Reference': self.SCADA_name,
            'Analog/Digital': 'Analog',
            'Pass/Fail': pass_fail,
            'Additional Information': f'{percentage_in_range:.1f}% in expected range {expected_temp_range}',
            'Check Performed': 'TC Check 1'
        }
        self.dataframe_report = pd.concat(
            [self.dataframe_report, pd.DataFrame([new_row])], ignore_index=True)

    def tc_2(self, tag_data, now):
        '''
        TC Check 2: Temperature stability check
        '''
        # Check temperature stability over time
        temp_range = np.max(tag_data) - np.min(tag_data)
        temp_std = np.std(tag_data)

        pass_fail = "PASS" if temp_range < 20 and temp_std < 5 else "FAIL"

        new_row = {
            'Tag Name': self.LD_name,
            'Reference': self.SCADA_name,
            'Analog/Digital': 'Analog',
            'Pass/Fail': pass_fail,
            'Additional Information': f'Range: {temp_range:.2f}°C, Std: {temp_std:.2f}°C',
            'Check Performed': 'TC Check 2'
        }
        self.dataframe_report = pd.concat(
            [self.dataframe_report, pd.DataFrame([new_row])], ignore_index=True)

    def finalize_report(self, now):
        '''
        Finalizes and saves the main report
        '''
        final_report_path = f'./_Report/_final/{self.report_name}_final_report_{now}.csv'
        self.dataframe_report.to_csv(final_report_path, index=False)

        # Create summary statistics
        total_checks = len(self.dataframe_report)
        passed_checks = len(
            self.dataframe_report[self.dataframe_report['Pass/Fail'] == 'PASS'])
        pass_rate = (passed_checks / total_checks *
                     100) if total_checks > 0 else 0

        summary = {
            'Total Checks': total_checks,
            'Passed Checks': passed_checks,
            'Failed Checks': total_checks - passed_checks,
            'Pass Rate': f'{pass_rate:.1f}%',
            'Report Generated': now
        }

        summary_df = pd.DataFrame([summary])
        summary_path = f'./_Report/_final/{self.report_name}_summary_{now}.csv'
        summary_df.to_csv(summary_path, index=False)

        return final_report_path, summary_path
