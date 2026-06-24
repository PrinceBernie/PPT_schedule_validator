import pandas as pd
from rapidfuzz import fuzz, process

# --- Global Settings ---
CONFIG = {
    'strict_threshold': 70,
    'loose_threshold': 90,
    'min_salary': 539,
    'max_salary': 61000,
    'contribution_tolerance': 0.5
}

# --- Utility Functions ---
def clean_name(value):
    return (
        str(value).strip().lower()
        .replace('.', ' ')
        .replace(',', ' ')
        .replace('-', ' ')
        .replace("  ", " ")
    )

def normalize_name(name):
    return " ".join(sorted(clean_name(name).split()))

def clean_id(value):
    if pd.isna(value):
        return ""
    return str(value).strip().replace(".0", "")

def clean_alphanum(value):
    if pd.isna(value):
        return ""
    return str(value).strip()

# --- Improved Fallback Matcher ---
def find_and_validate_match(df, key_col, key_val, input_name, threshold):
    """Generic function to find and validate matches across different ID types"""
    if pd.isna(key_val) or str(key_val).strip() == '':
        return None, None

    matches = df[df[key_col] == key_val]
    if not matches.empty:
        db_row = matches.iloc[0]
        score = fuzz.token_sort_ratio(input_name, db_row['clean_name'])
        if score >= threshold:
            return db_row, score

    return None, None

# --- Cross-Employer Check Helper ---
def cross_employer_flag(matched_row, employer_name):
    """Returns a warning string if the matched member belongs to a different employer, else empty string."""
    if not employer_name:
        return ""
    matched_group = str(matched_row.get('Group name', '')).strip() if 'Group name' in matched_row.index else ''
    if matched_group and matched_group != employer_name:
        return f" | ⚠️ CROSS-EMPLOYER — matched member belongs to '{matched_group}', not '{employer_name}'. VERIFY BEFORE UPLOAD."
    return ""

