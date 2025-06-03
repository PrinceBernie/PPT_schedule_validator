import pandas as pd
from rapidfuzz import fuzz, process

# --- Utility Functions ---

def clean_name(column):
    return (column.astype(str).str.strip().str.lower()
            .str.replace(".", " ", regex=False)
            .str.replace(",", " ", regex=False)
            .str.replace(r"\s+", " ", regex=True))

def build_full_name(df):
    return (df[['FirstName', 'MiddleName', 'LastName']].fillna('')
            .agg(' '.join, axis=1)
            .str.strip()
            .str.replace(r"\s+", " ", regex=True))

def find_and_validate_match(df, key_col, key_val, input_name, threshold):
    """
    Attempts to find a matching row in the provided DataFrame using a specific ID or contact field,
    and validates the match by checking the similarity of names using fuzzy string matching.

    Parameters:
    -----------
    df : pandas.DataFrame
        The dataset (usually the system dump) to search for a potential match.
    
    key_col : str
        The name of the (system) column to match against (e.g., 'NIA Number', 'SSNIT Number', or 'Contact').
    
    key_val : str or float
        The value from the uploaded schedule that we want to use for matching (e.g., a specific Ghana Card number).
    
    input_name : str
        The cleaned name of the member from the uploaded schedule (used for verifying that the ID/contact belongs to the right person).
    
    threshold : int
        The minimum acceptable fuzzy match score (0–100) required to consider the name validation successful.

    Returns:
    --------
    db_row : pandas.Series or None
        The first row from the dataset that matches the key value and passes the fuzzy name similarity check.
        Returns None if no match is found or if the name does not meet the similarity threshold.

    score : float or None
        The fuzzy match score between the input name and the matched system record's name. 
        This score helps determine how similar the names are (used as a secondary validation step).
        Returns None if no valid match is found.

    Function Logic:
    ---------------
    1. If the provided value (`key_val`) is missing or NaN, the function skips and returns no match.
    2. Otherwise, it searches the DataFrame for rows where the `key_col` exactly matches the given `key_val`.
    3. If one or more matches are found:
        a. It selects the first match (assumes uniqueness).
        b. It compares the cleaned name from the schedule to the cleaned name in the system using fuzzy token sorting.
        c. If the similarity score is greater than or equal to the threshold, it returns the matched row and score.
    4. If there's no match or the name similarity is too low, it returns None, None.

    This function is typically used for fallback validation when a scheme number is missing or unreliable,
    relying on alternate identifiers like Ghana Card, SSNIT Number, or Contact to find the member.
    """
    if pd.isna(key_val):
        return None, None
    match = df[df[key_col] == key_val]
    if not match.empty:
        db_row = match.iloc[0]
        score = fuzz.token_sort_ratio(input_name, db_row['clean_name'])
        if score >= threshold:
            return db_row, score
    return None, None

# --- Main Validation Function ---

