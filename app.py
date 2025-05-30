import streamlit as st
import pandas as pd
from validator import validate_schedule

st.set_page_config(
    page_title="Contribution Schedule Validator",
    layout="wide"
)

# --- Preload System Dump File Once ---
@st.cache_data
def load_system_dump():
    try:
        dump_df = pd.read_excel("Members.xlsx")  # Place the dump file in the same directory
        return dump_df
    except Exception as e:
        st.error(f"Failed to load system dump: {e}")
        return pd.DataFrame()

# --- Load System Dump at Startup ---
dump_df = load_system_dump()

# --- Title & Instructions ---
st.title("📋 Contribution Schedule Validator")
st.markdown("""
Upload only the **schedule file** below.  
Then select your **Employer Name** and **Scheme Type** to run the validation.
""")

# --- Dropdown Selectors (Populated from Dump) ---
employer_name = ""
scheme_type = ""
employer_options = []
scheme_options = []

if not dump_df.empty:
    if 'Group name' in dump_df.columns:
        employer_options = sorted(dump_df['Group name'].dropna().unique().tolist())
        employer_name = st.selectbox("🏢 Select Employer Name", employer_options, key="employer_select")
    else:
        st.warning("❗ 'Group name' column not found in system dump.")

    if '[Scheme name]' in dump_df.columns:
        scheme_options = sorted(dump_df['[Scheme name]'].dropna().unique().tolist())
        scheme_type = st.selectbox("📘 Select Scheme Type", scheme_options, key="scheme_select")
    else:
        st.warning("❗ '[Scheme name]' column not found in system dump.")

# --- Schedule Upload ---
schedule_file = st.file_uploader("📤 Upload Contribution Schedule (.xlsx)", type=["xlsx"], key="schedule")

# --- Run Validation ---
if st.button("✅ Run Validation"):
    if schedule_file is None:
        st.error("Please upload a schedule file.")
    elif not employer_name or not scheme_type:
        st.error("Please select both Employer Name and Scheme Type.")
    else:
        try:
            schedule_df = pd.read_excel(schedule_file)

            # --- Filter Dump by Employer and Scheme Type ---
            filtered_dump = dump_df.copy()
            if 'Group name' in filtered_dump.columns:
                filtered_dump = filtered_dump[filtered_dump['Group name'] == employer_name]
            if '[Scheme name]' in filtered_dump.columns:
                filtered_dump = filtered_dump[filtered_dump['[Scheme name]'] == scheme_type]

            if filtered_dump.empty:
                st.warning("⚠️ No matching records found in system data for selected Employer and Scheme.")
            else:
                validated_df = validate_schedule(schedule_df, filtered_dump)

                st.success("🎉 Validation Complete!")
                st.dataframe(validated_df[['SSNIT Number',
                                           'NIA Number',
                                           'Contact',
                                           'Scheme Number',
                                           'Member Name', 
                                           'Salary',
                                           'Tier2 Contribution', 
                                           'Status']], use_container_width=True)

                import io

                # Create in-memory buffer
                output = io.BytesIO()

                # Write DataFrame to Excel in-memory
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    validated_df.to_excel(writer, index=True, sheet_name='Validated', index_label = "S/N")

                # Get Excel binary data
                excel_data = output.getvalue()

                st.download_button(
                    label="📥 Download Validated Results (Excel)",
                    data=excel_data,
                    file_name= f"validated_schedule_{employer_name}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        except Exception as e:
            st.error(f"❌ Unexpected error during validation: {e}")
