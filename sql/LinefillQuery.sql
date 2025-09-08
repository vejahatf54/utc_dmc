-- SQL Query for fetching linefill data from Oracle SCADA_CMT_PRD database
-- This query retrieves linefill data based on line number and timestamp
-- It joins with batch name data and replaces batch names in the file text
-- Parameters: %line%, %lineFillStartTime%

WITH
linefill_data AS (
  SELECT
    ROW_NUMBER() OVER (ORDER BY NULL) AS rn,
    FILE_TEXT,
    LNFL_INTL_ID
  FROM linefill_pcs_xfr
  WHERE TO_NUMBER(REGEXP_SUBSTR(file_text, '(\S*)(\s*)',1,3)) > 0
    AND line_no = '%line%'
    AND linefill_date = to_date('%lineFillStartTime%', 'hh24mi dd-Mon-yyyy')
    ORDER BY LNFLPX_INTL_ID ASC
),
linefill_batch_name AS (
  SELECT
    ROW_NUMBER() OVER (ORDER BY LINEFILL_SEQ_NBR) AS rn,
    REGEXP_REPLACE(LINEFILL_BATCH_NAME, '-', '    ') AS LINEFILL_BATCH_NAME
  FROM DIS_LINEFILL_BATCH_V
  WHERE LNFL_INTL_ID = (
    SELECT LNFL_INTL_ID
    FROM (
      SELECT LNFL_INTL_ID
      FROM linefill_data
      ORDER BY LNFL_INTL_ID
    )
    WHERE ROWNUM = 1
  )
)
SELECT
  REPLACE(
    linefill_data.FILE_TEXT, 
    SUBSTR(
      linefill_data.FILE_TEXT, 
      INSTR(linefill_data.FILE_TEXT, ' ') + 1, 
      INSTR(linefill_data.FILE_TEXT, ' ', 1, 2) - INSTR(linefill_data.FILE_TEXT, ' ') - 1
    ), 
    linefill_batch_name.LINEFILL_BATCH_NAME
  ) AS new_file_text
FROM linefill_data
JOIN linefill_batch_name ON linefill_data.rn = linefill_batch_name.rn
