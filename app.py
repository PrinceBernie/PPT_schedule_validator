import streamlit as st
import pandas as pd
import io
import traceback
from validator import validate_schedule
from PIL import Image
import xlsxwriter

# --- Page Config ---
st.set_page_config(
    page_title="Contribution Schedule Validator",
    layout="wide",
    page_icon="📋"
)

# --- Load System Dump ---
@st.cache_data
def load_system_dump():
    """Load the system dump file with error handling"""
    try:
        df = pd.read_excel("Members.xlsx", dtype=str)
        st.success(f"✅ System dump loaded successfully ({len(df):,} records)")
        return df
    except FileNotFoundError:
        st.error("❌ 'Members.xlsx' file not found. Please ensure it's in the same directory as this app.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Failed to load system dump: {e}")
        st.code(traceback.format_exc())
        return pd.DataFrame()

# --- Template Generation Function ---
def generate_schedule_template(employer_name, scheme_type, filtered_df):
    """Generate a blank schedule template with pre-filled member data"""

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('Contribution Schedule')

        # Formats
        white_bg = workbook.add_format({'bg_color': '#FFFFFF'})
        header_format = workbook.add_format({
            'bg_color': '#000000',
            'font_color': '#FFFFFF',
            'bold': True,
            'align': 'left',
            'valign': 'vcenter',
            'border': 1
        })
        left_align_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter'
        })
        right_align_format = workbook.add_format({
            'align': 'right',
            'valign': 'vcenter'
        })

        # Logo
        try:
            worksheet.insert_image('A1', 'ppt_logo.png', {'x_scale': 0.35, 'y_scale': 0.35})
        except Exception:
            worksheet.merge_range('A1:A3', 'LOGO', workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'bg_color': '#F0F0F0'
            }))

        # Header information
        worksheet.write('B1', 'Employer Name:', right_align_format)
        worksheet.write('C1', employer_name, left_align_format)

        worksheet.write('B2', 'ER Number:', right_align_format)
        worksheet.write('C2', 'xxxx', left_align_format)

        worksheet.write('B3', 'Contribution Month:', right_align_format)
        worksheet.write('C3', 'xxxx', left_align_format)

        # Schedule headers
        headers = ['SSNIT Number', 'NIA Number', 'Contact', 'Scheme Number', 'Member Name', 'Salary', 'Tier2 Contribution']
        for col_num, header in enumerate(headers):
            worksheet.write(4, col_num, header, header_format)  # Excel row 5

        if not filtered_df.empty:
            filtered_df = filtered_df.copy()
            filtered_df['NIA Number'] = filtered_df['NIA Number'].fillna("").astype(str)
            filtered_df['SSNIT Number'] = filtered_df['SSNIT Number'].fillna("").astype(str)
            filtered_df['Contact'] = filtered_df['Contact'].fillna("").astype(str)
            filtered_df['Scheme Number'] = filtered_df['Scheme Number'].fillna("").astype(str)
            filtered_df = filtered_df.sort_values(by="FirstName")

            template_data = []
            for _, row in filtered_df.iterrows():
                name_parts = [
                    str(row.get('FirstName', '')) if pd.notna(row.get('FirstName', '')) else '',
                    str(row.get('MiddleName', '')) if pd.notna(row.get('MiddleName', '')) else '',
                    str(row.get('LastName', '')) if pd.notna(row.get('LastName', '')) else ''
                ]
                full_name = ' '.join([part for part in name_parts if part.strip()]).title()

                template_row = [
                    str(row.get('SSNIT Number', '')),
                    str(row.get('NIA Number', '')),
                    str(row.get('Contact', '')),
                    str(row.get('Scheme Number', '')),
                    full_name,
                    '',  # Salary
                    ''   # Tier2 Contribution
                ]
                template_data.append(template_row)

            for row_num, row_data in enumerate(template_data, start=5):
                for col_num, value in enumerate(row_data):
                    worksheet.write(row_num, col_num, value, white_bg)

        worksheet.set_column('A:A', 15)
        worksheet.set_column('B:B', 18)
        worksheet.set_column('C:C', 12)
        worksheet.set_column('D:D', 18)
        worksheet.set_column('E:E', 25)
        worksheet.set_column('F:F', 12)
        worksheet.set_column('G:G', 18)

    return output.getvalue()

