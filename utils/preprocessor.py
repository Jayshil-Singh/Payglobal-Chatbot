"""
PayGlobal query preprocessor (#7).

Expands common PayGlobal abbreviations before embedding so the retriever
finds more relevant chunks — e.g. "ESS" -> "ESS (Employee Self Service)".
"""
import re

# Common PayGlobal + HR/Payroll abbreviations
PAYGLOBAL_ABBREVIATIONS = {
    "ESS":  "Employee Self Service",
    "MSS":  "Manager Self Service",
    "GL":   "General Ledger",
    "PR":   "Payroll",
    "HR":   "Human Resources",
    "OB":   "Onboarding",
    "TA":   "Time and Attendance",
    "LM":   "Leave Management",
    "RM":   "Recruitment Management",
    "PD":   "Performance and Development",
    "WF":   "Workflow",
    "DB":   "Database",
    "SQL":  "SQL Server",
    "IIS":  "Internet Information Services",
    "AD":   "Active Directory",
    "LDAP": "Lightweight Directory Access Protocol",
    "API":  "Application Programming Interface",
    "FTP":  "File Transfer Protocol",
    "SMTP": "Simple Mail Transfer Protocol",
    "PDF":  "Portable Document Format",
    "CSV":  "Comma Separated Values",
    "XML":  "Extensible Markup Language",
    "SSRS": "SQL Server Reporting Services",
    "SSIS": "SQL Server Integration Services",
    "MFA":  "Multi-Factor Authentication",
    "SSO":  "Single Sign-On",
    "TFA":  "Two-Factor Authentication",
    "UI":   "User Interface",
    "SLA":  "Service Level Agreement",
    "EFT":  "Electronic Funds Transfer",
    "ABA":  "Australian Banking Association",
    "YTD":  "Year to Date",
    "MTD":  "Month to Date",
    "FY":   "Financial Year",
    "EOM":  "End of Month",
    "PAYG": "Pay As You Go",
    "SGC":  "Superannuation Guarantee Charge",
    "STP":  "Single Touch Payroll",
    "ATO":  "Australian Taxation Office",
    "TFN":  "Tax File Number",
    "ABN":  "Australian Business Number",
    "ACN":  "Australian Company Number",
}


def preprocess_query(query: str) -> str:
    """
    Expand known PayGlobal abbreviations in the query.
    Only expands if the full form isn't already present.

    Example:
      "ESS portal not loading" -> "ESS (Employee Self Service) portal not loading"
    """
    result = query
    for abbr, full in PAYGLOBAL_ABBREVIATIONS.items():
        pattern = r"\b" + re.escape(abbr) + r"\b"
        # Only expand if abbreviation present but full form is not
        if re.search(pattern, result, re.IGNORECASE) and full.lower() not in result.lower():
            result = re.sub(
                pattern,
                f"{abbr} ({full})",
                result,
                count=1,
                flags=re.IGNORECASE,
            )
    return result