# --- Main Validator ---
def validate_schedule(schedule_df, filtered_df, scheme_df, employer_name="", debug=False):
    columns = [
        'SSNIT Number', 'NIA Number', 'Contact', 'Scheme Number',
        'Member Name', 'Salary', 'Tier2 Contribution'
    ]
    schedule_df = schedule_df.copy()
    filtered_df = filtered_df.copy()
    scheme_df = scheme_df.copy()

    schedule_df.columns = columns

    # Preserve identifier fields as text
    text_cols_schedule = ['SSNIT Number', 'NIA Number', 'Contact', 'Scheme Number', 'Member Name']
    for col in text_cols_schedule:
        schedule_df[col] = schedule_df[col].astype('string')

    text_cols_system = ['SSNIT Number', 'NIA Number', 'Contact', 'Scheme Number']
    for df in [filtered_df, scheme_df]:
        for col in text_cols_system:
            if col in df.columns:
                df[col] = df[col].astype('string')

    # Cleanup schedule data
    schedule_df['Member Name'] = schedule_df['Member Name'].fillna("").astype(str)
    schedule_df['clean_name'] = schedule_df['Member Name'].apply(normalize_name)

    schedule_df['NIA Number'] = schedule_df['NIA Number'].fillna("").astype(str).str.replace(r"[^a-zA-Z0-9]", "", regex=True)
    schedule_df['SSNIT Number'] = schedule_df['SSNIT Number'].fillna("").astype(str).str.replace(r"[^a-zA-Z0-9]", "", regex=True)

    # Contact: keep raw text version for assignment safety, numeric version for exact numeric comparison
    schedule_df['Contact_raw'] = schedule_df['Contact'].fillna("").astype(str).str.strip()
    schedule_df['Contact'] = pd.to_numeric(schedule_df['Contact_raw'], errors='coerce')

    schedule_df['Salary'] = pd.to_numeric(schedule_df['Salary'], errors='coerce')
    schedule_df['Tier2 Contribution'] = pd.to_numeric(schedule_df['Tier2 Contribution'], errors='coerce')
    schedule_df['Validation Status'] = ""

    # Cleanup scheme/system data
    scheme_df['clean_name'] = scheme_df[['FirstName', 'MiddleName', 'LastName']].fillna('').agg(' '.join, axis=1).apply(normalize_name)
    scheme_df['NIA Number'] = scheme_df['NIA Number'].fillna("").astype(str).str.replace(r"[^a-zA-Z0-9]", "", regex=True)
    scheme_df['SSNIT Number'] = scheme_df['SSNIT Number'].fillna("").astype(str).str.replace(r"[^a-zA-Z0-9]", "", regex=True)
    scheme_df['Contact_raw'] = scheme_df['Contact'].fillna("").astype(str).str.strip()
    scheme_df['Contact'] = pd.to_numeric(scheme_df['Contact_raw'], errors='coerce')
    scheme_df['Scheme Number'] = scheme_df['Scheme Number'].fillna("").astype(str).str.strip()

    filtered_df['clean_name'] = filtered_df[['FirstName', 'MiddleName', 'LastName']].fillna('').agg(' '.join, axis=1).apply(normalize_name)
    filtered_df['NIA Number'] = filtered_df['NIA Number'].fillna("").astype(str).str.replace(r"[^a-zA-Z0-9]", "", regex=True)
    filtered_df['SSNIT Number'] = filtered_df['SSNIT Number'].fillna("").astype(str).str.replace(r"[^a-zA-Z0-9]", "", regex=True)
    filtered_df['Contact_raw'] = filtered_df['Contact'].fillna("").astype(str).str.strip()
    filtered_df['Contact'] = pd.to_numeric(filtered_df['Contact_raw'], errors='coerce')
    filtered_df['Scheme Number'] = filtered_df['Scheme Number'].fillna("").astype(str).str.strip()

    for i, row in schedule_df.iterrows():
        status = []

        name = row['clean_name']
        scheme = str(row['Scheme Number']).strip() if pd.notna(row['Scheme Number']) else ""
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
                status.append("❌ Salary not within statutory range")

            expected = round(salary * 0.05, 2)
            if abs(round(tier2, 2) - expected) > CONFIG['contribution_tolerance']:
                status.append(f"❌ Incorrect 5% contribution (Expected: {expected})")

        # === Step 2: Member Identification ===
        matched_row = None
        scheme_match_found = False

        # Direct Scheme Match
        if scheme and scheme.startswith("1010") and len(scheme) == 13:
            match = scheme_df[scheme_df['Scheme Number'] == scheme]
            if not match.empty:
                db_name = match.iloc[0]['clean_name']
                score = fuzz.token_sort_ratio(name, db_name)
                if score >= CONFIG['loose_threshold']:
                    matched_row = match.iloc[0]
                    cross_flag = cross_employer_flag(matched_row, employer_name)
                    status.append(f"✅ Valid: Scheme match with name{cross_flag}")
                    scheme_match_found = True
                else:
                    status.append(f"⚠️ Scheme mismatch. Assigned to {db_name.title()}")
            else:
                status.append("⚠️ Scheme number not found in system")

        # === Step 3: Fallback Matching ===
        if not scheme_match_found:
            fallback_found = False

            # Use employer-specific search first
            if not fallback_found:
                matched_row, score = find_and_validate_match(filtered_df, 'Contact', contact, name, CONFIG['strict_threshold'])
                if matched_row is not None:
                    schedule_df.at[i, 'Scheme Number'] = str(matched_row['Scheme Number'])
                    status.append(f"✅ Contact Matched. Matched Name: {matched_row['clean_name'].title()} ({round(score, 2)}%)")
                    fallback_found = True

            if not fallback_found:
                matched_row, score = find_and_validate_match(filtered_df, 'NIA Number', gh_card, name, CONFIG['strict_threshold'])
                if matched_row is not None:
                    schedule_df.at[i, 'Scheme Number'] = str(matched_row['Scheme Number'])
                    status.append(f"✅ Ghana Card Matched. Matched Name: {matched_row['clean_name'].title()} ({round(score, 2)}%)")
                    fallback_found = True

            if not fallback_found:
                matched_row, score = find_and_validate_match(filtered_df, 'SSNIT Number', ssnit, name, CONFIG['strict_threshold'])
                if matched_row is not None:
                    schedule_df.at[i, 'Scheme Number'] = str(matched_row['Scheme Number'])
                    status.append(f"✅ SSNIT Number matched. Matched Name: {matched_row['clean_name'].title()} ({round(score, 2)}%)")
                    fallback_found = True

            # Fallback to full scheme search only if needed
            if not fallback_found:
                matched_row, score = find_and_validate_match(scheme_df, 'Contact', contact, name, CONFIG['strict_threshold'])
                if matched_row is not None:
                    schedule_df.at[i, 'Scheme Number'] = str(matched_row['Scheme Number'])
                    cross_flag = cross_employer_flag(matched_row, employer_name)
                    status.append(f"✅ Contact matched in scheme. Matched Name: {matched_row['clean_name'].title()} ({round(score, 2)}%){cross_flag}")
                    fallback_found = True

            if not fallback_found:
                matched_row, score = find_and_validate_match(scheme_df, 'NIA Number', gh_card, name, CONFIG['strict_threshold'])
                if matched_row is not None:
                    schedule_df.at[i, 'Scheme Number'] = str(matched_row['Scheme Number'])
                    cross_flag = cross_employer_flag(matched_row, employer_name)
                    status.append(f"✅ Ghana Card matched in scheme. Matched Name: {matched_row['clean_name'].title()} ({round(score, 2)}%){cross_flag}")
                    fallback_found = True

            if not fallback_found:
                matched_row, score = find_and_validate_match(scheme_df, 'SSNIT Number', ssnit, name, CONFIG['strict_threshold'])
                if matched_row is not None:
                    schedule_df.at[i, 'Scheme Number'] = str(matched_row['Scheme Number'])
                    cross_flag = cross_employer_flag(matched_row, employer_name)
                    status.append(f"✅ SSNIT Number matched in scheme. Matched Name: {matched_row['clean_name'].title()} ({round(score, 2)}%){cross_flag}")
                    fallback_found = True

            # Fuzzy name match within employer only
            # NOTE: Cross-employer fuzzy matching has been intentionally removed.
            # Matching names against the full scheme_df risks assigning contributions
            # to members from different employers with similar names, causing misallocations
            # that require reversals and damage data integrity.
            # If no identifier or employer-scoped name match is found, the record is
            # flagged as Unregistered for manual resolution.
            if not fallback_found and not filtered_df.empty:
                match = process.extractOne(name, filtered_df['clean_name'].tolist(), scorer=fuzz.token_sort_ratio)
                if match and match[1] >= CONFIG['loose_threshold']:
                    matched_name = match[0]
                    row_match = filtered_df[filtered_df['clean_name'] == matched_name].iloc[0]
                    group_name = str(row_match.get('Group name', 'Unknown')).strip() if 'Group name' in row_match.index else 'Unknown'
                    schedule_df.at[i, 'Scheme Number'] = str(row_match['Scheme Number'])
                    status.append(
                        f"⚠️🔎 FUZZY NAME MATCH — MANUAL REVIEW REQUIRED | "
                        f"Matched: {matched_name.title()} ({round(match[1], 2)}%) | "
                        f"Group: {group_name}"
                    )
                    fallback_found = True

            if not fallback_found:
                status.append("🟡 Unregistered member")

        # Finalize status
        if not status:
            status.append("✅ Valid")

        schedule_df.at[i, 'Validation Status'] = "; ".join(status)

    # Sort: issues first, clean records last, alphabetical by name within each group.
    # Priority: cross-employer warnings > errors > fuzzy matches > suspense/unregistered > scheme mismatches > clean
    def sort_priority(status_val):
        s = str(status_val)
        if 'CROSS-EMPLOYER' in s:
            return 0
        if '❌' in s:
            return 1
        if 'FUZZY' in s:
            return 2
        if 'Unregistered member' in s:
            return 3
        if 'Scheme mismatch' in s or 'not found in system' in s:
            return 4
        return 5  # clean ✅ records

    schedule_df['_sort_priority'] = schedule_df['Validation Status'].apply(sort_priority)
    return (
        schedule_df
        .sort_values(by=['_sort_priority', 'Member Name'], ascending=[True, True])
        .drop(columns=['_sort_priority'])
    )