def validate_schedule(schedule_df, filtered_df, scheme_df):
    strict_threshold, loose_threshold = 85, 50

    rename_map = {
        'Creation time': 'Creation Time', 'Start date': 'Start Date', 'Region': 'Region',
        'Gender': 'Gender', 'First name': 'FirstName', '[Middle name]': 'MiddleName',
        '[Last name]': 'LastName', 'Member number': 'Member Number', '[Scheme number]': 'Scheme Number',
        'Mobile': 'Contact', 'Date of birth': 'DOB', '[Scheme name]': 'Scheme Name',
        '[Agent name]': 'Agent Name', 'Group name': 'Group Name', 'Place of birth': 'Place of Birth',
        'S s n i t': 'SSNIT Number', '[IDType]': 'ID Type', 'Id number': 'NIA Number',
        'Residential address': 'Residential Address', 'Digital address code': 'Digital Address',
        'Postal address': 'Postal Address', 'Landmark': 'Landmark', 'Email': 'Email',
        'Home town': 'HomeTown', 'Marital status': 'Marital Status', 'Country': 'Country',
        'Occupation': 'Occupation', 'Status': 'Status'
    }

    # --- Prepare Dump Copies ---
    dump_dfs = []
    for df in [filtered_df.copy(), scheme_df.copy()]:
        df.rename(columns=rename_map, inplace=True)
        df['clean_name'] = clean_name(build_full_name(df))
        df['clean_name'] = df['clean_name'].apply(lambda name: " ".join(sorted(str(name).split())))
        df['NIA Number'] = df['NIA Number'].astype(str).str.strip().str.replace(r"[^\w]", "", regex=True)
        df['SSNIT Number'] = df['SSNIT Number'].astype(str).str.strip().str.replace(r"[^\w]", "", regex=True)
        df['Contact'] = pd.to_numeric(df['Contact'], errors='coerce')
        dump_dfs.append(df)
    filtered_df, scheme_df = dump_dfs

    # --- Prepare Schedule ---
    schedule_df = schedule_df.rename(columns={
        'SSNIT NUMBER': 'SSNIT Number', 'GH. CARD NUMBER': 'NIA Number', 'CONTACT': 'Contact',
        'PPT SCHEME NUMBER': 'Scheme Number', 'MEMBER NAME': 'Member Name',
        'BASIC SALARY': 'Salary', '5% CONTRIBUTION': 'Tier2 Contribution'
    })

    schedule_df['clean_name'] = clean_name(schedule_df['Member Name'])
    schedule_df['clean_name'] = schedule_df['clean_name'].apply(lambda name: " ".join(sorted(str(name).split())))
    schedule_df['NIA Number'] = schedule_df['NIA Number'].astype(str).str.strip().str.replace(r"[^\w]", "", regex=True)
    schedule_df['SSNIT Number'] = schedule_df['SSNIT Number'].astype(str).str.strip().str.replace(r"[^\w]", "", regex=True)
    schedule_df['Scheme Number'] = schedule_df['Scheme Number'].astype(str).str.strip().str.replace(r"[^\w]", "", regex=True)
    schedule_df['Contact'] = pd.to_numeric(schedule_df['Contact'], errors='coerce')
    schedule_df['Salary'] = pd.to_numeric(schedule_df['Salary'], errors='coerce')
    schedule_df['Tier2 Contribution'] = pd.to_numeric(schedule_df['Tier2 Contribution'], errors='coerce')
    schedule_df['Validation Status'] = ""
    schedule_df['Match Type'] = ""

    for i, row in schedule_df.iterrows():
        status = []
        match_type = ""
        name = row['clean_name']
        scheme = row['Scheme Number']
        gh_card = row['NIA Number']
        ssnit = row['SSNIT Number']
        contact = row['Contact']
        salary = row['Salary']
        tier2 = row['Tier2 Contribution']

        # Step 1: Salary & Contribution Check
        if pd.isna(salary) or pd.isna(tier2):
            schedule_df.at[i, 'Validation Status'] = "❌ FLAG: Missing basic salary or 5% contribution"
            continue

        if not (539.8 <= salary <= 61000):
            schedule_df.at[i, 'Validation Status'] = "❌ FLAG: Basic salary not within statutory range (GHS 539.80 - 61,000)"
            continue

        expected = round(salary * 0.05, 2)
        if (abs(round(tier2, 2) - expected) > 0.5) and ("ops" in str(scheme).lower()):
            schedule_df.at[i, 'Validation Status'] = f"❌ FLAG: Incorrect 5% contribution (expected GHS {expected:.2f})"
            continue

        # Step 2: Scheme ID or Fallback Matching
        matched_row = None
        scheme_mismatch = False

        # --- Direct Scheme Match ---
        if scheme and len(scheme) == 13 and scheme.startswith("1010"):
            match_row = scheme_df[scheme_df['Scheme Number'] == scheme]
            if not match_row.empty:
                db_name = match_row.iloc[0]['clean_name']
                similarity = fuzz.token_sort_ratio(name, db_name)
                if similarity >= loose_threshold:
                    status.append("✅ VALID: Member matched with scheme ID and name")
                    match_type = "Direct Scheme"
                    matched_row = match_row.iloc[0]
                else:
                    status.append(f"⚠️ WARNING: Incorrect scheme number assignment. Assigned scheme number, {scheme}, belongs to {str(db_name).title()}")
                    scheme_mismatch = True 
            else:
                status.append(f"⚠️ WARNING: No match for Scheme No., {scheme}, in the selected scheme's database")
                scheme_mismatch = True
        else:
            scheme_mismatch = True

        # --- Allow fallback if scheme is missing or mismatch occurred ---
        if scheme_mismatch and matched_row is None:
            for id_type, col in [('Ghana Card', 'NIA Number'), ('SSNIT', 'SSNIT Number'), ('Contact', 'Contact')]:
                match, score = find_and_validate_match(scheme_df, col, row[col], name, strict_threshold)
                if match is not None:
                    schedule_df.at[i, 'Scheme Number'] = match['Scheme Number']
                    status.append(f"✅ VALID: Scheme ID auto-matched and populated using ({id_type} match). Matched name: {match['clean_name'].title()}")
                    match_type = id_type
                    matched_row = match
                    break

            # ---- Fuzzy Name Match ----
            if matched_row is None:
                match = process.extractOne(name, filtered_df['clean_name'].tolist(), scorer=fuzz.token_sort_ratio)
                if match:
                    matched_name, score, _ = match  # updated for rapidfuzz (score is float, match includes index)
                    if score >= strict_threshold:
                        matched_row = filtered_df[filtered_df['clean_name'] == matched_name].iloc[0]
                        schedule_df.at[i, 'Scheme Number'] = matched_row['Scheme Number']
                        status.append(f"🚫 INFO: Scheme ID filled via fuzzy name. Matched: {matched_name} Fuzzy score = {round(float(score), 2)}%")
                        match_type = "Fuzzy Name"
                    else:
                        status.append("🟡 NOTICE: No match found in system (likely unregistered member)")
                else:
                    status.append("🟡 NOTICE: No match found in system (likely unregistered member)")

        # Optional: flag if name doesn't match well
        if matched_row is not None and fuzz.token_sort_ratio(name, matched_row['clean_name']) < loose_threshold:
            status.append(f"⚠️ *Name mismatch with matched record {round(fuzz.token_sort_ratio(name, matched_row['clean_name']),2)}%")

        schedule_df.at[i, 'Validation Status'] = "; ".join(status)
        schedule_df.at[i, 'Match Type'] = match_type
        schedule_df[["SSNIT Number", "NIA Number", "Contact", "Scheme Number"]] = schedule_df[
            ["SSNIT Number", "NIA Number", "Contact", "Scheme Number"]].astype(str).replace("nan", "")

    return schedule_df.fillna("").sort_values(by=["Member Name", "Validation Status"], ascending=[True, True])
