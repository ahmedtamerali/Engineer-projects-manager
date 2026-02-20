🏗️ Eng. Abdelrahman Projects Manager

A desktop application for managing projects, workers, importers, and payments.
Built with Python, ttkbootstrap, and SQLite.

🚀 Features

Manage multiple projects with a clean dashboard

Track workers, importers, and customer payments

Arabic interface (Right-to-Left layout)

Local SQLite database (data.db)

Export data to Excel

Create automatic backups of the database

⚙️ Installation

Clone the repository:

git clone https://github.com/ahmedtamerali/Engineer-projects-manager.git
cd Engineer-projects-manager

Install dependencies:

python -m pip install -r requirements.txt
▶️ Usage

Run the application:

python main.py
🧩 Project Structure
Engineer-projects-manager/
│
├── main.py                  # App entry point
├── requirements.txt         # Dependencies
├── data.db                  # Local SQLite database
│
├── ui/                      # User interface components
│   ├── main_window.py
│   └── project_window.py
│
├── db/                      # Database logic
│   └── db.py
│
└── utils/                   # Helper utilities (validation, etc.)
🧠 Notes

Interface language: Arabic (RTL)

Database file: data.db (auto-created in working directory)

Works completely offline


👨‍💻 Developer

Ahmed Tamer
Created to simplify and organize project payment management.

📦 GitHub Repository → Engineer-projects-manager