# Load system data
system_df = load_system_dump()

# --- UI Layout ---
st.title("📋 Contribution Schedule Validator")
st.markdown("""
* Upload your schedule file, then select the relevant Employer Name and Scheme Type to validate.
""")

# --- Show System Statistics ---
if not system_df.empty:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Members", f"{len(system_df):,}")
    with col2:
        active_members = len(system_df[system_df.get('Status', '') == 'Open']) if 'Status' in system_df.columns else 0
        st.metric("Total Open Accounts", f"{active_members:,}")
    with col3:
        unique_schemes = len(system_df['[Scheme name]'].dropna().unique()) if '[Scheme name]' in system_df.columns else 0
        st.metric("Scheme Types", f"{unique_schemes:,}")

# --- Selection Interface ---
st.markdown("### 🎯 Filter Selection")

employer_name, scheme_type = None, None
col1, col2 = st.columns(2)

with col1:
    if not system_df.empty and 'Group name' in system_df.columns:
        employer_options = sorted(system_df['Group name'].dropna().unique())
        employer_name = st.selectbox(
            "🏢 Select Employer Name",
            employer_options,
            help="Choose the employer/company for validation"
        )
    else:
        st.error("❌ Column 'Group name' not found in system dump.")

with col2:
    if not system_df.empty and '[Scheme name]' in system_df.columns:
        scheme_options = sorted(system_df['[Scheme name]'].dropna().unique())
        scheme_type = st.selectbox(
            "📘 Select Scheme Type",
            scheme_options,
            help="Choose the pension scheme type"
        )
    else:
        st.error("❌ Column '[Scheme name]' not found in system dump.")

# --- Show filtered statistics ---
if employer_name and scheme_type and not system_df.empty:
    filtered_count = len(system_df[
        (system_df['Group name'] == employer_name) &
        (system_df['[Scheme name]'] == scheme_type) &
        (system_df.get('Status', '') == 'Open')
    ])
    st.info(f"📊 **{filtered_count:,} active members** found for {employer_name} under {scheme_type} scheme")

# --- Template Download Section ---
st.markdown("### 📄 Download Blank Schedule Template")
st.markdown("Generate a pre-filled template with member information for the selected employer and scheme.")

if st.button("📥 **GENERATE SCHEDULE TEMPLATE**", type="primary", use_container_width=False):
    if not employer_name or not scheme_type:
        st.error("⚠️ Please select both Employer Name and Scheme Type first.")
    else:
        try:
            system_df_renamed = system_df.rename(columns={
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
            }).copy()

            filtered_df = system_df_renamed[
                (system_df_renamed['Group name'] == employer_name) &
                (system_df_renamed['[Scheme name]'] == scheme_type) &
                (system_df_renamed.get('Status', '') == 'Open')
            ].copy()

            if filtered_df.empty:
                st.error("❌ No active members found for the selected employer and scheme type.")
            else:
                template_data = generate_schedule_template(employer_name, scheme_type, filtered_df)

                st.download_button(
                    label="📥 Download Template (Excel)",
                    data=template_data,
                    file_name=f"Schedule_Template_{employer_name}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help="Download blank schedule template with pre-filled member information"
                )

                st.success(f"✅ Template ready for download! Contains {len(filtered_df)} members.")

        except Exception as e:
            st.error(f"❌ Error generating template: {e}")
            st.code(traceback.format_exc())

# --- File Upload ---
st.markdown("### 📤 Upload Schedule")
schedule_file = st.file_uploader(
    "Upload Contribution Schedule (.xlsx)",
    type=["xlsx"],
    help="Upload Excel file with columns: SSNIT Number, NIA Number, Contact, Scheme Number, Member Name, Salary, Tier2 Contribution"
)

# --- Preview uploaded file ---
schedule_df = pd.DataFrame()

