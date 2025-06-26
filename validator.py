import pandas as pd
from rapidfuzz import fuzz, process

# --- Global Settings .i.e. configuable parameters---
CONFIG = {
    'strict_threshold': 85,
    'loose_threshold': 50,
    'min_salary': 539.8,
    'max_salary': 61000,
    'contribution_tolerance': 0.5
}

# --- Utility Functions ---
def clean_name(value):
    return (str(value).strip().lower()
            .replace('.', ' ').replace(',', ' ').replace("-"," ")
            .replace("  ", " "))

def normalize_name(name):
    return " ".join(sorted(clean_name(name).split()))

# --- Fallback Matchers ---
def match_by_contact(system_df, contact, name):
    if pd.isna(contact):
        return None, None
    contact_match = system_df.loc[system_df['Contact'] == contact]
    if not contact_match.empty:
        db_row = contact_match.iloc[0]
        score = fuzz.token_sort_ratio(name, db_row['clean_name'])
        if score >= CONFIG['strict_threshold']:
            return db_row, f"✅ Contact Matched. Matched Name: {db_row['clean_name'].title()} ({round(score,2)}%)"
    return None, None

def match_by_ghana_card(system_df, gh_card, name):
    if pd.isna(gh_card):
        return None, None
    for col in ['NIA Number', 'SSNIT Number']:
        match = system_df.loc[system_df[col] == gh_card]
        if not match.empty:
            db_row = match.iloc[0]
            score = fuzz.token_sort_ratio(name, db_row['clean_name'])
            if score >= CONFIG['strict_threshold']:
                return db_row, f"✅ Ghana Card Matched. Matched Name: {db_row['clean_name'].title()} ({round(score,2)}%)"
    return None, None

def match_by_ssnit(system_df, ssnit, name):
    if pd.isna(ssnit):
        return None, None
    for col in ['SSNIT Number', 'NIA Number']:
        match = system_df.loc[system_df[col] == ssnit]
        if not match.empty:
            db_row = match.iloc[0]
            score = fuzz.token_sort_ratio(name, db_row['clean_name'])
            if score >= CONFIG['strict_threshold']:
                return db_row, f"✅ SSNIT Number matched. Matched Name: {db_row['clean_name'].title()} ({round(score,2)}%)"
    return None, None

def match_by_fuzzy_name(filtered_df, name):
    match = process.extractOne(name, filtered_df['clean_name'].tolist(), scorer=fuzz.token_sort_ratio)
    if match and match[1] >= CONFIG['strict_threshold']:
        matched_name = match[0]
        row = filtered_df[filtered_df['clean_name'] == matched_name].iloc[0]
        return row, f"🔎 Fuzzy Name Match: {matched_name.title()} ({round(match[1],2)}%)"
    return None, "🟡 No fuzzy match found"

