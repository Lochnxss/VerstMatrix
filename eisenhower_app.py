import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import math

# Authenticate with Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("google_sheets_key.json", scope)
client = gspread.authorize(creds)

# Open Google Sheet
SHEET_NAME = "EisenhowerMatrixTasks"
sheet = client.open(SHEET_NAME).sheet1

# Estimated time per task (in minutes)
TASK_TIME = {
    "Putaway 3002": 20,
    "Putaway 3043": 15,  
    "Unload Shuttles": 20,
    "Unload 3002 Inbound": 20,
    "Unload 3043 Inbound": 20,
    "Load 3043 Outbound": 20,
    "Load 3002 Outbound": 20,
    "Load LTL Outbound": 20,
    "LTL Picks Same Day": 15,
    "LTL Picks Next Day": 15,
    "FTL Picks Same Day": 25,
    "FTL Picks Next Day": 25,
    "Export Live Loads Same Day": 25,
    "Export Live Loads Next Day": 25,
    "Export Drop Same Day": 25,
    "Export Drop Next Day": 25
}

# Work hours per worker (7 hours per shift = 420 minutes)
WORK_MINUTES_PER_WORKER = 420

# Function to calculate people needed dynamically
def calculate_people_needed(task, quantity, urgency, importance):
    if task not in TASK_TIME:
        return 1  # Default to 1 if task not found

    time_per_task = TASK_TIME[task]
    total_time_needed = quantity * time_per_task

    # Priority Factor: higher urgency & importance = more workers
    priority_factor = (urgency * 1.5 + importance * 2) / 10

    # Dynamically allocate more workers to high-priority tasks
    people_needed = max(1, math.ceil((total_time_needed / WORK_MINUTES_PER_WORKER) * priority_factor))

    print(f"🔹 Dynamic People Allocation: {task} | Quantity: {quantity} | Urgency: {urgency} | Importance: {importance} | Priority Factor: {priority_factor:.2f} | People Needed: {people_needed}")

    return people_needed

# Function to update an existing task in Google Sheets
def update_task(task, urgency, importance, days_until_due, quantity):
    existing_tasks = sheet.get_all_records()
    
    for i, row in enumerate(existing_tasks):
        if row["Task"] == task:  
            priority = (int(urgency) * 1.5) + (int(importance) * 2) - (int(days_until_due) * 0.5)
            people_needed = calculate_people_needed(task, quantity, urgency, importance)

            print(f"✅ UPDATING TASK IN GOOGLE SHEETS: {task} | Urgency: {urgency} | Importance: {importance} | Quantity: {quantity} | Days Until Due: {days_until_due} | People Needed: {people_needed}")

            # Update values in Google Sheets
            sheet.update_cell(i+2, 2, urgency)     
            sheet.update_cell(i+2, 3, importance)  
            sheet.update_cell(i+2, 4, days_until_due)    
            sheet.update_cell(i+2, 5, priority)    
            sheet.update_cell(i+2, 6, quantity)    
            sheet.update_cell(i+2, 7, people_needed)  

            print("✅ Google Sheets Update Successful!")

            return True  
    return False  

# Function to load tasks from Google Sheets
def load_tasks():
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        # Convert columns to numeric where necessary
        df["Priority"] = pd.to_numeric(df["Priority"], errors="coerce").fillna(0)
        df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0)
        df["People Needed"] = pd.to_numeric(df["People Needed"], errors="coerce").fillna(1)
        df["Days Until Due"] = pd.to_numeric(df["Days Until Due"], errors="coerce").fillna(0)

        return df
    except Exception as e:
        print("❌ Error loading tasks:", e)
        return pd.DataFrame(columns=["Task", "Urgency", "Importance", "Days Until Due", "Priority", "Quantity", "People Needed"])

# Function to reset all task values to default (zero sum)
def reset_tasks():
    existing_tasks = sheet.get_all_records()

    for i, row in enumerate(existing_tasks):
        # Reset all task fields except task names
        sheet.update_cell(i+2, 2, 5)  # Default Urgency (5)
        sheet.update_cell(i+2, 3, 5)  # Default Importance (5)
        sheet.update_cell(i+2, 4, 0)  # Days Until Due (0 = Today)
        sheet.update_cell(i+2, 5, 0)  # Priority (0)
        sheet.update_cell(i+2, 6, 0)  # Quantity (0)
        sheet.update_cell(i+2, 7, 1)  # People Needed (1 - Ensures minimum)

    print("✅ All tasks reset to default values!")

# Streamlit UI
st.title("📋 Eisenhower Matrix Task Tracker")

# Load updated task data
df = load_tasks()

# Select Task from Dropdown
selected_task = st.selectbox("Select a Task", df["Task"].tolist())

# Load task data
task_data = df[df["Task"] == selected_task]

# Set default values
urgency = 5
importance = 5
quantity = 0  
days_until_due = 0  

if not task_data.empty:
    urgency = int(task_data.iloc[0]["Urgency"])
    importance = int(task_data.iloc[0]["Importance"])
    quantity = int(task_data.iloc[0]["Quantity"])
    days_until_due = int(task_data.iloc[0]["Days Until Due"])

# Due Date Slider
st.markdown("#### 📅 Task Due Timeline:")
days_until_due = st.slider("Days Until Due", 0, 5, days_until_due)

# Urgency & Importance Sliders with Legends
st.markdown("#### ⏳ Urgency Scale:")
st.markdown("""
- **1-3** → Low urgency (Can be done later)  
- **4-6** → Medium urgency (Should be done soon)  
- **7-9** → High urgency (Needs attention ASAP)  
- **10** → **Critical** (Must be done immediately)
""")
urgency = st.slider("Urgency (1-10)", 1, 10, urgency)

st.markdown("#### ⭐ Importance Scale:")
st.markdown("""
- **1-3** → Low importance (Minimal impact if delayed)  
- **4-6** → Medium importance (Moderate impact)  
- **7-9** → High importance (Significant impact)  
- **10** → **Critical** (Essential task, high consequences)
""")
importance = st.slider("Importance (1-10)", 1, 10, importance)

# Quantity Input
quantity = st.number_input("Quantity (How many of this task?)", min_value=0, value=quantity)

# Update Button
if st.button("Update Task"):
    update_task(selected_task, urgency, importance, days_until_due, quantity)
    st.rerun()

# Reset Button
if st.button("Reset All Tasks"):
    reset_tasks()
    st.success("✅ All tasks have been reset!")
    st.rerun()

# Display Updated Tasks Table
st.subheader("📊 Task Overview")
st.dataframe(df)
