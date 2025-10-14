import streamlit as st
import pandas as pd
import io
from validator import validate_schedule
from PIL import Image
import xlsxwriter

# --- Page Config ---
st.set_page_config(
    page_title="Contribution Schedule Validator", 
    layout="wide",
    page_icon="📋",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Modern UI ---
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    .main {
        padding-top: 1rem;
    }
    
    /* Custom Header */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 1.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        color: white;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    
    .main-header h1 {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 2.5rem;
        margin: 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    
    .main-header p {
        font-family: 'Inter', sans-serif;
        font-size: 1.1rem;
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }
    
    /* Card Components */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
    }
    
    .section-card {
        background: white;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        margin-bottom: 2rem;
        border: 1px solid #e1e5e9;
    }
    
    .section-title {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 1.3rem;
        color: #2c3e50;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Metrics Styling */
    .metric-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }
    
    .metric-value {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 2rem;
        color: #2c3e50;
    }
    
    .metric-label {
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        color: #7f8c8d;
        font-size: 0.9rem;
    }
    
    /* Button Styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 2px 10px rgba(102, 126, 234, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
    }
    
    .primary-button {
        background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%) !important;
        box-shadow: 0 2px 10px rgba(231, 76, 60, 0.3) !important;
    }
    
    .primary-button:hover {
        box-shadow: 0 4px 20px rgba(231, 76, 60, 0.4) !important;
    }
    
    /* File Upload Styling */
    .uploadedFile {
        background: #f8f9fa;
        border: 2px dashed #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    /* Progress Bar Styling */
    .stProgress > div > div > div > div {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Status Messages */
    .success-message {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .error-message {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .warning-message {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .info-message {
        background: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    /* Data Table Styling */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
    }
    
    /* Sidebar Styling */
    .css-1d391kg {
        background: #f8f9fa;
    }
    
    /* Footer Styling */
    .footer {
        text-align: center;
        color: #6c757d;
        font-size: 0.9rem;
        margin-top: 3rem;
        padding: 2rem;
        border-top: 1px solid #e9ecef;
    }
    
    /* Responsive Design */
    @media (max-width: 768px) {
        .main-header h1 {
            font-size: 2rem;
        }
        
        .metric-value {
            font-size: 1.5rem;
        }
    }
</style>
""", unsafe_allow_html=True)

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

# --- Template Generation Function ---
def generate_schedule_template(employer_name, scheme_type, filtered_df):
    """Generate a blank schedule template with pre-filled member data"""
    
    # Create Excel file in memory
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Create worksheet
        workbook = writer.book
        worksheet = workbook.add_worksheet('Contribution Schedule')
        
        # Set up formats
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
        
        # Fill entire sheet with white background
        #worksheet.set_column('A:Z', 15, white_bg)
        
        # Insert logo (A1:B3) - we'll handle this as a merged cell with text for now
        # Note: In production, you'd use worksheet.insert_image() with actual logo file
        try:
            # Try to insert actual logo if file exists
            worksheet.insert_image('A1', 'ppt_logo.png', {'x_scale': 0.35, 'y_scale': 0.35})
        except:
            # Fallback: merged cell with "LOGO" text
            worksheet.merge_range('A1:A3', 'LOGO', workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'bg_color': '#F0F0F0'
            }))
        
        # Header information (C1:D3)
        worksheet.write('B1', 'Employer Name:', right_align_format)
        worksheet.write('C1', employer_name, left_align_format)
        
        worksheet.write('B2', 'ER Number:', right_align_format)
        worksheet.write('C2', 'xxxx', left_align_format)
        
        worksheet.write('B3', 'Contribution Month:', right_align_format)
        worksheet.write('C3', 'xxxx', left_align_format)
        
        # Schedule headers starting from row 5 (A5)
        headers = ['SSNIT Number', 'NIA Number', 'Contact', 'Scheme Number', 'Member Name', 'Salary', 'Tier2 Contribution']
        for col_num, header in enumerate(headers):
            worksheet.write(4, col_num, header, header_format)  # Row 5 is index 4
        
        # Prepare member data
        if not filtered_df.empty:
            filtered_df['NIA Number'] = filtered_df['NIA Number'].fillna("")
            filtered_df['SSNIT Number'] = filtered_df['SSNIT Number'].fillna('')
            filtered_df = filtered_df.sort_values(by = "FirstName")

            # Create template data with first 5 columns filled, last 2 blank
            template_data = []
            for _, row in filtered_df.iterrows():
                # Build full name
                name_parts = [
                    str(row.get('FirstName', '')) if pd.notna(row.get('FirstName', '')) else '',
                    str(row.get('MiddleName', '')) if pd.notna(row.get('MiddleName', '')) else '',
                    str(row.get('LastName', '')) if pd.notna(row.get('LastName', '')) else ''
                ]
                # Filter out empty strings and join with single spaces
                full_name = ' '.join([part for part in name_parts if part.strip()])
                full_name = full_name.title()
                
                template_row = [
                    str(row.get('SSNIT Number', '')),
                    str(row.get('NIA Number', '')),
                    str(row.get('Contact', '')),
                    str(row.get('Scheme Number', '')),
                    full_name,
                    '',  # Salary - blank
                    ''   # Tier2 Contribution - blank
                ]
                template_data.append(template_row)
            
            # Write data starting from row 6 (index 5)
            for row_num, row_data in enumerate(template_data, start=5):
                for col_num, value in enumerate(row_data):
                    worksheet.write(row_num, col_num, value, white_bg)
        
        # Auto-fit columns
        worksheet.set_column('A:A', 15)  # SSNIT Number
        worksheet.set_column('B:B', 18)  # NIA Number
        worksheet.set_column('C:C', 12)  # Contact
        worksheet.set_column('D:D', 15)  # Scheme Number
        worksheet.set_column('E:E', 25)  # Member Name
        worksheet.set_column('F:F', 12)  # Salary
        worksheet.set_column('G:G', 15)  # Tier2 Contribution
    
    return output.getvalue()

# Load system data
system_df = load_system_dump()

# --- Sidebar Navigation ---
with st.sidebar:
    st.markdown("## 🧭 Navigation")
    st.markdown("---")
    
    # Quick stats in sidebar
    if not system_df.empty:
        st.markdown("### 📊 Quick Stats")
        st.metric("Total Members", f"{len(system_df):,}")
        active_members = len(system_df[system_df.get('Status', '') == 'Open']) if 'Status' in system_df.columns else 0
        st.metric("Active Members", f"{active_members:,}")
        unique_schemes = len(system_df['[Scheme name]'].dropna().unique()) if '[Scheme name]' in system_df.columns else 0
        st.metric("Scheme Types", f"{unique_schemes:,}")
    
    st.markdown("---")
    st.markdown("### 💡 Help")
    st.markdown("""
    **How to use:**
    1. Select employer and scheme
    2. Download template (optional)
    3. Upload your schedule
    4. Run validation
    5. Download results
    """)
    
    st.markdown("---")
    st.markdown("### 📞 Support")
    st.markdown("**Email:** compliance@peoplespensiontrust.com")

# --- Main Header ---
st.markdown("""
<div class="main-header">
    <h1>📋 Contribution Schedule Validator</h1>
    <p>Upload your schedule file, then select the relevant Employer Name and Scheme Type to validate.</p>
</div>
""", unsafe_allow_html=True)

# --- System Statistics Cards ---
if not system_df.empty:
    st.markdown("### 📊 System Overview")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-container">
                <div>
                    <div class="metric-label">Total Members</div>
                    <div class="metric-value">{:,}</div>
                </div>
                <div style="font-size: 2rem;">👥</div>
            </div>
        </div>
        """.format(len(system_df)), unsafe_allow_html=True)
    
    with col2:
        active_members = len(system_df[system_df.get('Status', '') == 'Open']) if 'Status' in system_df.columns else 0
        st.markdown("""
        <div class="metric-card">
            <div class="metric-container">
                <div>
                    <div class="metric-label">Active Members</div>
                    <div class="metric-value">{:,}</div>
                </div>
                <div style="font-size: 2rem;">✅</div>
            </div>
        </div>
        """.format(active_members), unsafe_allow_html=True)
    
    with col3:
        unique_schemes = len(system_df['[Scheme name]'].dropna().unique()) if '[Scheme name]' in system_df.columns else 0
        st.markdown("""
        <div class="metric-card">
            <div class="metric-container">
                <div>
                    <div class="metric-label">Scheme Types</div>
                    <div class="metric-value">{:,}</div>
                </div>
                <div style="font-size: 2rem;">📋</div>
            </div>
        </div>
        """.format(unique_schemes), unsafe_allow_html=True)


# --- Filter Selection Card ---
st.markdown("""
<div class="section-card">
    <div class="section-title">
        🎯 Filter Selection
    </div>
""", unsafe_allow_html=True)

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
        st.markdown('<div class="error-message">❌ Column "Group name" not found in system dump.</div>', unsafe_allow_html=True)

with col2:
    if not system_df.empty and '[Scheme name]' in system_df.columns:
        scheme_options = sorted(system_df['[Scheme name]'].dropna().unique())
        scheme_type = st.selectbox(
            "📘 Select Scheme Type", 
            scheme_options,
            help="Choose the pension scheme type"
        )
    else:
        st.markdown('<div class="error-message">❌ Column "[Scheme name]" not found in system dump.</div>', unsafe_allow_html=True)

# --- Show filtered statistics ---
if employer_name and scheme_type and not system_df.empty:
    filtered_count = len(system_df[
        (system_df['Group name'] == employer_name) & 
        (system_df['[Scheme name]'] == scheme_type) &
        (system_df.get('Status', '') == 'Open')
    ])
    st.markdown(f"""
    <div class="info-message">
        📊 <strong>{filtered_count:,} active members</strong> found for {employer_name} under {scheme_type} scheme
    </div>
    """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# --- Template Download Section ---
st.markdown("""
<div class="section-card">
    <div class="section-title">
        📄 Download Blank Schedule Template
    </div>
    <p style="color: #6c757d; margin-bottom: 1.5rem;">Generate a pre-filled template with member information for the selected employer and scheme.</p>
""", unsafe_allow_html=True)

if st.button("📥 **GENERATE SCHEDULE TEMPLATE**", type="primary", use_container_width=True):
    if not employer_name or not scheme_type:
        st.markdown('<div class="error-message">⚠️ Please select both Employer Name and Scheme Type first.</div>', unsafe_allow_html=True)
    else:
        try:
            # Prepare filtered data for template
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
            
            # Filter data
            filtered_df = system_df_renamed[
                (system_df_renamed['Group name'] == employer_name) & 
                (system_df_renamed['[Scheme name]'] == scheme_type) &
                (system_df_renamed.get('Status', '') == 'Open')
            ]
            
            if filtered_df.empty:
                st.markdown('<div class="error-message">❌ No active members found for the selected employer and scheme type.</div>', unsafe_allow_html=True)
            else:
                # Generate template
                template_data = generate_schedule_template(employer_name, scheme_type, filtered_df)
                
                st.download_button(
                    label="📥 Download Template (Excel)",
                    data=template_data,
                    file_name=f"Schedule_Template_{employer_name}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help="Download blank schedule template with pre-filled member information"
                )
                
                st.markdown(f'<div class="success-message">✅ Template ready for download! Contains {len(filtered_df)} members.</div>', unsafe_allow_html=True)
                
        except Exception as e:
            st.markdown(f'<div class="error-message">❌ Error generating template: {e}</div>', unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# --- File Upload Section ---
st.markdown("""
<div class="section-card">
    <div class="section-title">
        📤 Upload Schedule
    </div>
""", unsafe_allow_html=True)
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
        st.markdown(f'<div class="error-message">❌ Error reading schedule file: {e}</div>', unsafe_allow_html=True)
        st.markdown('<div class="info-message">💡 Please ensure your Excel file has the correct format and structure.</div>', unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# --- Validation Interface ---
st.markdown("""
<div class="section-card">
    <div class="section-title">
        ⚡ Run Validation
    </div>
""", unsafe_allow_html=True)

# Validation button with enhanced styling
if st.button("**VALIDATE SCHEDULE**", type="primary", use_container_width=True):
    
    # Pre-validation checks
    if schedule_df.empty:
        st.markdown('<div class="error-message">⚠️ Please upload a valid schedule file.</div>', unsafe_allow_html=True)
    elif not employer_name or not scheme_type:
        st.markdown('<div class="error-message">⚠️ Please select both Employer Name and Scheme Type.</div>', unsafe_allow_html=True)
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
                st.markdown('<div class="error-message">❌ No active records found for selected scheme type.</div>', unsafe_allow_html=True)
            elif employer_filtered_df.empty:
                st.markdown('<div class="error-message">❌ No active records found for selected employer in this scheme.</div>', unsafe_allow_html=True)
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
                        st.markdown('<div class="success-message">🎉 No suspense found! Please inspect output before uploading.</div>', unsafe_allow_html=True)

        except Exception as e:
            progress_bar.progress(0)
            status_text.text("")
            st.markdown(f'<div class="error-message">❌ Error during validation: {str(e)}</div>', unsafe_allow_html=True)
            st.markdown('<div class="info-message">💡 Please check your file format and try again. Contact support if the issue persists.</div>', unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# --- Footer ---
st.markdown("""
<div class="footer">
    <p><strong>Peoples Pension Trust Contribution Schedule Validator</strong> | Powered by Advanced Fuzzy Matching</p>
    <p>For support or questions, contact PPT compliance (compliance@peoplespensiontrust.com)</p>
</div>
""", unsafe_allow_html=True)
