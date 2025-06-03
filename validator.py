import pandas as pd
from fuzzywuzzy import fuzz, process

# --- Utility Functions ---

def clean_name(series):
    return (series.astype(str).str.strip().str.lower()
            .str.replace(".", " ", regex=False)
            .str.replace(",", " ", regex=False)
            .str.replace(r"\s+", " ", regex=True))

def build_full_name(df):
    return (df[['FirstName', 'MiddleName', 'LastName']].fillna('')
            .agg(' '.join, axis=1)
            .str.strip()
            .str.replace(r"\s+", " ", regex=True))

def find_and_validate_match(df, key_col, key_val, input_name, threshold):
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
    strict_threshold, loose_threshold = 80, 50

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
    schedule_df['NIA Number'] = schedule_df['NIA Number'].astype(str).str.strip().str.replace(r"[^\w]", "", regex=True)
    schedule_df['SSNIT Number'] = schedule_df['SSNIT Number'].astype(str).str.strip().str.replace(r"[^\w]", "", regex=True)
    schedule_df['Scheme Number'] = schedule_df['Scheme Number'].astype(str).str.strip().str.replace(r"[^\w]", "", regex=True)
    schedule_df['Contact'] = pd.to_numeric(schedule_df['Contact'], errors='coerce')
    schedule_df['Salary'] = pd.to_numeric(schedule_df['Salary'], errors='coerce')
    schedule_df['Tier2 Contribution'] = pd.to_numeric(schedule_df['Tier2 Contribution'], errors='coerce')
    schedule_df['Status'] = ""
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
            schedule_df.at[i, 'Status'] = "❌ *Missing salary or contribution"
            continue

        if not (539.8 <= salary <= 61000):
            schedule_df.at[i, 'Status'] = "❌ *Invalid salary range. (min: GHS 539.80, max: GHS 61,000)"
            continue

        expected = round(salary * 0.05, 2)
        if (abs(round(tier2, 2) - expected) > 0.5) and ("ops" in str(scheme).lower()):
            schedule_df.at[i, 'Status'] = f"❌ *Incorrect 5% (expected GHS {expected:.2f})"
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
                    status.append("✅ Valid Scheme ID & Name Match")
                    match_type = "Direct Scheme"
                    matched_row = match_row.iloc[0]
                else:
                    status.append("❌ *Scheme number assigned to different member")
                    print(f"[i={i}] Scheme mismatch, attempting fallback for: {name}")
                    scheme_mismatch = True
            else:
                status.append("❌ *Scheme number not found in system")
                scheme_mismatch = True
        else:
            scheme_mismatch = True

        # --- Allow fallback if scheme is missing or mismatch occurred ---
        if scheme_mismatch and matched_row is None:
            # --- ID/Contact Fallback Matching ---
            for id_type, col in [('Ghana Card', 'NIA Number'), ('SSNIT', 'SSNIT Number'), ('Contact', 'Contact')]:
                match, score = find_and_validate_match(scheme_df, col, row[col], name, strict_threshold)
                if match is not None:
                    schedule_df.at[i, 'Scheme Number'] = match['Scheme Number']
                    status.append(f"✅ *Scheme auto-filled ({id_type} match)")
                    match_type = id_type
                    matched_row = match
                    break

            # --- Fuzzy Name Match ---
            if matched_row is None:
                match = process.extractOne(name, filtered_df['clean_name'].tolist(), scorer=fuzz.token_sort_ratio)
                if match:
                    matched_name, score = match
                    if score >= strict_threshold:
                        matched_row = filtered_df[filtered_df['clean_name'] == matched_name].iloc[0]
                        schedule_df.at[i, 'Scheme Number'] = matched_row['Scheme Number']
                        status.append(f"🚫 *Scheme number populated via fuzzy name. Fuzzy score = {round(float(score),2)}%")
                        match_type = "Fuzzy Name"
                    else:
                        status.append("🟡 *Unregistered member")
                else:
                    status.append("🟡 *Unregistered member")

        # --- Optional: Detect mismatched name if ID matched but name differs ---
        if matched_row is not None and fuzz.token_sort_ratio(name, matched_row['clean_name']) < strict_threshold:
            status.append("⚠️ *Name mismatch with matched record")

        # --- Final Status ---
        schedule_df.at[i, 'Status'] = "; ".join(status)
        schedule_df.at[i, 'Match Type'] = match_type
        schedule_df[["SSNIT Number", "NIA Number", "Contact", "Scheme Number"]] = schedule_df[["SSNIT Number", "NIA Number", "Contact", "Scheme Number"]].astype(str).replace("nan", "")

    return schedule_df.fillna("").sort_values(by=["Status", "Member Name"], ascending=[True, True])
