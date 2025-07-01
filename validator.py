import pandas as pd
from rapidfuzz import fuzz, process

# --- Global Settings .i.e. configurable parameters---
CONFIG = {
    'strict_threshold': 70,
    'loose_threshold': 90,
    'min_salary': 539,
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

# --- Improved Fallback Matcher ---
def find_and_validate_match(df, key_col, key_val, input_name, threshold):
    """Generic function to find and validate matches across different ID types"""
    if pd.isna(key_val) or str(key_val).strip() == '':
        return None, None
    
    # Handle both exact matches and potential variations
    matches = df[df[key_col] == key_val]
    if not matches.empty:
        db_row = matches.iloc[0]
        score = fuzz.token_sort_ratio(input_name, db_row['clean_name'])
        if score >= threshold:
            return db_row, score
    return None, None

# --- Main Validator ---
def validate_schedule(schedule_df, filtered_df, scheme_df, debug=False):
    columns = [
        'SSNIT Number', 'NIA Number', 'Contact', 'Scheme Number',
        'Member Name', 'Salary', 'Tier2 Contribution'
    ]
    schedule_df.columns = columns

    # Cleanup schedule data
    schedule_df['clean_name'] = schedule_df['Member Name'].apply(normalize_name)
    schedule_df['NIA Number'] = schedule_df['NIA Number'].astype(str).str.replace(r"[^a-zA-Z0-9]", "", regex=True)
    schedule_df['SSNIT Number'] = schedule_df['SSNIT Number'].astype(str).str.replace(r"[^a-zA-Z0-9]", "", regex=True)
    #schedule_df['Contact'] = schedule_df['Contact'].astype(str).str.replace(r"[^\d]", "", regex=True).str.strip()
    schedule_df['Contact'] = pd.to_numeric(schedule_df['Contact'], errors='coerce')
    schedule_df['Salary'] = pd.to_numeric(schedule_df['Salary'], errors='coerce')
    schedule_df['Tier2 Contribution'] = pd.to_numeric(schedule_df['Tier2 Contribution'], errors='coerce')
    schedule_df['Validation Status'] = ""

    # Cleanup system data
    scheme_df['clean_name'] = scheme_df[['FirstName', 'MiddleName', 'LastName']].fillna('').agg(' '.join, axis=1).apply(normalize_name)
    scheme_df['NIA Number'] = scheme_df['NIA Number'].astype(str).str.replace(r"[^a-zA-Z0-9]", "", regex=True)
    scheme_df['SSNIT Number'] = scheme_df['SSNIT Number'].astype(str).str.replace(r"[^a-zA-Z0-9]", "", regex=True)
    #scheme_df['Contact'] = scheme_df['Contact'].astype(str).str.replace(r"[^\d]", "", regex=True).str.strip()
    scheme_df['Contact'] = pd.to_numeric(scheme_df['Contact'], errors='coerce')

    filtered_df['clean_name'] = filtered_df[['FirstName', 'MiddleName', 'LastName']].fillna('').agg(' '.join, axis=1).apply(normalize_name)
    filtered_df['NIA Number'] = filtered_df['NIA Number'].astype(str).str.replace(r"[^a-zA-Z0-9]", "", regex=True)
    filtered_df['SSNIT Number'] = filtered_df['SSNIT Number'].astype(str).str.replace(r"[^a-zA-Z0-9]", "", regex=True)
    #filtered_df['Contact'] = filtered_df['Contact'].astype(str).str.replace(r"[^\d]", "", regex=True).str.strip()
    filtered_df['Contact'] = pd.to_numeric(filtered_df['Contact'], errors='coerce')
    
    for i, row in schedule_df.iterrows():
        status = []
        name = row['clean_name']
        scheme = str(row['Scheme Number']).strip()
        gh_card = row['NIA Number']
        ssnit = row['SSNIT Number']
        contact = row['Contact']
        salary = row['Salary']
        tier2 = row['Tier2 Contribution']

        # === Step 1: Salary and 5% Contribution Validation ===
        if pd.isna(salary) or pd.isna(tier2):
            status.append("❌ Missing Salary or 5% Contribution")
        else:
            if not (CONFIG['min_salary'] <= salary <= CONFIG['max_salary']):
                status.append("❌ Salary not within allowed range")
            expected = round(salary * 0.05, 2)
            if abs(round(tier2, 2) - expected) > CONFIG['contribution_tolerance']:
                status.append(f"❌ Incorrect 5% contribution (Expected: {expected})")

        # === Step 2: Member Identification ===
        matched_row = None
        scheme_match_found = False

        # Direct Scheme Match (if valid scheme number exists)
        if scheme and scheme.startswith("1010") and len(scheme) == 13:
            match = scheme_df[scheme_df['Scheme Number'] == scheme]
            if not match.empty:
                db_name = match.iloc[0]['clean_name']
                score = fuzz.token_sort_ratio(name, db_name)
                if score >= CONFIG['loose_threshold']:
                    matched_row = match.iloc[0]
                    status.append("✅ Valid: Scheme match with name")
                    scheme_match_found = True
                else:
                    status.append(f"⚠️ Scheme mismatch. Assigned to {db_name.title()}")
            else:
                status.append("⚠️ Scheme number not found in system")

        # === Step 3: Fallback Matching (only if no valid scheme match) ===
        if not scheme_match_found:
            fallback_found = False
            
            # Try Contact matching first (using filtered_df for employer-specific search)
            if not fallback_found:
                matched_row, score = find_and_validate_match(scheme_df, 'Contact', contact, name, CONFIG['strict_threshold'])
                if matched_row is not None:
                    schedule_df.at[i, 'Scheme Number'] = matched_row['Scheme Number']
                    status.append(f"✅ Contact Matched. Matched Name: {matched_row['clean_name'].title()} ({round(score,2)}%)")
                    fallback_found = True

            # Try Ghana Card matching (using filtered_df for employer-specific search)
            if not fallback_found:
                matched_row, score = find_and_validate_match(scheme_df, 'NIA Number', gh_card, name, CONFIG['strict_threshold'])
                if matched_row is not None:
                    schedule_df.at[i, 'Scheme Number'] = matched_row['Scheme Number']
                    status.append(f"✅ Ghana Card Matched. Matched Name: {matched_row['clean_name'].title()} ({round(score,2)}%)")
                    fallback_found = True

            # Try SSNIT Number matching (using filtered_df for employer-specific search)
            if not fallback_found:
                matched_row, score = find_and_validate_match(scheme_df, 'SSNIT Number', ssnit, name, CONFIG['strict_threshold'])
                if matched_row is not None:
                    schedule_df.at[i, 'Scheme Number'] = matched_row['Scheme Number']
                    status.append(f"✅ SSNIT Number matched. Matched Name: {matched_row['clean_name'].title()} ({round(score,2)}%)")
                    fallback_found = True

            # Fuzzy Name Match as last resort (using filtered_df for employer-specific search)
            if not fallback_found:
                match = process.extractOne(name, filtered_df['clean_name'].tolist(), scorer=fuzz.token_sort_ratio)
                if match and match[1] >= CONFIG['loose_threshold']:
                    matched_name = match[0]
                    row_match = filtered_df[filtered_df['clean_name'] == matched_name].iloc[0]
                    schedule_df.at[i, 'Scheme Number'] = row_match['Scheme Number']
                    status.append(f"🔎 Fuzzy Name Match: {matched_name.title()} ({round(match[1],2)}%)")
                    fallback_found = True

            # If no fallback match found
            if not fallback_found:
                status.append("🟡 Unregistered member")

        # Finalize status
        if not status:
            status.append("✅ Valid")
        
        schedule_df.at[i, 'Validation Status'] = "; ".join(status)

    return schedule_df.sort_values(by=["Validation Status", "Member Name"], ascending=[False, True])
