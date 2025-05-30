import streamlit as st
import pandas as pd
import io
from validator import validate_schedule

# --- Page Config ---
st.set_page_config(
    page_title="Contribution Schedule Validator",
    layout="wide"
)

# --- Load System Dump Once ---
@st.cache_data
def load_system_dump():
    try:
        dump_df = pd.read_excel("Members.xlsx")  # Make sure this file is in the same folder
        return dump_df
    except Exception as e:
        st.error(f"❌ Failed to load system dump: {e}")
        return pd.DataFrame()

# --- Load at Startup ---
dump_df = load_system_dump()

# --- App Title & Instructions ---
st.title("📋 Contribution Schedule Validator")
st.markdown("""
Upload the **schedule file** only.  
Then select the relevant **Employer Name** and **Scheme Type** to validate.
""")

# --- Dropdown Selections ---
employer_name = ""
scheme_type = ""
employer_options = []
scheme_options = []

if not dump_df.empty:
    if 'Group name' in dump_df.columns:
        employer_options = sorted(dump_df['Group name'].dropna().unique().tolist())
        employer_name = st.selectbox("🏢 Select Employer Name", employer_options, key="employer_select")
    else:
        st.warning("❗ Column 'Group name' not found in system dump.")

    if '[Scheme name]' in dump_df.columns:
        scheme_options = sorted(dump_df['[Scheme name]'].dropna().unique().tolist())
        scheme_type = st.selectbox("📘 Select Scheme Type", scheme_options, key="scheme_select")
    else:
        st.warning("❗ Column '[Scheme name]' not found in system dump.")

# --- Upload Schedule File ---
schedule_file = st.file_uploader("📤 Upload Contribution Schedule (.xlsx)", type=["xlsx"])

# --- Preview Uploaded File ---
if schedule_file:
    try:
        schedule_df = pd.read_excel(schedule_file)
        st.markdown("### 📄 Preview Uploaded Schedule")
        st.dataframe(schedule_df.head(), use_container_width=True)
    except Exception as e:
        st.error(f"❌ Error reading uploaded file: {e}")
        schedule_df = pd.DataFrame()
else:
    schedule_df = pd.DataFrame()

# --- Run Validation Button ---
if st.button("✅ Run Validation"):
    if schedule_df.empty:
        st.error("⚠️ Please upload a valid schedule file.")
    elif not employer_name or not scheme_type:
        st.error("⚠️ Please select both Employer Name and Scheme Type.")
    else:
        try:
            # --- Filter system dump for matching scheme ---
            scheme_only_dump = dump_df[dump_df['[Scheme name]'] == scheme_type].copy()

            if scheme_only_dump.empty:
                st.warning("⚠️ No records found in system data for selected scheme type.")
            else:
                # --- Further filter by employer for fuzzy matching ---
                filtered_dump = scheme_only_dump[scheme_only_dump['Group name'] == employer_name].copy()

                # --- Validate Schedule ---
                validated_df = validate_schedule(schedule_df, filtered_dump, scheme_only_dump)

                # --- Sort by Status for better visibility ---
                validated_df = validated_df.sort_values(by="Status")

                # --- Highlight Invalid Rows ---
                def highlight_invalid(row):
                    return ['background-color: #fdd' if 'Invalid' in str(row['Status']) else '' for _ in row]

                st.success("🎉 Validation Complete!")
                st.dataframe(
                    validated_df[[
                        'SSNIT Number', 'NIA Number', 'Contact', 'Scheme Number',
                        'Member Name', 'Salary', 'Tier2 Contribution', 'Status'
                    ]].style.apply(highlight_invalid, axis=1),
                    use_container_width=True
                )

                # --- Excel Download ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    validated_df.to_excel(writer, index=True, sheet_name='Validated', index_label="S/N")
                excel_data = output.getvalue()

                st.download_button(
                    label="📥 Download Validated Results (Excel)",
                    data=excel_data,
                    file_name=f"validated_schedule_{employer_name}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        except Exception as e:
            st.error(f"❌ Unexpected error during validation: {e}")
