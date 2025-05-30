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
    strict_threshold, loose_threshold = 50, 50

    # --- Rename & Clean Dump Columns for both filtered_df and scheme_df ---
    rename_map  = {
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

    for df in [filtered_df, scheme_df]:
        df.rename(columns=rename_map, inplace=True)
        df['clean_name'] = clean_name(build_full_name(df))
        df['NIA Number'] = df['NIA Number'].astype(str).str.strip().str.replace(r"[^\w]", "", regex=True)
        df['SSNIT Number'] = df['SSNIT Number'].astype(str).str.strip().str.replace(r"[^\w]", "", regex=True)
        df['Contact'] = pd.to_numeric(df['Contact'], errors='coerce')

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

    for i, row in schedule_df.iterrows():
        status = []
        name = row['clean_name']
        scheme = row['Scheme Number']
        gh_card = row['NIA Number']
        ssnit = row['SSNIT Number']
        contact = row['Contact']
        salary = row['Salary']
        tier2 = row['Tier2 Contribution']

        # === Step 1: Salary and 5% Contribution ===
        if pd.isna(salary) or pd.isna(tier2):
            schedule_df.at[i, 'Status'] = "❌ *Missing salary or contribution"
            continue

        if not (539.8 <= salary <= 61000):
            schedule_df.at[i, 'Status'] = "❌ *Invalid salary range. (min sal: GHS 539.80, max sal: GHS 61,000.00)"
            continue

        expected = round(salary * 0.05, 2)
        if (abs(round(tier2, 2) - expected) > 0.5) and ("ops" in str(scheme).lower()):
            schedule_df.at[i, 'Status'] = f"❌ *Incorrect Tier2 5% computation (expected {expected:.2f})"
            continue

        # === Step 2: Scheme Number or Fallback Matching ===
        fallback_match = None

        # Direct Scheme Match
        if scheme and len(scheme) == 13 and scheme.startswith("1010"):
            match_row = scheme_df[scheme_df['Scheme Number'] == scheme]
            if not match_row.empty:
                db_name = match_row.iloc[0]['clean_name']
                similarity = fuzz.token_sort_ratio(name, db_name)
                if similarity >= loose_threshold:
                    status.append("✅ Valid Scheme ID & Name Match")
                else:
                    status.append("❌ *Scheme number Assigned to Different Member")
            else:
                status.append("❌ *Scheme number Not Found in System")
        else:
            # --- Fallbacks: Search in scheme-level dump ---
            for id_type, col in [('Ghana Card', 'NIA Number'), ('SSNIT', 'SSNIT Number'), ('Contact', 'Contact')]:
                db_row, score = find_and_validate_match(scheme_df, col, row[col], name, strict_threshold)
                if db_row is not None:
                    fallback_match = db_row
                    schedule_df.at[i, 'Scheme Number'] = db_row['Scheme Number']
                    status.append(f"✅ *Scheme auto-filled ({id_type} match)")
                    break  # Stop at first valid fallback

            # Fuzzy Name Match
            if fallback_match is None:
                match = process.extractOne(name, filtered_df['clean_name'].tolist(), scorer=fuzz.token_sort_ratio)
                if match:
                    matched_name, score = match
                    if score >= strict_threshold:
                        matched_row = filtered_df[filtered_df['clean_name'] == matched_name].iloc[0]
                        schedule_df.at[i, 'Scheme Number'] = matched_row['Scheme Number']
                        status.append("🚫 *Scheme number populated via fuzzy name search")
                    else:
                        status.append("🟡 *Unregistered member")
                else:
                    status.append("🟡 *Unregistered member")

        # Save Status
        schedule_df.at[i, 'Status'] = "; ".join(status)

    return schedule_df.sort_values(by=["Status", "Member Name"], ascending=[False, True])
