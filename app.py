import streamlit as st
import pandas as pd
import io
from validator import validate_schedule

# --- Page Config ---
st.set_page_config(page_title="Contribution Schedule Validator", layout="wide")

# --- Load System Dump ---
@st.cache_data
def load_system_dump():
    try:
        df = pd.read_excel("Members.xlsx")
        return df
    except Exception as e:
        st.error(f"❌ Failed to load system dump: {e}")
        return pd.DataFrame()

system_df = load_system_dump()

# --- UI Layout ---
st.title("📋 Contribution Schedule Validator")
st.markdown("""
Upload your **schedule file**, then select the relevant **Employer Name** and **Scheme Type** to validate.
""")

# --- Dropdowns ---
employer_name, scheme_type = None, None
if not system_df.empty:
    if 'Group name' in system_df.columns:
        employer_name = st.selectbox("🏠 Select Employer Name", sorted(system_df['Group name'].dropna().unique()))
    else:
        st.warning("Column 'Group name' not found in system dump.")

    if '[Scheme name]' in system_df.columns:
        scheme_type = st.selectbox("📘 Select Scheme Type", sorted(system_df['[Scheme name]'].dropna().unique()))
    else:
        st.warning("Column '[Scheme name]' not found in system dump.")

# --- Upload Schedule ---
schedule_file = st.file_uploader("📝 Upload Contribution Schedule (.xlsx)", type=["xlsx"])

if schedule_file:
    try:
        schedule_df = pd.read_excel(schedule_file)
        schedule_df.columns = ['SSNIT Number', 
                               'NIA Number', 
                               'Contact', 
                               'Scheme Number',
                               'Member Name', 
                               'Salary', 
                               'Tier2 Contribution']
        st.markdown("### 🔍 Preview Uploaded Schedule")
        st.dataframe(schedule_df, use_container_width=True)
    except Exception as e:
        st.error(f"❌ Error reading schedule file: {e}")
        schedule_df = pd.DataFrame()
else:
    schedule_df = pd.DataFrame()

# --- Run Validation ---
if st.button("✅ Run Validation"):
    if schedule_df.empty:
        st.error("⚠️ Please upload a valid schedule file.")
    elif not employer_name or not scheme_type:
        st.error("⚠️ Please select both Employer Name and Scheme Type.")
    else:
        try:
            system_df = system_df.rename(columns={
        'Creation time': 'Creation Time', 'Start date': 'Start Date', 'Region': 'Region',
        'Gender': 'Gender', 'First name': 'FirstName', '[Middle name]': 'MiddleName',
        '[Last name]': 'LastName', 'Member number': 'Member Number', '[Scheme number]': 'Scheme Number',
        'Mobile': 'Contact', 'Date of birth': 'DOB',
        '[Agent name]': 'Agent Name', 'Place of birth': 'Place of Birth',
        'S s n i t': 'SSNIT Number', '[IDType]': 'ID Type', 'Id number': 'NIA Number',
        'Residential address': 'Residential Address', 'Digital address code': 'Digital Address',
        'Postal address': 'Postal Address', 'Landmark': 'Landmark', 'Email': 'Email',
        'Home town': 'HomeTown', 'Marital status': 'Marital Status', 'Country': 'Country',
        'Occupation': 'Occupation', 'Status': 'Status'
    })
            
            # --- Filter system dump ---
            scheme_only_df = system_df[(system_df['[Scheme name]'] == scheme_type) & (system_df['Status'] == 'Open')]
            employer_filtered_df = scheme_only_df[scheme_only_df['Group name'] == employer_name]

            if scheme_only_df.empty:
                st.warning("⚠️ No records found for selected scheme type.")
            elif employer_filtered_df.empty:
                st.warning("⚠️ No records found for selected employer in this scheme.")
            else:
                validated = validate_schedule(schedule_df.copy(), employer_filtered_df.copy(), scheme_only_df.copy())
                st.success("✔ Validation complete!")

                st.markdown("### 📊 Validated Results")
                st.dataframe(validated[[
                    'SSNIT Number', 'NIA Number', 'Contact', 'Scheme Number',
                    'Member Name', 'Salary', 'Tier2 Contribution', 'Validation Status'
                ]], use_container_width=True)

                # --- Download Button ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    validated.to_excel(writer, index=True, sheet_name='Validated', index_label = "S/N")
                st.download_button(
                    label="📥 Download Validated Excel",
                    data=output.getvalue(),
                    file_name=f"validated_schedule_{employer_name}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        except Exception as e:
            st.error(f"❌ Error during validation: {e}")
