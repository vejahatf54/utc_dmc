import flowmeter_main
import pytest
import os
import pandas as pd
import numpy as np
from time import strftime

arg_dict = {
        'rtu_file': None,
		'csv_tags_file': None,
		"review_file": None,
		"csv_file": "test_csvFile.csv",
		"report_name": "report",
		"time_start": "23/05/21 23:00:00",
		"time_end": "23/05/21 23:02:00",
		"threshold_FLAT": 5,
		"min_Q": 100,
		"max_Q": 10000,
        "accuracy_range": 2,
		"reliability_check_1": True,
		"reliability_check_2": True,
		"reliability_check_3": True,
		"reliability_check_4": True,
		"tc_check_1": True,
		"tc_check_2": True,
		"robustness_check_1": True,
		"accuracy_check_1": True,
		"accuracy_check_2": True,
		"accuracy_check_3": True,
		"accuracy_check_4": True
        }

test_dataframe_tags = {
        'LDTagID': ['RATE.FN-62-FIT-1-SQ-DFR', 'RATE.FN-62-FIT-1',
                      'ANALOG.FN-62-TIT-1', 'ANALOG.FN-62-PIT-1LD', 
                      'L01_LP_QSO_SU_1M1', 'L01_LP_QSO_SU_1M1A',
                      'L01_LP_P_SU_1PT2S', 'L01_LP_T_SU_1TT1'],
        'SCADATagID': ['FN_FLOW_DEL', 'FN_FLOW_DEL_ALT',
                      'FN_T_HO_62TT1', 'FN_P_UP_62PT1LD',
                      'LP_QSO_SU_1FY1', 'LP_QSO_SU_1FY1_A',
                      'LP_P_SUCT', 'LP_T_SU_1TT1'],
        'LowerBound': [-50, -10,
                      -1, -50,
                      -50, -50,
                       0, -10],
        'UpperBound': [2500, 2500,
                      70, 600,
                      2500, 2500,
                      1500, 40],
        'Reference_Meter': ['RD_FLOW_ML', 'RD_FLOW_ML_ALT',
                            'N/A', 'N/A',
                            'LB_FLOW_ML', 'LB_FLOW_ML',
                            'N/A', 'N/A']}

def test_directory():
    data_directory = './_Data'

    flowmeter_main.directory()

    assert os.path.exists(data_directory)

