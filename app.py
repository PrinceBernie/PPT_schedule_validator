import streamlit as st
import pandas as pd
import io
from validator import validate_schedule

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
        df = pd.read_excel("Members.xlsx")
        st.success(f"✅ System dump loaded successfully ({len(df):,} records)")
        return df
    except FileNotFoundError:
        st.error("❌ 'Members.xlsx' file not found. Please ensure it's in the same directory as this app.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Failed to load system dump: {e}")
        return pd.DataFrame()

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
        schedule_df = pd.read_excel(schedule_file)
        
        # Validate expected columns
        expected_cols = 7
        if len(schedule_df.columns) != expected_cols:
            st.warning(f"⚠️ Expected {expected_cols} columns, found {len(schedule_df.columns)}. Please verify your file format.")
        
        # Assign standard column names
        schedule_df.columns = [
            'SSNIT Number', 'NIA Number', 'Contact', 'Scheme Number',
            'Member Name', 'Salary', 'Tier2 Contribution'
        ]
        
        st.markdown("### 📄 Schedule Preview")
        st.dataframe(
            schedule_df, 
            use_container_width=True)
        
        # Show basic statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Records", len(schedule_df))
        with col2:
            total_tier2 = schedule_df['Tier2 Contribution'].sum() if 'Salary' in schedule_df.columns else 0
            st.metric("Total Contribution", f"GHS {total_tier2:,.2f}" if pd.notna(total_tier2) else "N/A")
        with col3:
            empty_schemes = schedule_df['Scheme Number'].isna().sum() if 'Scheme Number' in schedule_df.columns else 0
            st.metric("Empty Scheme Numbers", empty_schemes)
            
    except Exception as e:
        st.error(f"❌ Error reading schedule file: {e}")
        st.info("💡 Please ensure your Excel file has the correct format and structure.")

# --- Validation Interface ---
st.markdown("### ⚡ Run Validation")

# Validation button with enhanced styling
if st.button("**VALIDATE SCHEDULE**", type="primary", use_container_width=True):
    
    # Pre-validation checks
    if schedule_df.empty:
        st.error("⚠️ Please upload a valid schedule file.")
    elif not employer_name or not scheme_type:
        st.error("⚠️ Please select both Employer Name and Scheme Type.")
    else:
        # Show progress
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("🔄 Preparing system data...")
            progress_bar.progress(20)
            
            # Column mapping for system data
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
            })
            
            progress_bar.progress(40)
            status_text.text("🎯 Filtering data by scheme and employer...")
            
            # Filter system dump
            scheme_only_df = system_df_renamed.loc[
                (system_df_renamed['[Scheme name]'] == scheme_type) & 
                (system_df_renamed['Status'] == 'Open')
            ]
            
            employer_filtered_df = scheme_only_df.loc[
                scheme_only_df['Group name'] == employer_name
            ]

            progress_bar.progress(60)
            
            # Validation checks
            if scheme_only_df.empty:
                st.error("❌ No active records found for selected scheme type.")
            elif employer_filtered_df.empty:
                st.error("❌ No active records found for selected employer in this scheme.")
            else:
                status_text.text("🔍 Running enhanced validation...")
                progress_bar.progress(80)
                
                # Run validation
                validated = validate_schedule(
                    schedule_df.copy(), 
                    employer_filtered_df.copy(), 
                    scheme_only_df.copy()
                )
                
                progress_bar.progress(100)
                status_text.text("✅ Validation completed successfully!")
                
                # Results Analysis
                st.markdown("### 📊 Validation Results")
                
                # Status summary
                validation_status = validated['Validation Status']
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    valid_count = len([s for s in validation_status.values if '✅' in s])
                    st.metric("✅ Populated Scheme numbers", valid_count, delta=f"{valid_count/len(validated)*100:.1f}%")
                
                with col2:
                    error_count = len([s for s in validation_status.values if '❌' in s])
                    st.metric("❌ Error Records", error_count, delta=f"{error_count/len(validated)*100:.1f}%")
                
                with col3:
                    unregistered_count = len([s for s in validation_status.values if 'Unregistered member' in s])
                    st.metric("🟡 Suspense", unregistered_count, delta=f"{unregistered_count/len(validated)*100:.1f}%")

                # Detailed results table
                st.markdown("### 📋 Validated Schedule")
                
                # Select fixed columns to display
                columns_to_display = [
                    'SSNIT Number', 'NIA Number', 'Contact', 'Scheme Number',
                    'Member Name', 'Salary', 'Tier2 Contribution', 'Validation Status']

                # Prepare display DataFrame
                display_df = validated.copy()
                display_df = display_df[columns_to_display]

                
                # Display results
                st.dataframe(
                    display_df, 
                    use_container_width=True,
                    height=400
                )

                # Download section
                st.markdown("### 📥 Download Results")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Full results download
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        validated.to_excel(writer, index=True, sheet_name='Validated_Results', index_label="S/N")
                        
                        # Add summary sheet
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
                    # Errors only download
                    errors_df = validated[validated['Validation Status'].str.contains("🟡", na=False)]
                    if not errors_df.empty:
                        errors_output = io.BytesIO()
                        with pd.ExcelWriter(errors_output, engine='xlsxwriter') as writer:
                            errors_df.to_excel(writer, index=True, sheet_name='Suspense Members', index_label="S/N")
                        
                        st.download_button(
                            label="⚠️ Download unregistered members schedule ONLY (Excel)",
                            data=errors_output.getvalue(),
                            file_name=f"SUSPENSE_{employer_name.split()[0]}_{scheme_type}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            help="Download only records with validation errors"
                        )
                    else:
                        st.success("🎉 No suspense found! Please inspect output before uploading.")

        except Exception as e:
            progress_bar.progress(0)
            status_text.text("")
            st.error(f"❌ Error during validation: {str(e)}")
            st.info("💡 Please check your file format and try again. Contact support if the issue persists.")

# --- Footer ---
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.8em;'>
    <p>Peoples Pension Trust Contribution Schedule Validator | Powered by Advanced Fuzzy Matching</p>
    <p>For support or questions, contact PPT compliance (compliance@peoplespensiontrust.com)</p>
</div>
""", unsafe_allow_html=True)