# --- Main Validator ---
def validate_schedule(schedule_df, filtered_df, scheme_df, debug=False):
    columns = [
        'SSNIT Number', 'NIA Number', 'Contact', 'Scheme Number',
        'Member Name', 'Salary', 'Tier2 Contribution'
    ]
    schedule_df.columns = columns

    # Cleanup
    schedule_df['clean_name'] = schedule_df['Member Name'].apply(normalize_name)
    schedule_df['NIA Number'] = schedule_df['NIA Number'].astype(str).str.replace(r"[^a-zA-Z0-9]", "", regex=True)
    schedule_df['SSNIT Number'] = schedule_df['SSNIT Number'].astype(str).str.replace(r"[^a-zA-Z0-9]", "", regex=True)
    schedule_df['Contact'] = schedule_df['Contact'].astype(str).str.strip()
    schedule_df['Contact'] = pd.to_numeric(schedule_df['Contact'], errors='coerce')
    schedule_df['Salary'] = pd.to_numeric(schedule_df['Salary'], errors='coerce')
    schedule_df['Tier2 Contribution'] = pd.to_numeric(schedule_df['Tier2 Contribution'], errors='coerce')
    schedule_df['Validation Status'] = ""

    scheme_df['clean_name'] = scheme_df[['FirstName', 'MiddleName', 'LastName']].fillna('').agg(' '.join, axis=1).apply(normalize_name)
    scheme_df['NIA Number'] = scheme_df['NIA Number'].astype(str).str.replace(r"[^a-zA-Z0-9]", "", regex=True)
    scheme_df['SSNIT Number'] = scheme_df['SSNIT Number'].astype(str).str.replace(r"[^a-zA-Z0-9]", "", regex=True)
    scheme_df['Contact'] = scheme_df['Contact'].astype(str).str.strip()
    scheme_df['Contact'] = pd.to_numeric(scheme_df['Contact'], errors='coerce')

    filtered_df['clean_name'] = filtered_df[['FirstName', 'MiddleName', 'LastName']].fillna('').agg(' '.join, axis=1).apply(normalize_name)
    filtered_df['NIA Number'] = filtered_df['NIA Number'].astype(str).str.replace(r"[^a-zA-Z0-9]", "", regex=True)
    filtered_df['SSNIT Number'] = filtered_df['SSNIT Number'].astype(str).str.replace(r"[^a-zA-Z0-9]", "", regex=True)
    filtered_df['Contact'] = pd.to_numeric(filtered_df['Contact'], errors='coerce')
    filtered_df['Contact'] = filtered_df['Contact'].astype(str).str.strip()
    
    for i, row in schedule_df.iterrows():
        status = []
        name = row['clean_name']
        scheme = str(row['Scheme Number']).strip()

        # Salary checks
        if pd.isna(row['Salary']) or pd.isna(row['Tier2 Contribution']):
            status.append("❌ Missing Salary or 5% Contribution")
        else:
            if not (CONFIG['min_salary'] <= row['Salary'] <= CONFIG['max_salary']):
                status.append("❌ Salary not within allowed range")
            expected = round(row['Salary'] * 0.05, 2)
            if abs(round(row['Tier2 Contribution'], 2) - expected) > CONFIG['contribution_tolerance']:
                status.append(f"❌ Incorrect 5% contribution (Expected: {expected})")

        matched_row = None

        # --- Direct Scheme Match ---
        if scheme and scheme.startswith("1010") and len(scheme) == 13:
            match = scheme_df[scheme_df['Scheme Number'] == scheme]
            if not match.empty:
                db_name = match.iloc[0]['clean_name']
                score = fuzz.token_sort_ratio(name, db_name)
                if score >= CONFIG['loose_threshold']:
                    matched_row = match.iloc[0]
                    status.append("✅ Valid: Scheme match with name")
                else:
                    status.append(f"⚠️ Scheme mismatch. Assigned to {db_name.title()}")
            else:
                status.append("⚠️ Scheme number not found in system")
        else:
            # --- Fallbacks ---
            for fallback in [match_by_contact, match_by_ghana_card, match_by_ssnit, match_by_fuzzy_name]:
                if fallback == match_by_contact:
                    matched_row, msg = fallback(scheme_df, row['Contact'], name)
                elif fallback == match_by_ghana_card:
                    matched_row, msg = fallback(scheme_df, row['NIA Number'], name)
                elif fallback == match_by_ssnit:
                    matched_row, msg = fallback(scheme_df, row['SSNIT Number'], name)
                elif fallback == match_by_fuzzy_name:
                    matched_row, msg = fallback(filtered_df, name)
                
                if matched_row is not None:
                    schedule_df.at[i, 'Scheme Number'] = matched_row['Scheme Number']
                    status.append(msg)
                    break
                elif msg:
                    status.append(msg)

        schedule_df.at[i, 'Validation Status'] = "; ".join(status)

    return schedule_df.sort_values(by=["Validation Status", "Member Name"], ascending=[False, True])