def test_main_report():
    reference_dataframe = pd.DataFrame(
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
    test_obj = flowmeter_main.argument(arg_dict)
    test_obj.main_report()
    pd.testing.assert_frame_equal(test_obj.dataframe_report, reference_dataframe)

def test_tag_name_and_list():
    test_obj = flowmeter_main.argument(arg_dict)
    test_obj.dataframe_tags = pd.DataFrame.from_dict(test_dataframe_tags)
    test_obj.tag_name_and_list()
    assert test_obj.flow_LD_tag_name_list == ['RATE.FN-62-FIT-1-SQ-DFR', 'RATE.FN-62-FIT-1', 'L01_LP_QSO_SU_1M1', 'L01_LP_QSO_SU_1M1A']

def test_hour_check_1():
    test_dataframe_hour_check = pd.DataFrame(index=np.arange(4000), columns=['rtime','value'])
    test_dataframe_hour_check['value'] = 250
    test_dataframe_hour_check['rtime'] = test_dataframe_hour_check.index
    test_obj = flowmeter_main.Calculation(arg_dict).hour_check(test_dataframe_hour_check)
    assert type(test_obj) == list

def test_hour_check_2():
    test_dataframe_hour_check = pd.DataFrame(index=np.arange(8000), columns=['rtime','value'])
    test_dataframe_hour_check.iloc[0:4000, -1] = 50
    test_dataframe_hour_check.iloc[4000:8000, -1] = 250
    test_dataframe_hour_check['rtime'] = test_dataframe_hour_check.index
    test_obj = flowmeter_main.Calculation(arg_dict).hour_check(test_dataframe_hour_check)
    assert len(test_obj) == 3601

def test_hour_check_3():
    test_dataframe_hour_check = pd.DataFrame(index=np.arange(4000), columns=['rtime','value'])
    test_dataframe_hour_check['value'] = 50
    test_dataframe_hour_check['rtime'] = test_dataframe_hour_check.index
    test_obj = flowmeter_main.Calculation(arg_dict).hour_check(test_dataframe_hour_check)
    assert test_obj == None

def test_unit_check_1():
    test_list_of_values = list(range(100, 150))*12
    test_obj = flowmeter_main.Calculation(arg_dict)
    test_obj.dataframe_report = pd.DataFrame(columns=['Check 1.2'])
    result = test_obj.unit_check(test_list_of_values)
    assert result == "Reliability Check 2: Units are all in m3/hr"

def test_unit_check_2():
    test_list_of_values = list(range(1, 10))*12
    test_obj = flowmeter_main.Calculation(arg_dict)
    test_obj.value = test_list_of_values
    test_obj.dataframe_report = pd.DataFrame(columns=['Check 1.2'])
    result = test_obj.unit_check(test_list_of_values)
    assert result == "Reliability Check 2: Some units appeared in barrels/hr, and were converted to m3/hr"

def test_unit_check_3():
    test_list_of_values = list(range(100, 150))
    test_obj = flowmeter_main.Calculation(arg_dict)
    test_obj.dataframe_report = pd.DataFrame(columns=['Check 1.2'])
    test_obj.reliability_check_2 = False
    result = test_obj.unit_check(test_list_of_values)
    assert result == 'Reliability Check 2: Not Selected'

def test_mean_squared_error():
    test_list_of_tags = ['RATE.FN-62-FIT-1', 'RATE.FN-62-FIT-1-SQ-DFR']
    test_obj = flowmeter_main.Calculation(arg_dict)
    test_obj.analog_digital = test_list_of_tags
    result_mse, result_Q = test_obj.mean_squared_error()
    assert result_mse < 5
    assert result_Q < 2000

def test_reference_comparison():
    test_obj = flowmeter_main.Calculation(arg_dict)
    test_obj.dataframe_tags = pd.DataFrame.from_dict(test_dataframe_tags)
    test_dataframe_review = {
        'TIME': ["2023/05/21 23:00:00.000", "2023/05/21 23:01:00.000", "2023/05/21 23:02:00.000"],
        ' FN_FLOW_DEL:VAL': [753.923, 754.225, 754.12],
        ' FN_FLOW_DEL_ALT:FLAT': [752.277, 752.673, 752.529],
        ' RD_FLOW_ML:VAL': [752.96, 752.577, 752.919],
        ' RD_FLOW_ML_ALT:VAL': [754, 753, 754],
    }
    test_obj.dataframe_review = pd.DataFrame.from_dict(test_dataframe_review)
    test_obj.attribute_list = ['ST', 'FLAT', 'VAL']
    test_obj.LD_name = 'RATE.FN-62-FIT-1-SQ-DFR'
    test_obj.SCADA_name = 'FN_FLOW_DEL'
    test_obj.review_file = "./l62.review"
    now = strftime('%Y-%m-%d_%H-%M')
    result = test_obj.reference_comparison(now)
    assert result == 100

def test_mse_unit_check_1():
    test_obj = flowmeter_main.Calculation(arg_dict)
    test_list = [200]* 100
    test_result_list = test_list
    result = test_obj.mse_unit_check(test_list)
    assert result == test_list

def test_mse_unit_check_2():
    test_obj = flowmeter_main.Calculation(arg_dict)
    test_list = [200, 10]* 50
    test_result_list = [200, 1.58988] *50
    result = test_obj.mse_unit_check(test_list)
    assert result == test_result_list

def test_signal_noise_ratio_1():
    test_dataframe_hour_check = pd.DataFrame(index=np.arange(4000), columns=['rtime','value'])
    test_dataframe_hour_check.iloc[0:2000, -1] = 200
    test_dataframe_hour_check.iloc[2000:4000, -1] = 250
    test_dataframe_hour_check['rtime'] = test_dataframe_hour_check.index
    test_obj = flowmeter_main.Calculation(arg_dict)
    result = test_obj.signal_noise_ratio(test_dataframe_hour_check)
    assert result == 8.944

def test_signal_noise_ratio_2():
    test_dataframe_hour_check = pd.DataFrame(index=np.arange(4000), columns=['rtime','value'])
    test_dataframe_hour_check.iloc[0:2000, -1] = 50
    test_dataframe_hour_check.iloc[2000:4000, -1] = 75
    test_dataframe_hour_check['rtime'] = test_dataframe_hour_check.index
    test_obj = flowmeter_main.Calculation(arg_dict)
    result = test_obj.signal_noise_ratio(test_dataframe_hour_check)
    assert result == None

def test_reliability_check_1_function():
    test_obj = flowmeter_main.Calculation(arg_dict)
    test_obj.dataframe_report = pd.DataFrame(columns=['Check 1.1'])
    test_obj.counter = 1
    test_obj.number_oor_values = 0
    result = test_obj.reliability_check_1_function()
    assert result == 'Reliability Check 1: Number of values in provided rtu \
file that are Out of Range: 0'

def test_reliability_check_2_function():
    test_obj = flowmeter_main.Calculation(arg_dict)
    test_obj.time_start = "23/05/21 18:00:00"
    test_obj.time_end = "23/05/21 23:00:00"
    test_obj.counter = 1
    test_dataframe_temporary = pd.DataFrame(index=np.arange(8000), columns=['rtime','value'])
    test_dataframe_temporary['value'] = 250
    test_dataframe_temporary['rtime'] = test_dataframe_temporary.index
    test_obj.dataframe_temporary = test_dataframe_temporary
    test_obj.dataframe_report = pd.DataFrame(columns=['Check 1.2'])
    result = test_obj.reliability_check_2_function()
    assert result == "Reliability Check 2: Units are all in m3/hr"

def test_reliability_1():
    test_obj = flowmeter_main.Calculation(arg_dict)
    now = strftime('%Y-%m-%d_%H-%M')
    test_obj.flow_use = True
    test_obj.pressure_use = test_obj.temperature_use = False
    test_dataframe_temporary = pd.DataFrame(index=np.arange(2000), columns=['ptnum', 'rtime', 'ident', 'value', 'qual'])
    test_dataframe_temporary['value'] = 100
    test_dataframe_temporary['rtime'] = test_dataframe_temporary.index
    test_dataframe_temporary['qual'] = 'GOOD'
    test_obj.dataframe_temporary = test_dataframe_temporary
    test_obj.dataframe_report = pd.DataFrame(columns=['Check 1.1', 'Check 1.2', 'Check 1.3', 'Check 1.4'])
    test_dataframe_review = pd.DataFrame(index=np.arange(2000), columns=[' FN_FLOW_DEL:ST'])
    test_dataframe_review[' FN_FLOW_DEL:ST'] = 1
    test_obj.value = test_obj.time_unix = []
    test_obj.dataframe_review = test_dataframe_review
    test_obj.lower_bound_value = -10
    test_obj.upper_bound_value = 2500
    test_obj.bad_quality = test_obj.number_oor_values = 0
    test_obj.LD_name = 'RATE.FN-62-FIT-1-SQ-DFR'
    test_obj.SCADA_name = 'FN_FLOW_DEL'
    test_obj.counter = 1
    test_obj.attribute_list = ['ST', 'FLAT', 'VAL']
    test_obj.statement_list = []
    test_obj.reliability(now)
    assert test_obj.statement_list == ['Reliability Check 1: Number of values in provided rtu \
file that are Out of Range: 0', "Reliability Check 2: Units are all in m3/hr", 'Reliability Check 3: Quality for tag RATE.FN-62-FIT-1-SQ-DFR is all GOOD',
'Reliability Check 4: Values appear GOOD in the review file']

def test_reliability_2():
    test_obj = flowmeter_main.Calculation(arg_dict)
    now = strftime('%Y-%m-%d_%H-%M')
    test_obj.flow_use = True
    test_obj.pressure_use = test_obj.temperature_use = False
    test_dataframe_temporary = pd.DataFrame(index=np.arange(2000), columns=['ptnum', 'rtime', 'ident', 'value', 'qual'])
    test_dataframe_temporary['value'] = 100
    test_dataframe_temporary['rtime'] = test_dataframe_temporary.index
    test_dataframe_temporary.iloc[0:1998, -1] = 'GOOD'
    test_dataframe_temporary.iloc[1997:2000, -1] = 'BAD'
    test_obj.dataframe_temporary = test_dataframe_temporary
    test_obj.dataframe_report = pd.DataFrame(columns=['Check 1.1', 'Check 1.2', 'Check 1.3', 'Check 1.4'])
    test_dataframe_review = pd.DataFrame(index=np.arange(2000), columns=[' FN_FLOW_DEL:ST'])
    test_dataframe_review[' FN_FLOW_DEL:ST'] = 1
    test_obj.value = test_obj.time_unix = []
    test_obj.dataframe_review = test_dataframe_review
    test_obj.lower_bound_value = -10
    test_obj.upper_bound_value = 2500
    test_obj.bad_quality = test_obj.number_oor_values = 0
    test_obj.LD_name = 'RATE.FN-62-FIT-1-SQ-DFR'
    test_obj.SCADA_name = 'FN_FLOW_DEL'
    test_obj.counter = 1
    test_obj.attribute_list = ['ST', 'FLAT', 'VAL']
    test_obj.statement_list = []
    test_obj.reliability(now)
    assert test_obj.statement_list == ['Reliability Check 1: Number of values in provided rtu \
file that are Out of Range: 0', "Reliability Check 2: Units are all in m3/hr", 'Reliability Check 3: BAD Quality present with 2 number of instances',
'Reliability Check 4: Values appear GOOD in the review file']