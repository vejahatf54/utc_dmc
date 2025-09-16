import os
import sys
import subprocess
from datetime import datetime
import argparse
import pandas as pd
import csv
import matplotlib as mpl
import matplotlib.pyplot as plt
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
		self.time_start_datetime = datetime.strptime(self.time_start, \
			"%y/%m/%d %H:%M:%S")
		self.time_end_datetime = datetime.strptime(self.time_end, \
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
			self.dataframe = pd.read_csv(self.csv_file)
		except:
			ctypes.windll.user32.MessageBoxW(0, "Please review time input", "Error \
				in the Start and/or End Time", 1)
		self.dataframe_tags['LDTagID'] = self.dataframe_tags['LDTagID'] \
			.str.upper()
		self.dataframe_tags['SCADATagID'] = self.dataframe_tags['SCADATagID'] \
			.str.upper()

		argument.main_report(self)
		argument.tag_name_and_list(self)
		argument.write_data(self)
		argument.flow_check(self, now)
		argument.temperature_check(self, now)
		argument.pressure_check(self, now)

	def write_data(self):
		'''
		Writes data per tag in 'LDTagID', to a csv and to a dataframe
-------------------------------------
		Parameters:
		self.dataframe_tags: list of all tags in the 'csv_tags" file
		self.dataframe_temporary: holds tag data temporarily during assessment
-------------------------------------
		Returns:
		A csv of all data from the given time period for a tag
		'''
		for index in range(len(self.dataframe_tags['LDTagID'])):
			self.dataframe_temporary = self.dataframe.loc[self.dataframe['ident'] \
				== self.dataframe_tags['LDTagID'][index]]
			self.dataframe_temporary.to_csv('./_Data/_rtu/{}.csv'.format( \
				self.dataframe_tags['LDTagID'][index]) ,index=False)

	def main_report(self):
		'''
		Creates the main report dataframe
-------------------------------------
		Parameters:
		self.dataframe_report: report dataframe that is written to per tag
-------------------------------------
		Returns:
		Newly created dataframe for the report
		'''
		self.dataframe_report = pd.DataFrame(
		columns=['TagID', 
		'Check 1.1',
		'Check 1.2',
		'Check 1.3',
		'Check 1.4',
		'Check 2.1 (Max)', 
		'Check 2.1 (Mean)',
		'Check 2.2',
		'Check 3.1',
		'Check 3.2',
		'Check 3.3'])

	def tag_name_and_list(self):
		'''
		The method uses 3 regular expressions, to isolate the flow tags, 
			the pressure, and the temperature. Each tag of each type is added to
			a seperate list. Similar process is used to obrain the lower and
			upper bounds of each instrument
-------------------------------------
		Parameters:
		self.dataframe_tags: list of all tags in the 'csv_tags" file
		self.flow_SCADA_tag_name_list: List of flowrate SCADA ID tags
		self.temp_SCADA_tag_name_list: List of temperature SCADA ID tags
		self.pres_SCADA_tag_name_list: List of pressure SCADA ID tags
-------------------------------------
		Returns:
		self.flow_LD_tag_name_list: List of flowrate LD ID tags
		self.flow_upper_bound_list: List of flowrate upper bounds
		self.flow_lower_bound_list: List of flowrate lower bounds
		self.temp_LD_tag_name_list: List of temperature LD ID tags
		self.temp_lower_bound_list: List of temperature upper bounds
		self.temp_upper_bound_list: List of temperature lower bounds
		self.pres_LD_tag_name_list: List of pressure LD ID tags
		self.pres_lower_bound_list: List of pressure upper bounds
		self.pres_upper_bound_list: List of pressure lower bounds
		'''
		rT = re.compile(".*_T_*")
		rP = re.compile(".*_P_*")
		rFlow = re.compile("(?:.*_FLOW_.*A*|.*_QSO_.*A*)")

		# Compiling all Q tags
		self.flow_SCADA_tag_name_list = list(filter(rFlow.match, \
			self.dataframe_tags['SCADATagID']))
		self.flow_LD_tag_name_list = self.dataframe_tags['LDTagID'].loc[self.dataframe_tags \
			['SCADATagID'].isin(self.flow_SCADA_tag_name_list)].to_list()
		self.flow_upper_bound_list = self.dataframe_tags['UpperBound'].loc[self.dataframe_tags \
			['SCADATagID'].isin(self.flow_SCADA_tag_name_list)].to_list()
		self.flow_lower_bound_list = self.dataframe_tags['LowerBound'].loc[self.dataframe_tags \
			['SCADATagID'].isin(self.flow_SCADA_tag_name_list)].to_list()

		# Compiling all T tags
		self.temp_SCADA_tag_name_list = list(filter(rT.match, self.dataframe_tags \
			['SCADATagID']))
		self.temp_LD_tag_name_list = self.dataframe_tags['LDTagID'].loc[self.dataframe_tags \
			['SCADATagID'].isin(self.temp_SCADA_tag_name_list)].to_list()
		self.temp_lower_bound_list = self.dataframe_tags['LowerBound'].loc[self.dataframe_tags \
			['SCADATagID'].isin(self.temp_SCADA_tag_name_list)].to_list()
		self.temp_upper_bound_list = self.dataframe_tags['UpperBound'].loc[self.dataframe_tags \
			['SCADATagID'].isin(self.temp_SCADA_tag_name_list)].to_list()

		# Compiling all P tags
		self.pres_SCADA_tag_name_list = list(filter(rP.match, self.dataframe_tags \
			['SCADATagID']))
		self.pres_LD_tag_name_list = self.dataframe_tags['LDTagID'].loc[self.dataframe_tags \
			['SCADATagID'].isin(self.pres_SCADA_tag_name_list)].to_list()
		self.pres_lower_bound_list = self.dataframe_tags['LowerBound'].loc[self.dataframe_tags \
			['SCADATagID'].isin(self.pres_SCADA_tag_name_list)].to_list()
		self.pres_upper_bound_list = self.dataframe_tags['UpperBound'].loc[self.dataframe_tags \
			['SCADATagID'].isin(self.pres_SCADA_tag_name_list)].to_list()

	def flow_check(self, now):
		'''
		Completes assessment for all flowrate tags; uses the variables "string",
			"rAnalog", and "rAnalog_list" to locate and compile the digital and
			analog tags for a given set of tags, using a series of regular
			expressions.
-------------------------------------
		Parameters:
		now: Current date and time
		self.flow_use: True or False if assessing a flowmeter tag
		self.flow_LD_tag_name_list: List of flowrate LD ID tags
		self.flow_SCADA_tag_name_list: List of flowrate SCADA ID tags
		self.LD_name: LD Tag ID
		self.SCADA_name: SCADA Tag ID
		self.analog_digital: Holds two tags, analog and digital for the
			same location
		self.dataframe_tags: List of all tags in the 'csv_tags" file
		self.counter: Counter used to indicate position in the final report
		self.lower_bound_value: Lower bound
		self.upper_bound_value: Upper bound
		self.flow_lower_bound_list: List of flowrate lower bounds
		self.flow_upper_bound_list: List of flowrate upper bounds
-------------------------------------
		Returns:
		Results for flowrate tags
		'''
		for index in range(len(self.flow_LD_tag_name_list)):
			self.flow_use = True
			self.LD_name = self.flow_LD_tag_name_list[index].upper()
			self.SCADA_name = self.flow_SCADA_tag_name_list[index].upper()
			string = self.LD_name.replace('DFR', 'AFR') if 'DFR' in \
				self.LD_name else self.LD_name.replace('AFR', '')
			rAnalog = re.compile("(?:.*{}.*A.*|.*{}.*.|{})".format(string, \
				string, string))
			rAnalog_list = list(filter(rAnalog.match, self.dataframe_tags['LDTagID']))
			if len(rAnalog_list) == 2:
				self.analog_digital = rAnalog_list
			self.lower_bound_value = self.flow_lower_bound_list[index]
			self.upper_bound_value = self.flow_upper_bound_list[index]
			individualCheck = Calculation.initialize(self, now)
			del self.analog_digital[:]
			self.counter += 1
		self.flow_use = False
	
	def temperature_check(self, now):
		'''
		Completes assessment for all temperature tags
-------------------------------------
		Parameters:
		now: Current date and time
		self.temp_LD_tag_name_list: List of flowrate LD ID tags
		self.temp_SCADA_tag_name_list: List of flowrate SCADA ID tags
		self.LD_name: LD Tag ID
		self.SCADA_name: SCADA Tag ID
		self.counter: Counter used to indicate position in the final report
		self.lower_bound_value: Lower bound
		self.upper_bound_value: Upper bound
		self.temp_lower_bound_list: List of temperature lower bounds
		self.temp_upper_bound_list: List of temperature upper bounds
-------------------------------------
		Returns:
		Results for temperature tags
		'''
		for index in range(len(self.temp_LD_tag_name_list)):
			self.LD_name = self.temp_LD_tag_name_list[index].upper()
			self.SCADA_name = self.temp_SCADA_tag_name_list[index].upper()
			self.lower_bound_value = self.temp_lower_bound_list[index]
			self.upper_bound_value = self.temp_upper_bound_list[index]
			individualCheck = Calculation.initialize(self, now)
			self.counter += 1

	def pressure_check(self, now):
		'''
		Completes assessment for all pressure tags
-------------------------------------
		Parameters:
		now: Current date and time
		self.pres_LD_tag_name_list: List of pressure LD ID tags
		self.pres_SCADA_tag_name_list: List of pressure SCADA ID tags
		self.LD_name: LD Tag ID
		self.SCADA_name: SCADA Tag ID
		self.counter: Counter used to indicate position in the final report
		self.lower_bound_value: Lower bound
		self.upper_bound_value: Upper bound
		self.pres_lower_bound_list: List of pressure lower bounds
		self.pres_upper_bound_list: List of pressure upper bounds
-------------------------------------
		Returns:
		Results for pressure tags
		'''
		for index in range(len(self.pres_LD_tag_name_list)):
			self.LD_name = self.pres_LD_tag_name_list[index].upper()
			self.SCADA_name = self.pres_SCADA_tag_name_list[index].upper()
			self.lower_bound_value = self.pres_lower_bound_list[index]
			self.upper_bound_value = self.pres_upper_bound_list[index]
			individualCheck = Calculation.initialize(self, now)
			self.counter += 1

class Calculation(argument):

	def __init__(self, arg_dict):
		super().__init__(arg_dict)

	def initialize(self, now):
		'''
		Method is called to initialize variables for one single tag; the method
			is called for each tag from the for loop in "complete_check".
			All the checks are called from here
-------------------------------------
		Parameters:
		now: Current date and time
		self.dataframe_report: Report dataframe that is written to per tag
		self.dataframe_temporary: Holds tag data temporarily during assessment
-------------------------------------
		Returns:
		Individual reports and images
		'''
		self.dataframe_temporary = self.dataframe.loc[self.dataframe['ident'] \
			== self.LD_name]

		self.dataframe_report.at[self.counter, 'TagID'] = self.LD_name
		scada_name = self.SCADA_name
		Calculation.review(self, scada_name)
		try:
			Calculation.reliability(self, now)
		except:
			ctypes.windll.user32.MessageBoxW(0, "Please review inputs", "Error \
				in the Reliability Section", 1)
		try:
			Calculation.timeliness_and_completeness(self, now)
		except:
			ctypes.windll.user32.MessageBoxW(0, "Please review inputs", "Error \
				in the Timeliness and Completeness Section", 1)
		try:
			Calculation.accuracy(self, now)
		except:
			ctypes.windll.user32.MessageBoxW(0, "Please review inputs", "Error \
				in the Accuracy Section", 1)
		try:
			Calculation.robustness(self, now)
		except:
			ctypes.windll.user32.MessageBoxW(0, "Please review inputs", "Error \
				in the Robustness Section", 1)
		Calculation.create_report(self, now)

	def rtu_to_csv(self):
		'''
		Calls on drtutocsv through cmd, to read/write the rtu data file
-------------------------------------
		Parameters:
		self.dataframe_tags: list of all tags in the 'csv_tags" file
		self.rtu_file: User input rtu file
		self.csv_file: User input csv file
		self.time_start: Time at which the analysis begins
		self.time_end: Time at which the analysis ends
-------------------------------------
		Returns:
		CSV of all data from the rtu data file, for the selected timeframe
		'''
		rtu_tag_list = self.dataframe_tags['LDTagID'].to_list()
		deliminator = '|'
		expression_to_search = deliminator.join(rtu_tag_list).upper()
		os.system('drtutocsv.py "{}" "{}" -s "{}" -e "{}" -f "{}"'.format(self.rtu_file, \
			self.csv_file, self.time_start, self.time_end, expression_to_search))

	def review(self, name):
		'''
		Copy's data from the review file to csv
-------------------------------------
		Parameters:
		name: SCADA ID
		self.attribute_list: List of review file attributes
		self.review_file: User input review file
		self.time_start: Time at which the analysis begins
		self.time_end: Time at which the analysis ends
-------------------------------------
		Returns:
		CSV for each tag called
		self.dataframe_review: Uses the dataframe created using the review file
			for the tag being assessed
		'''
		name_status = "{}:{}".format(name, self.attribute_list[0])
		name_FLAT = "{}:{}".format(name, self.attribute_list[1])
		name_val = "{}:{}".format(name, self.attribute_list[2])
		review_file_path = "./_Data/_review/{}.csv".format(name)
		try:
			output = subprocess.check_output('dreview.exe "{}" -MATCH ({}, {}, {}) \
				-TBEGIN "{}" -TEND "{}" '.format(self.review_file, name_status, name_FLAT, name_val, \
				self.time_start, self.time_end), shell=True, text=True)
		except:
			output = subprocess.check_output('dreview.exe "{}" -MATCH ({}, {}) \
				-TBEGIN "{}" -TEND "{}" '.format(self.review_file, name_status, name_val, \
				self.time_start, self.time_end), shell=True, text=True)
		formated_output = output.splitlines()
		del formated_output[1]
		with open(review_file_path, "w") as written_file:
			for line in formated_output:
				written_file.write(line)
				written_file.write("\n")
		self.dataframe_review = pd.read_csv(review_file_path)

	def reliability(self, now):
		'''
		Completes all reliability checks, calls on the "reliability_check_1_function",
			"reliability_check_2_function", "reliability_check_3_function", and
			"reliability_check_4_function" functions
-------------------------------------
		Parameters:
		now: Current date and time
		self.flow_use: True or False if assessing a flowmeter tag
		self.value: List of values from the rtu tag file
		self.dataframe_temporary: Holds the data for the current tag in analysis
		self.bad_quality: Number of tag instances not considered "GOOD" in rtu
		self.num_oor_values: values outside of the lower or upper bound of
			values provided in the "csv_tags" file
		self.time_unix: List of rtu Unix times
-------------------------------------
		Returns:
		self.statement_list: List of statements written per check
		'''
		self.value = self.dataframe_temporary['value'].to_list()

		if self.flow_use:
			s2 = Calculation.reliability_check_2_function(self)
		else:
			s2 = "Reliability Check 2: N/A"
			self.dataframe_report.at[self.counter, 'Check 1.2'] = 'N/A'

		for second_index in range(len(self.dataframe_temporary) - 1):

			self.time_unix.append(self.dataframe_temporary.iloc[second_index, 1])
			if self.dataframe_temporary.iloc[second_index, -1] != "GOOD":
				self.bad_quality += 1

			if (self.value[second_index] >= self.lower_bound_value) and \
				(self.value[second_index] <= self.upper_bound_value):
				self.number_oor_values += 0
			else:
				self.number_oor_values += 1

		s1 = Calculation.reliability_check_1_function(self)
		s3 = Calculation.reliability_check_3_function(self)
		s4 = Calculation.reliability_check_4_function(self)
		
		self.statement_list.extend([s1, s2, s3, s4])

	def reliability_check_1_function(self):
		'''
		First uses the start and end times to determine if the time period
			selected is over 12h. If over 12h, calls on "hour_check". Else,
			uses the first hour. Either path leads to using "unit_check"
-------------------------------------	
		Parameters:
		self.time_delta: time difference between start and end time
		self.dataframe_temporary: Holds the data for the current tag in analysis
		self.num_oor_values: values outside of the lower or upper bound of
			values provided in the "csv_tags" file
-------------------------------------
		Returns:
		s1: Statement on Reliability
		'''
		if self.reliability_check_1:
			s1 = 'Reliability Check 1: Number of values in provided rtu \
file that are Out of Range: {}'.format(self.number_oor_values)
			self.dataframe_report.at[self.counter, 'Check 1.1'] = self.number_oor_values
		else:
			s1 = "Reliability Check 1: Not Selected"
		return s1

	def reliability_check_2_function(self):
		'''
		Checks if the time difference between the start and end is over 12h,
			if so, calls on "hour_check" to locate an hour of data above min
			flowrate, then call "unit_check". If below 12h, calls "unit_check" 
			directly.
-------------------------------------	
		Parameters:
		self.time_delta: time difference between start and end time
		self.dataframe_temporary: Holds the data for the current tag in analysis
-------------------------------------
		Returns:
		result from "unit_check" function			
		'''
		try:
			if int((self.time_delta.total_seconds())/3600) > 12:
				df = self.dataframe_temporary
				list_1_hour_above_min = Calculation.hour_check(self, df)
				return Calculation.unit_check(self, list_1_hour_above_min)
			else:
				list_of_steady_values = self.dataframe_temporary['value'].to_list()
				return Calculation.unit_check(self, list_of_steady_values)
		except:
			return 'No Steady State Section Available'

	def hour_check(self, df):
		'''
		Locates the first index at which the "value" is above the minimum
			flowrate. When located, checks the first hour at that time to
			determine if the flowrate is between the minimum and maximum
			operating conditions. If not, it checks the next hour. If no
			time period is found, it returns None
-------------------------------------	
		Parameters:
		self.min_Q: Minimum flowrate input from user
		df: dataframe from self.dataframe_temporary, which can be edited to
			remove 1h of data if a period of 1h is not found to be above the
			minimum operating flowrate
-------------------------------------
		Returns:
		list of 1 hour of data above the minimum flowrate			
		'''
		try:
			first_flow_index = df[df['value'] > self.min_Q].first_valid_index()
			time_at_first_flow = df['rtime'][first_flow_index]
			dataframe_1_hour = df[(df['rtime'] >= time_at_first_flow) & 
				(df['rtime'] <= time_at_first_flow + 3600)]
			if (dataframe_1_hour['value'] > self.min_Q).all() == True:
				return list(dataframe_1_hour['value'])
			else:
				df = pd.concat([df, dataframe_1_hour]).drop_duplicates(keep=False)
				return Calculation.hour_check(self, df)
		except:
			return None

	def hour_check_review(self, df, scada_id_name):
		'''
		Similar to "hour_check" except works on review file
-------------------------------------	
		Parameters:
		self.min_Q: Minimum flowrate input from user
		scada_id_name: SCADA ID
		df: dataframe from self.dataframe_temporary, which can be edited to
			remove 1h of data if a period of 1h is not found to be above the
			minimum operating flowrate
-------------------------------------
		Returns:
		list of 1 hour of data above the minimum flowrate			
		'''
		try:
			df['TIME'] = pd.to_datetime(df['TIME'])
			first_flow_index_review = df[df[' {}:VAL'.format(scada_id_name)] >
				self.min_Q].first_valid_index()
			time_at_first_flow_review = df['TIME'][first_flow_index_review]
			second_time_index_review = time_at_first_flow_review + pd.Timedelta(hours=1)
			dataframe_1_hour_review = df[(df['TIME'] >= time_at_first_flow_review) &
				(df['TIME'] <= second_time_index_review)]
			if (dataframe_1_hour_review[' {}:VAL'.format(scada_id_name)] > 
				self.min_Q).first_valid_index():
				return list(dataframe_1_hour_review[' {}:VAL'.format(scada_id_name)])
			else:
				df = pd.concat([df, dataframe_1_hour_review]).drop_duplicates(keep=False)
				return Calculation.hour_check_review(self, df, scada_id_name)
		except:
			return None

	def unit_check(self, list_of_values):
		'''
		Takes a list of values (hour of data) and assess if all values are
			in m3/h or barrels/h. If barrels, it converts to m3/h
-------------------------------------
		Parameters:
		list_of_values: list of flowrate values used when assessing units
		self.reliability_check_2: True or False value for check 2 reliability
		self.dataframe_report: report dataframe that is written to per tag
		self.counter: Counter used to indicate position in the final report
		self.value: List of values from the rtu tag file
-------------------------------------
		Returns:
		s2: Statement on Reliability
		'''
		wrong_unit_instance = 0
		if self.reliability_check_2:
			for index in range(len(list_of_values)):
				if list_of_values[index] >= 0.8*self.min_Q and \
					list_of_values[index] <= 1.2*self.max_Q: # Keep note of truncation errors
					pass
				else:
					wrong_unit_instance += 1
					self.value[index] = list_of_values[index]/6.2898
			if wrong_unit_instance > 0:
				s2 = "Reliability Check 2: Some units appeared in barrels/hr, and were converted to m3/hr"
				self.dataframe_report.at[self.counter, 'Check 1.2'] = 'Some values in b/hr'
			else:
				s2 = "Reliability Check 2: Units are all in m3/hr"
				self.dataframe_report.at[self.counter, 'Check 1.2'] = 'values in m3/h'
		else:
			s2 = 'Reliability Check 2: Not Selected'
			self.dataframe_report.at[self.counter, 'Check 1.2'] = 'N/A'
		return s2

	def reliability_check_3_function(self):
		'''
		Using the "bad_quality" variable, function assesses check 3 Reliability
-------------------------------------
		Parameters:
		self.bad_quality: Number of tag instances not considered "GOOD" in rtu
		self.reliability_check_3: True or False value for check 3 reliability
		self.dataframe_report: report dataframe that is written to per tag
		self.counter: Counter used to indicate position in the final report
-------------------------------------
		Returns:
		s3: Statement on Reliability
		'''
		if self.bad_quality == 0:
			if self.reliability_check_3:
				s3 = 'Reliability Check 3: Quality for tag {} is all GOOD' \
					.format(self.LD_name)
				self.dataframe_report.at[self.counter, 'Check 1.3'] = "GOOD"
			else:
				s3 = "Reliability Check 3: Not Selected"
		else:
			if self.reliability_check_3:
				s3 = 'Reliability Check 3: BAD Quality present with {} \
number of instances'.format(self.bad_quality)
				self.dataframe_report.at[self.counter, 'Check 1.3'] = "BAD"
			else:
				s3 = "Reliability Check 3: Not Selected"
		return s3

	def reliability_check_4_function(self):
		'''
		Uses the review file to assess if the tag is "GOOD"/1 or not
-------------------------------------
		Parameters:
		self.dataframe_review: Uses the dataframe created using the review file
			for the tag being assessed
		self.attribute_list: list of review file attributes
		self.reliability_check_4: True or False value for check 4 reliability
		self.dataframe_report: report dataframe that is written to per tag
		self.counter: Counter used to indicate position in the final report
-------------------------------------
		Returns:
		s4: Statement on Reliability
		'''
		if self.reliability_check_4:
			review_st = (self.dataframe_review[' {}:{}'.format(self.SCADA_name, \
				self.attribute_list[0])] == 1).all()
			if review_st:
				self.dataframe_report.at[self.counter, 'Check 1.4'] = "GOOD"
				s4 = 'Reliability Check 4: Values appear GOOD in the review file'
			else:
				self.dataframe_report.at[self.counter, 'Check 1.4'] = "BAD" 
				s4 = 'Reliability Check 4: Some values appear BAD in the \
review file - Requires further investigation from the LC'
		else:
			s4 = "Reliability Check 4: Not Selected"
		return s4

	def timeliness_and_completeness(self, now):
		'''
		Completes all timeliness and completeness checks; calls on "timeliness_check_2"
			function.
-------------------------------------
		Parameters:
		self.dataframe_temporary: Holds the data for the current tag in analysis
		self.time_difference: List of the time differences between two tag
			instances
		self.dataframe_report: report dataframe that is written to per tag
-------------------------------------
		Returns:
		self.statement_list: List of statements written per check
		'''
		for k in range(len(self.dataframe_temporary) - 1):
			x = self.dataframe_temporary.iloc[k, 1]
			y = self.dataframe_temporary.iloc[k + 1, 1]
			self.time_difference.append(y - x)

		if self.tc_check_1:
			s5 = 'Timeliness and Completeness Check 1: Maximum time difference \
is {}s for {}'.format(max(self.time_difference), self.LD_name)
			s6 = 'Timeliness and Completeness Check 1: Mean time different is \
{}s for {}'.format(round(np.mean(self.time_difference), 2), self.LD_name)
			self.dataframe_report.at[self.counter, 'Check 2.1 (Max)'] = max(self.time_difference)
			self.dataframe_report.at[self.counter, 'Check 2.1 (Mean)'] = \
				round(np.mean(self.time_difference), 2)
			Calculation.time_plot(self, now)
		else:
			s5 = "Timeliness and Completeness Check 1: Not Selected"
			s6 = "Timeliness and Completeness Check 1: Not Selected"
			self.dataframe_report.at[self.counter, 'Check 2.1 (Max)'] = 'N/A'
			self.dataframe_report.at[self.counter, 'Check 2.1 (Mean)'] = 'N/A'
		
		s7 = Calculation.timeliness_check_2(self)
		
		self.statement_list.extend([s5, s6, s7])

	def timeliness_check_2(self):
		'''
		Completes the second Timeliness and Completeness check; uses the review
			file data to assess if the FLAT attribute of the tag is below or at
			the Threshold, by removing any instance of a shutdown period, to 
			avoid FLAT increasing in that state.
-------------------------------------
		Parameters:
		self.tc_check_2: True or False value for check 2 timeliness and completeness
		self.dataframe_review: Uses the dataframe created using the review file
			for the tag being assessed
		self.SCADA_name: SCADA ID
		self.counter: Counter used to indicate position in the final report
		self.dataframe_report: Report dataframe that is written to per tag
		self.attribute_list: List of review file attributes
		self.threshold_FLAT: FLAT Threshold as provided by LC (or default to 5 min)
-------------------------------------
		Returns:
		s7: Statement on Timeliness and Completeness
		'''
		if self.tc_check_2:
			try:
				dataframe_not_shutdown = self.dataframe_review[self.dataframe_review \
					[' {}:{}'.format(self.SCADA_name, self.attribute_list[2])] > 1]
				review_flat = (dataframe_not_shutdown[' {}:{}'.format(self.SCADA_name, \
					self.attribute_list[1])] <= self.threshold_FLAT).all()
				if review_flat:
					self.dataframe_report.at[self.counter, 'Check 2.2'] = "GOOD"
					s7 = 'Timeliness and Completeness Check 2: GOOD'
				else:
					self.dataframe_report.at[self.counter, 'Check 2.2'] = "BAD"
					s7 = 'Timeliness and Completeness Check 2: BAD'
			except:
				s7 = 'Timeliness and Completeness Check 2: FLAT Attribute Not Accessible'
				self.dataframe_report.at[self.counter, 'Check 2.2'] = "FLAT Not Available"
		else:
			s7 = "Timeliness and Completeness Check 2: Not Selected"
			self.dataframe_report.at[self.counter, 'Check 2.2'] = "N/A"
		return s7

	def accuracy(self, now):
		'''
		Completes all Accuracy checks, calls on several functions to complete
			all checks including "mean_squared_error", "signal_noise_ratio",
			and "reference_comparison"
-------------------------------------
		Parameters:
		self.accuracy_check_1: True or False for Accuracy Check 1
		self.accuracy_check_2: True or False for Accuracy Check 2
		self.accuracy_check_3: True or False for Accuracy Check 3
		self.analog_digital: Holds two tags, analog and digital for the
			same location
		self.flow_use: True or False if assessing a flowmeter tag
		self.dataframe_report: Report dataframe that is written to per tag
		self.counter: Counter used to indicate position in the final report
-------------------------------------
		Returns:
		self.statement_list: List of statements written per check
		'''
		if self.accuracy_check_1 and len(self.analog_digital) == 2 and self.flow_use:
			mse_value, nominal_flowrate = Calculation.mean_squared_error(self)
			self.dataframe_report.at[self.counter, 'Check 3.1'] = "{}".format \
				(round(mse_value, 3))
			s8 = 'Accuracy Check 1: mse available as {}, with average flowrate {}' \
				.format(round(mse_value, 2), round(nominal_flowrate, 2))
		else:
			self.dataframe_report.at[self.counter, 'Check 3.1'] = "N/A"
			s8 = 'Accuracy Check 1: N/A'

		if self.accuracy_check_2 and self.flow_use and \
			int((self.time_delta.total_seconds())/3600) > 2:
			df = self.dataframe_temporary
			signal_to_noise_ratio = Calculation.signal_noise_ratio(self, df)
			self.dataframe_report.at[self.counter, 'Check 3.2'] = "{}".format \
				(signal_to_noise_ratio)
			s9 = 'Accuracy Check 2: SNR available as {}'.format(signal_to_noise_ratio)
		else:
			self.dataframe_report.at[self.counter, 'Check 3.2'] = "N/A"
			s9 = 'Accuracy Check 2: N/A'

		if self.accuracy_check_3 and self.flow_use:
			reference_value = Calculation.reference_comparison(self, now)
			s10 = 'Accuracy Check 3: {}% values appear within a {}% range of the \
reference flowmeter mean'.format(reference_value, self.accuracy_range) \
				if type(reference_value) == float else reference_value
			self.dataframe_report.at[self.counter, 'Check 3.3'] = "{}".format(reference_value)
		else:
			s10 = 'Accuracy Check 3: N/A'
			self.dataframe_report.at[self.counter, 'Check 3.3'] = 'N/A'

		self.statement_list.extend([s8, s9, s10])

	def mean_squared_error(self):
		'''
		Calculates the mse value between the digital and analog tags
-------------------------------------
		Parameters:
		self.analog_digital: Holds two tags, analog and digital for the
			same location
		self.time_delta: time difference between start and end time
-------------------------------------
		Returns:
		mse_value: mean squared error
		nominal_flowrate: average flowrate of the time selected
		'''
		df_flowmeterSet1 = pd.read_csv('./_Data/_rtu/{}.csv'.format \
			(self.analog_digital[0]))
		df_flowmeterSet2 = pd.read_csv('./_Data/_rtu/{}.csv'.format \
			(self.analog_digital[1]))
		
		flowmeter_hour_set_1 = Calculation.hour_check(self, df_flowmeterSet1) if \
			int((self.time_delta.total_seconds())/3600) > 12 else df_flowmeterSet1['value']
		flowmeter_hour_set_2 = Calculation.hour_check(self, df_flowmeterSet2) if \
			int((self.time_delta.total_seconds())/3600) > 12 else df_flowmeterSet2['value'] 

		flowmeter_hour_set_1 = Calculation.mse_unit_check(self, flowmeter_hour_set_1)
		flowmeter_hour_set_2 = Calculation.mse_unit_check(self, flowmeter_hour_set_2)

		if len(flowmeter_hour_set_1) > len(flowmeter_hour_set_2):
			flowmeter_hour_set_1 = flowmeter_hour_set_1[0:len(flowmeter_hour_set_2)]
		if len(flowmeter_hour_set_1) < len(flowmeter_hour_set_2):
			flowmeter_hour_set_2 = flowmeter_hour_set_2[0:len(flowmeter_hour_set_1)]

		# This assumes both data sets are of equal size
		mse_value = (np.square(np.subtract(flowmeter_hour_set_1, \
			flowmeter_hour_set_2)).mean())/np.mean(flowmeter_hour_set_1) * 100
		nominal_flowrate = np.mean(flowmeter_hour_set_1)
		return mse_value, nominal_flowrate

	def mse_unit_check(self, list_of_values):
		'''
		Called if over 12h of data is provided; converts data to m3 if provided
			in barrels
-------------------------------------
		Parameters:
		self.min_Q: Minimum flowrate input from user
		self.max_Q: Maximum flowrate input from user
-------------------------------------
		Returns:
		list_of_values: A list of 1 hour, converted to barrels if necessary, selected
			at a steady state section
		'''
		for index in range(len(list_of_values)):
			if list_of_values[index] >= 0.8*self.min_Q and \
				list_of_values[index] <= 1.2*self.max_Q:
				pass
			else:
				list_of_values[index] = round(list_of_values[index]/6.2898, 5)
		return list_of_values

	def reference_comparison(self, now):
		'''
		Compares two review file tags, by isolating a list of values
			from the review file of both tags and checking if the flowmeter values
			appear within 1% of the reference mean. If the time difference between
			the start and end time is over 12h, it calls on "hour_check_review",
			and uses the first hour above min_Q to calculate the comparison plots
			and values within 1% of the mean. Else, it uses the first hour for
			the plots and mean comparison.
-------------------------------------
		Parameters:
		self.dataframe_tags: List of all tags in the 'csv_tags" file
		self.LD_name: LD Tag ID
		self.attribute_list: List of review file attributes
		self.dataframe_review: Uses the dataframe created using the review file
			for the tag being assessed
-------------------------------------
		Returns:
		Image comparison between the analong and digital flowmeters
		'''
		reference_tag = (self.dataframe_tags['Reference_Meter'].loc \
			[self.dataframe_tags['LDTagID'] == self.LD_name]).to_string \
			(index=False).upper()
		if int((self.time_delta.total_seconds())/3600) > 12:
			scada_tag_values = Calculation.hour_check_review(self,
				self.dataframe_review, self.SCADA_name)
		else:
			scada_tag_values = self.dataframe_review[' {}:{}'.format \
				(self.SCADA_name, self.attribute_list[2])].to_list()
		try:
			Calculation.review(self, reference_tag)
			if int((self.time_delta.total_seconds())/3600) > 12:
				reference_values = Calculation.hour_check_review(self,
					self.dataframe_review, reference_tag)
				referance_average = np.mean(reference_values)
			else:
				reference_values = self.dataframe_review[' {}:{}'.format \
					(reference_tag, self.attribute_list[2])]
				referance_average = reference_values.mean()
			Calculation.comparison_plot(self, reference_tag, reference_values, \
				scada_tag_values, now)
			comparison_length = []
			lower_value = 1 - ((self.accuracy_range)/100)
			upper_value = 1 + ((self.accuracy_range)/100)
			for i in scada_tag_values:
				if lower_value*referance_average <= i <= upper_value*referance_average:
					comparison_length.append(i)
			len_comparison = (len(comparison_length)/len(scada_tag_values)) * 100
			return round(len_comparison, 2)
		except:
			return "No reference provided"

	def signal_noise_ratio(self, df):
		'''
		Uses an hour of data to assess the signal-to-noise ratio for a steady
			state section. Calls on "hour_check" to evaluate the 1 hour time.
			The SNR is calculated using the mean and standard deviation of 
			the list of hour data returned from "hour_check"
-------------------------------------
		Parameters:
		df: self.dataframe_temporary, or the data for the current tag
-------------------------------------
		Returns:
		SNR: The signal-to-noise ratio
		'''
		list_1_h_above_min = Calculation.hour_check(self, df)
		if list_1_h_above_min == None:
			return None
		else:
			mean_steady_state = np.mean(list_1_h_above_min)
			standard_dev_steady_state = np.std(list_1_h_above_min)
			return round((mean_steady_state/standard_dev_steady_state), 3)

	def robustness(self, now):
		'''
		Performs the test for robustness by plotting the value of each tag, and
			determining the percent of values that are within a +/- 3 SD, in
			order to pass or fail the values read.
-------------------------------------
		Parameters:
		now: Current date and time
		self.robustness_check_1: True or False for Robustness Check 1
		self.flow_use: True or False if assessing a flowmeter tag
		self.value: List of values from the tag being assessed
		self.statement_list: list of statements written to per check
-------------------------------------
		Returns:
		Images in "_meter_rate" folder
		'''
		if self.robustness_check_1 and self.flow_use:
			pass_fail = Calculation.signal_plot(self, now)
			pass_percent = len(pass_fail)/len(self.value)
			try:
				if pass_percent > 0.9:
					s11 = 'Robustness Check 1: Plots available in "_images" folder, \
values pass with {}% within 3 Standard Deviations of the Mean' \
						.format(round(pass_percent * 100), 2)
				else:
					s11 = 'Robustness Check 1: Plots available in "_images" folder, \
values fail with {}% within 3 Standard Deviations of the Mean' \
					.format(round(pass_percent * 100), 2)
			except:
				s11 = 'Invalid Data'
		else:
			s11 = "Robustness Check 1: N/A"

		self.statement_list.append(s11)

	def comparison_plot(self, reference_tag, reference_values, scada_tag_values, now):
		'''
		Creates a histogram plot that compares a tag to a reference one provided
-------------------------------------
		Parameters:
		reference_tag: SCADA ID of the reference meter
		reference_values: Review data for the 1h+ time selected, or 1h if trying
			a full acceptance (for reference tag)
		scada_tag_values: Review data for the 1h+ time selected, or 1h if trying
			a full acceptance (for assessed tag)
		now: Current date and time
-------------------------------------
		Returns:
		Comparison histogram between meter and its reference
		'''
		mpl.rc('font', family='Times New Roman')
		fig, ax = plt.subplots(figsize=(16, 8), nrows=2, dpi=150, \
			facecolor='white', constrained_layout=True)
		ax[0].set_facecolor('gainsboro')
		ax[1].set_facecolor('gainsboro')

		(mu, sigma) = norm.fit(reference_values)
		(mu2, sigma2) = norm.fit(scada_tag_values)
		ax[0].set_title('Histogram Comparison for {} and {}'.format \
			(reference_tag, self.SCADA_name))
		ax[0].set_xlabel('Histogram Comparison between Reference and Tested Meters')
		ax[0].set_ylabel('Frequency of Intervals of flow')
		ax1 = ax[0].twinx()
		n, bins, patches = ax[0].hist(reference_values, 250, density=True, \
			facecolor='green', alpha=0.7, edgecolor='black')
		n2, bins2, patches2 = ax1.hist(scada_tag_values, 250, density=True, \
			facecolor='blue', alpha=0.7, edgecolor='black')
		ax[0].legend(['Reference Meter'], loc=1)
		ax1.legend(['Tested Meter'], loc=5)

		cdf = 0.5 * (1 + special.erf((bins - mu)/(sigma * np.sqrt(2))))
		cdf2 = 0.5 * (1 + special.erf((bins2 - mu2)/(sigma2 * np.sqrt(2))))

		ax[1].plot(bins, cdf, linestyle='--', color='green')
		ax[1].plot(bins2, cdf2, '--b')
		ax[1].set_title('Cumulative Distribution Plot')
		ax[1].set_xlabel("X")
		ax[1].set_ylabel("Sum of the Distribution up to a given X")
		ax[1].legend(['Reference Meter', 'Tested Meter'])

		plt.savefig('./_Report/_images/_comparison/Accuracy3_{}_{}.png'.format \
			(self.SCADA_name, now))

	def signal_plot(self, now):
		'''
		Creates number of plots for each flow tag for the values, overlapped with
			a distribution and noting outliers; also provides a percent count
			of values within 3 SD of the mean
-------------------------------------
		Parameters:
		now: Current date and time
		self.value: List of values from the tag being assessed
		self.LD_name: LD Tag ID
-------------------------------------
		Returns:
		pass_fail: Array of values within 3 SD of the mean
		'''
		tmr_font = {'fontname': 'Times New Roman'}
		mpl.rc('font', family='Times New Roman')
		fig, ax = plt.subplots(figsize=(12, 8), dpi=200, nrows=2, ncols=2, \
			facecolor='white', constrained_layout=True)
		ax[0, 0].set_facecolor('gainsboro') # ax[0, 0] references the first subplot of the left
		ax[1, 0].set_facecolor('gainsboro') # ax[1, 0] references the second subplot of the left
		ax[0, 1].set_facecolor('gainsboro') # ax[0, 1] references the first subplot of the right
		ax[1, 1].set_facecolor('gainsboro') # ax[1, 1] references the second subplot of the right

		# Creating the histogram
		ax[0, 0].set_xlabel('Tag {} Values'.format(self.LD_name), **tmr_font)
		ax[0, 0].set_ylabel('Frequency of Value Intervals', **tmr_font)
		(mu, sigma) = norm.fit(self.value)
		ax[0, 0].axvline(x=mu, linestyle='-.', alpha=1, color='black')
		ax[0, 0].axvline(x=mu + 3*sigma, color='blue')
		ax[0, 0].axvline(x=mu - 3*sigma, color='blue')
		n, bins, patches = ax[0, 0].hist(self.value, 100, density=True, \
			facecolor='green', alpha=0.7, edgecolor='black')
		pass_fail = [i for i in self.value if i > mu - 3*sigma and i < mu + 3*sigma]

		ax[0, 0].set_title('{}'.format(self.LD_name, **tmr_font))
		ax[0, 0].legend(['Mean of Data', '+/- 3 SD'], loc=1)
		ax1 = ax[0, 0].twinx()
		z = norm.pdf(self.value, mu, sigma)
		y = ((1 / (np.sqrt(2 * np.pi) * sigma)) * np.exp(-0.5 * (1 / sigma \
			 * (bins - mu))**2)) # Normal distribution PDF
		cdf = 0.5 * (1 + special.erf((bins - mu)/(sigma * np.sqrt(2))))
		ax1.plot(bins, y, '--r')
		ax1.legend(['Normal Curve'], loc=5)

		# Creating the boxplot on second subplot:
		ax[1, 0].boxplot(self.value, 0, 's', 0)
		ax[1, 0].set_title('{} Boxplot'.format(self.LD_name), **tmr_font)
		ax[1, 0].set_xlabel('Tag {} Values'.format(self.LD_name), **tmr_font)

		# Creating the p-p plot:
		res = probplot(self.value, plot=ax[0, 1])

		# CDF Plot
		ax[1, 1].plot(bins, cdf, '--b')
		ax[1, 1].set_title('Cumulative Distribution Plot', **tmr_font)
		ax[1, 1].set_xlabel("X", **tmr_font)
		ax[1, 1].set_ylabel("Sum of the Distribution up to a given X")

		# Statistical tests: - To test hypothesis test for if the distribution is normal
		# print("skew for {} is {}".format(self.LDName, skew(self.value)))
		# print("kurtosis for {} is {}".format(self.LDName, kurtosis(self.value)))

		plt.savefig('./_Report/_images/_meter_rate/{}_{}.png' \
			.format(self.LD_name, now))
		return pass_fail

	def time_plot(self, now):
		'''
		Creates a histogram plot for the time differences between two tag instances
			in rtu data
-------------------------------------
		Parameters:
		now: Current date and time
		self.time_difference: List of the time differences between two tag
			instances
		self.LD_name: LD Tag ID
-------------------------------------
		Returns:
		Histogram of time differences
		'''
		tmr_font = {'fontname': 'Times New Roman'}
		mpl.rc('font', family='Times New Roman')
		fig, ax = plt.subplots(figsize=(16, 8), nrows=2, dpi=150)
		ax[0].set_facecolor('gainsboro')
		ax[1].set_facecolor('gainsboro')

		(mu, sigma) = norm.fit(self.time_difference)
		ax[0].set_xlabel('Time Histogram for {}'.format(self.LD_name), **tmr_font)
		ax[0].set_ylabel('Frequency of Time Intervals', **tmr_font)
		n, bins, patches = ax[0].hist(self.time_difference, 250, density=True, \
			 facecolor='green', alpha=0.7, edgecolor='black')

		cdf = 0.5 * (1 + special.erf((bins - mu)/(sigma * np.sqrt(2))))
		ax[1].set_xlabel("X", **tmr_font)
		ax[1].set_ylabel("Sum of the Distribution up to a given X")
		ax[1].plot(bins, cdf, '--b')

		plt.savefig("./_Report/_images/_time_difference/TimeDifference_{}_{}.png" \
			.format(self.LD_name, now))

	def create_report(self, now):
		'''
		Writes to the final report, also deletes instances of any list, to be
			reused in the next tag
-------------------------------------
		Parameters:
		now: Current date and time
		self.statement_list: List of statements written per check
		self.value: List of values from the rtu tag file
		self.time_difference: List of the time differences between two tag
			instances
		self.time_unix: List of rtu Unix times
		self.bad_value_index: 
-------------------------------------
		Returns:
		final report addition per tag
		'''
		with open("./_Report/_individual_meter/tag_{}_{}.txt".format(self.counter, \
			now), "w") as NewFile:
			NewFile.write('Report for {} between start time {} and end time {}'.format(self.LD_name, self.time_start, self.time_end))
			NewFile.write('\n')
			for line in self.statement_list:
				NewFile.write(line)
				NewFile.write("\n")
				NewFile.write("\n")
		self.dataframe_report.to_csv('./_Report/_final/{}.csv'.format \
			(self.report_name), index=False)
		del self.statement_list[:]
		del self.value[:]
		del self.time_difference[:]
		del self.time_unix[:]
		del self.bad_value_index[:]
		self.number_oor_values = 0
		self.bad_quality = 0

if __name__ == "__main__":
	main()
