-- SQL Query for fetching distinct line numbers from Oracle SCADA_CMT_PRD database
-- This query retrieves unique line numbers for the line selection dropdown
SELECT DISTINCT line_no 
FROM linefill_pcs_xfr 
ORDER BY line_no ASC