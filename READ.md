# ☕ CafeBoss - Professional Billing System

A modern, user-friendly billing system for cafes and restaurants built with Streamlit.

## Features

- 🪑 **Table Management** - 10 tables with visual status indicators (free/occupied)
- 📋 **Menu Management** - Add, edit, and organize menu items by category
- 🧾 **Real-time Billing** - Create and manage bills for each table
- 💾 **Auto-save** - Bills are automatically saved as CSV files
- 📊 **Owner Dashboard** - View daily sales, revenue, and download reports
- 🔐 **Secure Access** - Password-protected owner dashboard
- 📱 **Responsive Design** - Works on desktop and mobile devices

## Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/cafe-boss.git
cd cafe-boss

2. pip install -r requirements.txt

3.streamlit run app.py


Usage
Customer View
Select a table from the sidebar

Add items to the bill using the item selector

Process payment when done

Owner Dashboard
Click on "Owner Dashboard" tab

Enter password (set on first run)

View daily sales, revenue, and download reports

cafe-boss/
├── app.py              # Main application
├── requirements.txt    # Python dependencies
├── README.md          # Documentation
├── .gitignore         # Git ignore file
└── bills/             # Auto-generated bill files
    └── YYYY-MM-DD/    # Daily bill folders

Technologies Used
Streamlit - Web framework

Pandas - Data manipulation

Python 3.8+

MIT License - feel free to use and modify!