if schedule_file:
    try:
        # Force all uploaded columns to string first to preserve identifiers
        schedule_df = pd.read_excel(schedule_file, dtype=str)

        expected_cols = 7
        if len(schedule_df.columns) != expected_cols:
            st.warning(f"⚠️ Expected {expected_cols} columns, found {len(schedule_df.columns)}. Please verify your file format.")

        # Standard column names
        schedule_df.columns = [
            'SSNIT Number', 'NIA Number', 'Contact', 'Scheme Number',
            'Member Name', 'Salary', 'Tier2 Contribution'
        ]

        # Preserve text columns as text
        text_cols = ['SSNIT Number', 'NIA Number', 'Contact', 'Scheme Number', 'Member Name']
        for col in text_cols:
            schedule_df[col] = schedule_df[col].astype('string')

        st.markdown("### 📄 Schedule Preview")
        st.dataframe(schedule_df, use_container_width=True)

        # Safer numeric stats
        salary_numeric = pd.to_numeric(schedule_df['Salary'], errors='coerce')
        tier2_numeric = pd.to_numeric(schedule_df['Tier2 Contribution'], errors='coerce')

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Records", len(schedule_df))
        with col2:
            total_tier2 = tier2_numeric.sum()
            st.metric("Total Contribution", f"GHS {total_tier2:,.2f}" if pd.notna(total_tier2) else "N/A")
        with col3:
            empty_schemes = schedule_df['Scheme Number'].isna().sum() + (schedule_df['Scheme Number'].astype(str).str.strip() == "").sum()
            st.metric("Empty Scheme Numbers", int(empty_schemes))

    except Exception as e:
        st.error(f"❌ Error reading schedule file: {e}")
        st.code(traceback.format_exc())
        st.info("💡 Please ensure your Excel file has the correct format and structure.")

# --- Validation Interface ---
st.markdown("### ⚡ Run Validation")

