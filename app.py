import streamlit as st
import pandas as pd
from openai import OpenAI
import os
import re
from dotenv import load_dotenv
from git import Repo



load_dotenv()

client = OpenAI(
    # Replace with actual API key
    api_key=os.getenv("API_KEY"),
    base_url="https://openrouter.ai/api/v1")


def fetch_data_from_excel(file_name, plant_name):
    plant_data = pd.read_excel(file_name)
    matched_rows = plant_data[plant_data["Flower Name"].str.strip(
    ).str.lower() == plant_name]

    details = ""  # Initialize details outside the loop

    # Loop through each row (in case of multiple matches)
    for _, row in matched_rows.iterrows():
        details += "\n".join(
            [f"**{col}**: {row[col]} \n" for col in plant_data.columns])
        details += "\n\n"  # Add a separator between rows

    return details


def check_data_exist(file_name, plant_name):
    plant_data = pd.read_excel(file_name)
    matched_rows = plant_data[plant_data["Flower Name"].str.strip(
    ).str.lower() == plant_name]

    if not matched_rows.empty:
        return True
    else:
        return False


def Column_preprocessing(file_name):

    df = pd.read_excel(file_name)
    # Extract column names
    columns = df.columns

    # Identify columns that end with '**'
    star_columns = [col for col in columns if col.endswith(
        '**') and col.startswith('**')]

    # Create column pairs by matching normal columns with their corresponding '**' columns
    column_pairs = []
    for star_col in star_columns:
        normal_col = star_col[:-2]  # Remove '**' from the column name
        if normal_col in columns:  # Check if the normal column exists
            column_pairs.append((normal_col, star_col))

    # Iterate through each row and select the value from the appropriate column
    for index, row in df.iterrows():
        for normal_col, star_col in column_pairs:
            if pd.notna(row[normal_col]):
                df.at[index, normal_col] = row[normal_col]
            elif pd.notna(row[star_col]):
                df.at[index, normal_col] = row[star_col]

    # Drop the ** columns as they are no longer needed
    df = df.drop(columns=[star_col for _, star_col in column_pairs])

    # Save the modified DataFrame back to Excel (optional)
    df.to_excel(file_name, index=False)
    repo_path = "https://github.com/amanrajgp/MeraPaudha.git"  # Change to your repo path
    file_path = os.path.join(repo_path, "output.xlsx")
    
    repo = Repo(repo_path)
    repo.git.add(file_path)
    repo.index.commit("Updated output.xlsx with new plant data")
    repo.remote("origin").push()

# Now you can use the column_pairs list in the previous code to process the data


# Streamlit UI
st.sidebar.title("🌿 Mera Paudha")


def generate_plant_data(flower_name):
    prompt = f"""
    You are a botanist specializing in India-specific flower cultivation. Provide full, detailed, structured information about [{flower_name}].
    Each section must contain a **detailed paragraph**.
    Output must be formatted as **key: detailed paragraph explanation**.

    **Sections:**
    Common Name, Botanical Name, Family, Plant Type, Mature Size, Sun Exposure, Soil Type, Soil pH, Bloom Time, Flower Color,
    Hardiness Zones, Native Area, Planting, Light, Soil Preparation, Watering, Temperature and Humidity, Fertilizer,
    Types/Varieties, Pruning, Propagation, Growing from Seed, Potting and Repotting, Pests and Diseases, Encouraging Blooms,
    Common Problems, Growth Rate, Watering Frequency, Pollinator-Friendly, Toxicity, Companion Plants, Cultural Significance,
    Eco-Friendliness, Indoor vs. Outdoor Suitability.

    **Example Output Format:**
    "Common Name": "Rose - The rose is one of the most beloved flowers, known for its fragrance..."
    "Botanical Name": "Rosa rubiginosa - This species belongs to the Rosaceae family..."

    - Ensure all responses are India-specific.
    - Do not skip any section.
    - Ensure detailed paragraph descriptions for each section.
    """

    response = client.chat.completions.create(
        model="deepseek/deepseek-r1:free",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content


def store_data_to_excel(plant_name, text, excel_file):
    # Convert the text into a dictionary
    data = {"Flower Name": plant_name}
    for line in text.strip().split("\n"):
        # Skip the line if it doesn't contain the delimiter ": "
        if ": " not in line:
            print(f"Skipping line (invalid format): {line}")
            continue

        # Split only on the first occurrence of ": "
        key, value = line.split(": ", 1)
        # Remove the surrounding quotes from the key
        key = key.strip('"') or key.strip('**')

        # Remove the surrounding quotes from the value
        value = value.strip('"')
        data[key] = value

    # If no valid data was found, return early
    if not data:
        print("No valid data found in the input text.")
        return

    # Convert the dictionary to a DataFrame
    df_new = pd.DataFrame([data])

    # Check if the Excel file already exists
    if os.path.exists(excel_file):
        # Load the existing Excel file
        df_existing = pd.read_excel(excel_file)
        # Append the new data to the existing DataFrame
        df_new.columns = df_new.columns.str.strip(
            '"').str.strip('*').str.strip()
        df_existing.columns = df_existing.columns.str.strip(
            '"').str.strip('*').str.strip()

        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        df_combined = df_combined.loc[:, ~df_combined.columns.duplicated()]

    else:
        # If the file doesn't exist, use the new DataFrame
        df_combined = df_new

    # Save the combined DataFrame to the Excel file
    df_combined.to_excel(excel_file, index=False)

    
    Column_preprocessing(excel_file)


# User input

file_name = "output.xlsx"
# Search when button is clicked


# Define your functions here like check_data_exist, fetch_data_from_excel, generate_plant_data, and store_data_to_excel

# Sidebar navigation
page = st.sidebar.radio(
    "Select a Page", ["Home", "Plant Details", "Plant Database"])

if page == "Home":
    st.title("Welcome to the Plant Information App")
    st.markdown("Explore the plant details and the plant database!")

elif page == "Plant Details":
    st.title("Plant Details")
    plant_name = st.text_input("Enter Plant Name").strip().lower()

    if st.button("Get Details"):
        if check_data_exist(file_name, plant_name):
            st.markdown("### 🌿 Plant Details:")
            st.write(fetch_data_from_excel("output.xlsx", plant_name))
        else:
            st.write(
                f"Plant doesn't exist in the database... Fetching details for **{plant_name.capitalize()}**...")
            with st.spinner("Generating plant details..."):
                plant_detail = generate_plant_data(plant_name)
                store_data_to_excel(plant_name, plant_detail, file_name)
                st.write(fetch_data_from_excel(file_name, plant_name))

elif page == "Plant Database":
    st.title("Plant Database")
    if st.button("Show Plant Database Excel Sheet"):
        plant_database = pd.read_excel(file_name)
        st.write(plant_database)


def generate_detail_of_plant(plant_name, file_name):
    st.title("plant_database")
