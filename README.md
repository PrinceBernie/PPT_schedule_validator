# 🧾 Contribution Schedule Validator

A user-friendly Streamlit application to validate pension contribution schedules submitted by employers. The tool ensures the integrity and correctness of member data before crediting contributions.

---

## 📌 Features

- Validates salary range and 5% Tier-2 contribution
- Matches scheme numbers with system records
- Supports fallback ID and fuzzy name matching
- Flags issues with clear, domain-relevant labels
- Easy-to-use web interface for non-technical users

---

## 🧠 Validation Logic

| Validation Step | Description |
|-----------------|-------------|
| ✅ Salary Check | Salary must be between GHS 539.80 and 61,000 |
| ✅ Contribution Check | Contribution must be 5% of salary (± GHS 0.50) |
| 🔍 Scheme Number Match | Verifies submitted Scheme ID against system |
| 🔁 Fallback Matching | Uses Ghana Card, SSNIT, or Contact if needed |
| 🤖 Fuzzy Matching | Uses name similarity for final fallback |
| ⚠️ Name Mismatch Detection | Warns when IDs match but names differ |

---

## 📁 Files in the Repo

| File | Description |
|------|-------------|
| `app.py` | Streamlit app interface |
| `validator.py` | Core validation logic |
| `utils.py` | Helper functions (name cleaning, fuzzy matching) |
| `README.md` | Project documentation |
| `sample_schedule.xlsx` | Sample employer schedule file |
| `sample_system_dump.xlsx` | Sample system member data |

---

## 🚀 How to Run Locally

> Requirements: Python 3.9+, pip, or conda

### 🔧 Installation

```bash
git clone https://github.com/your-username/contribution-validator.git
cd contribution-validator

# Install dependencies
pip install -r requirements.txt

▶️ Run the App
streamlit run app.py
```

## 🌐 How to Use (Web App)
Upload employer schedule file;

📄 Accepted Schedule Template
The validator tool expects uploaded contribution schedules to follow this column structure:
| SSNIT NUMBER | GH. CARD NUMBER | CONTACT | SCHEME NUMBER | MEMBER NAME | BASIC SALARY | 5% CONTRIBUTION |
| ------------ | --------------- | ------- | ------------- | ----------- | ------------ | --------------- |
|              |                 |         |               |             |              |                 |
|              |                 |         |               |             |              |                 |

📌 Note: Column headers must match exactly as listed above. Ensure there are no trailing spaces and that the file is in Excel (.xlsx) format.


Enter employer name and scheme type (e.g., OPS, PPS)

Click Validate

Review flagged records and download results

```
📝 Flags & Status Legend
Flag	Meaning
✅ Valid Scheme ID & Name Match	All checks passed
❌ FLAG: Missing salary or contribution	One or both fields are empty
❌ FLAG: Invalid salary range	Salary out of bounds
❌ FLAG: Incorrect 5%	Tier2 doesn't equal 5% salary
❌ FLAG: Wrong scheme number for member	Name doesn't match assigned scheme
❌ FLAG: Scheme number not found	Not in system
✅ FLAG: Auto-filled scheme via fallback	Ghana Card/SSNIT/Contact matched
🚫 FLAG: Scheme filled via fuzzy name	Closest match by name
⚠️ FLAG: Name mismatch	IDs match but name is suspicious
```

🤝 Contributing
Contributions are welcome! Please fork the repo, create a feature branch, and submit a pull request.

📄 License

MIT License © [Prince Armo-Bernie]