if st.button("**VALIDATE SCHEDULE**", type="primary", use_container_width=True):
    if schedule_df.empty:
        st.error("⚠️ Please upload a valid schedule file.")
    elif not employer_name or not scheme_type:
        st.error("⚠️ Please select both Employer Name and Scheme Type.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            status_text.text("🔄 Preparing system data...")
            progress_bar.progress(20)

            system_df_renamed = system_df.rename(columns={
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
            }).copy()

            progress_bar.progress(40)
            status_text.text("🎯 Filtering data by scheme and employer...")

            scheme_only_df = system_df_renamed.loc[
                (system_df_renamed['[Scheme name]'] == scheme_type) &
                (system_df_renamed['Status'] == 'Open')
            ].copy()

            employer_filtered_df = scheme_only_df.loc[
                scheme_only_df['Group name'] == employer_name
            ].copy()

            progress_bar.progress(60)

            if scheme_only_df.empty:
                st.error("❌ No active records found for selected scheme type.")
            elif employer_filtered_df.empty:
                st.error("❌ No active records found for selected employer in this scheme.")
            else:
                status_text.text("🔍 Running enhanced validation...")
                progress_bar.progress(80)

                validated = validate_schedule(
                    schedule_df.copy(),
                    employer_filtered_df.copy(),
                    scheme_only_df.copy()
                )

                progress_bar.progress(100)
                status_text.text("✅ Validation completed successfully!")

                st.markdown("### 📊 Validation Results")

                validation_status = validated['Validation Status']

                # --- Summary Metrics (4 columns) ---
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    valid_count = len([s for s in validation_status.values if '✅' in str(s)])
                    st.metric("✅ Populated Scheme Numbers", valid_count, delta=f"{valid_count/len(validated)*100:.1f}%")
                with col2:
                    error_count = len([s for s in validation_status.values if '❌' in str(s)])
                    st.metric("❌ Error Records", error_count, delta=f"{error_count/len(validated)*100:.1f}%")
                with col3:
                    unregistered_count = len([s for s in validation_status.values if 'Unregistered member' in str(s)])
                    st.metric("🟡 Suspense", unregistered_count, delta=f"{unregistered_count/len(validated)*100:.1f}%")
                with col4:
                    fuzzy_count = len([s for s in validation_status.values if 'FUZZY' in str(s)])
                    st.metric("⚠️ Fuzzy Matches (Review)", fuzzy_count, delta=f"{fuzzy_count/len(validated)*100:.1f}%")

                # --- Fuzzy Match Warning Banner ---
                if fuzzy_count > 0:
                    st.warning(
                        f"⚠️ **{fuzzy_count} record(s) were matched using fuzzy name matching within the selected employer only.** "
                        f"No identifier match (Ghana Card, SSNIT, Contact) was found for these records — name similarity was the sole basis. "
                        f"Please manually verify all records flagged with **⚠️🔎 FUZZY** before uploading the schedule. "
                        f"Note: cross-employer fuzzy matching has been disabled to prevent misallocation."
                    )

                st.markdown("### 📋 Validated Schedule")

                columns_to_display = [
                    'SSNIT Number', 'NIA Number', 'Contact', 'Scheme Number',
                    'Member Name', 'Salary', 'Tier2 Contribution', 'Validation Status'
                ]

                display_df = validated.copy()[columns_to_display]

                st.dataframe(
                    display_df,
                    use_container_width=True,
                    height=400
                )

                st.markdown("### 📥 Download Results")

                col1, col2, col3 = st.columns(3)

                with col1:
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        validated.to_excel(writer, index=True, sheet_name='Validated_Results', index_label="S/N")

                        summary_df = pd.DataFrame({
                            'Status': validated['Validation Status'].value_counts().index,
                            'Count': validated['Validation Status'].value_counts().values,
                            'Percentage': (validated['Validation Status'].value_counts().values / len(validated) * 100).round(2)
                        })
                        summary_df.to_excel(writer, index=False, sheet_name='Summary')

                    st.download_button(
                        label="📊 Download Full Validated Results (Excel)",
                        data=output.getvalue(),
                        file_name=f"validated_schedule_{employer_name.split()[0]}_{scheme_type}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        help="Download complete validation results with summary"
                    )

                with col2:
                    errors_df = validated[validated['Validation Status'].str.contains("🟡", na=False)]
                    if not errors_df.empty:
                        errors_output = io.BytesIO()
                        with pd.ExcelWriter(errors_output, engine='xlsxwriter') as writer:
                            errors_df.to_excel(writer, index=True, sheet_name='Suspense Members', index_label="S/N")

                        st.download_button(
                            label="⚠️ Download Unregistered Members Only (Excel)",
                            data=errors_output.getvalue(),
                            file_name=f"SUSPENSE_{employer_name.split()[0]}_{scheme_type}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            help="Download only records with validation errors"
                        )
                    else:
                        st.success("🎉 No suspense found! Please inspect output before uploading.")

                with col3:
                    fuzzy_df = validated[validated['Validation Status'].str.contains("FUZZY", na=False)]
                    if not fuzzy_df.empty:
                        fuzzy_output = io.BytesIO()
                        with pd.ExcelWriter(fuzzy_output, engine='xlsxwriter') as writer:
                            fuzzy_df.to_excel(writer, index=True, sheet_name='Fuzzy Matches', index_label="S/N")

                        st.download_button(
                            label="⚠️🔎 Download Fuzzy Matches for Review (Excel)",
                            data=fuzzy_output.getvalue(),
                            file_name=f"FUZZY_REVIEW_{employer_name.split()[0]}_{scheme_type}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            help="Employer-scoped fuzzy name matches only — no identifier found; manual verification required before upload"
                        )
                    else:
                        st.success("✅ No fuzzy-only matches found.")

        except Exception as e:
            progress_bar.progress(0)
            status_text.text("")
            st.error(f"❌ Error during validation: {str(e)}")
            st.code(traceback.format_exc())
            st.info("💡 Please check your file format and try again. Contact support if the issue persists.")

# --- Footer ---
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.8em;'>
    <p>Peoples Pension Trust Contribution Schedule Validator | Powered by Multi-Identifier Matching</p>
    <p>For support or questions, contact PPT compliance (compliance@peoplespensiontrust.com)</p>
</div>
""", unsafe_allow_html=True)
