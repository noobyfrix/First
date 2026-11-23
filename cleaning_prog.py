import io
import pandas as pd
import streamlit as st

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Data Cleanser",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <h1 style='text-align: center; margin-bottom: 30px;'>
        Data Cleanser
    </h1>
    """,
    unsafe_allow_html=True
)

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "original_df" not in st.session_state:
    st.session_state.original_df = None

if "result_df" not in st.session_state:
    st.session_state.result_df = None

if "history" not in st.session_state:
    st.session_state.history = []

if "file_signature" not in st.session_state:
    st.session_state.file_signature = None


# --------------------------------------------------
# DATA PROCESSING FUNCTIONS
# --------------------------------------------------

def fill_data(
    df,
    numeric_method="Median",
    categorical_method="Mode",
    custom_value="N/A",
    handle_outliers=True
):
    df = df.copy()

    for col in df.columns:

        # NUMERICAL COLUMNS
        if pd.api.types.is_numeric_dtype(df[col]):

            if numeric_method == "Mean":
                replacement = df[col].mean()
            else:
                replacement = df[col].median()

            # Fill missing values
            df[col] = df[col].fillna(replacement)

            # Detect and replace outliers using IQR
            if handle_outliers and df[col].notna().any():

                q1 = df[col].quantile(0.25)
                q3 = df[col].quantile(0.75)

                iqr = q3 - q1

                lower_bound = q1 - (1.5 * iqr)
                upper_bound = q3 + (1.5 * iqr)

                median = df[col].median()

                outliers = (
                    (df[col] < lower_bound) |
                    (df[col] > upper_bound)
                )

                df.loc[outliers, col] = median

        # NON-NUMERICAL COLUMNS
        else:

            if categorical_method == "Mode":
                modes = df[col].mode(dropna=True)

                if not modes.empty:
                    replacement = modes.iloc[0]
                else:
                    replacement = custom_value

            else:
                replacement = custom_value

            df[col] = df[col].fillna(replacement)

    return df


def organize_data(
    df,
    selected_columns,
    sort_column=None,
    ascending=True
):
    df = df.copy()

    # Reorder columns
    if selected_columns:
        remaining = [
            col for col in df.columns
            if col not in selected_columns
        ]

        df = df[selected_columns + remaining]

    # Sort rows
    if sort_column and sort_column != "None":
        df = df.sort_values(
            by=sort_column,
            ascending=ascending
        )

    return df.reset_index(drop=True)


def manual_clean(
    df,
    remove_duplicates=False,
    remove_empty_rows=False,
    remove_empty_columns=False,
    trim_spaces=False,
    columns_to_drop=None,
    missing_columns=None,
    replace_column=None,
    old_value=None,
    new_value=None
):
    df = df.copy()

    # Remove duplicate rows
    if remove_duplicates:
        df = df.drop_duplicates()

    # Remove completely empty rows
    if remove_empty_rows:
        df = df.dropna(how="all")

    # Remove completely empty columns
    if remove_empty_columns:
        df = df.dropna(axis=1, how="all")

    # Remove selected columns
    if columns_to_drop:
        df = df.drop(columns=columns_to_drop, errors="ignore")

    # Remove rows with missing values in selected columns
    if missing_columns:
        existing_columns = [
            col for col in missing_columns
            if col in df.columns
        ]

        if existing_columns:
            df = df.dropna(subset=existing_columns)

    # Trim unnecessary spaces in text columns
    if trim_spaces:
        for col in df.select_dtypes(include=["object", "string"]).columns:
            df[col] = df[col].apply(
                lambda value: value.strip()
                if isinstance(value, str)
                else value
            )

    # Replace a specific value in a selected column
    if (
        replace_column
        and old_value is not None
        and new_value is not None
    ):
        df[replace_column] = df[replace_column].replace(
            old_value,
            new_value
        )

    return df.reset_index(drop=True)


# --------------------------------------------------
# FILE UPLOAD
# --------------------------------------------------

with st.sidebar:

    st.header("Data Upload")

    uploaded_file = st.file_uploader(
        "Upload your dataset",
        type=["csv", "xlsx", "xls"]
    )

    if uploaded_file is not None:

        signature = (
            uploaded_file.name,
            uploaded_file.size
        )

        if signature != st.session_state.file_signature:

            st.session_state.file_signature = signature
            st.session_state.result_df = None
            st.session_state.history = []

            try:

                if uploaded_file.name.lower().endswith(".csv"):

                    df = pd.read_csv(uploaded_file)

                else:

                    excel_file = pd.ExcelFile(uploaded_file)

                    sheet = st.selectbox(
                        "Choose Excel sheet",
                        excel_file.sheet_names
                    )

                    df = pd.read_excel(
                        excel_file,
                        sheet_name=sheet
                    )

                st.session_state.original_df = df

            except Exception as error:

                st.error(f"Unable to read file: {error}")
                st.session_state.original_df = None

# --------------------------------------------------
# MAIN APPLICATION
# --------------------------------------------------

if uploaded_file is None:

    st.info("Upload a CSV or Excel file to get started.")

elif st.session_state.original_df is not None:

    original_df = st.session_state.original_df

    st.subheader("Original Dataset")

    col1, col2, col3 = st.columns(3)

    col1.metric("Rows", original_df.shape[0])
    col2.metric("Columns", original_df.shape[1])
    col3.metric(
        "Missing Values",
        int(original_df.isna().sum().sum())
    )

    st.dataframe(
        original_df,
        width="stretch",
        height=300
    )

    st.divider()

    # --------------------------------------------------
    # CLEANING METHOD SELECTION
    # --------------------------------------------------

    st.sidebar.divider()

    st.sidebar.header("Data Operations")

    method = st.sidebar.selectbox(
        "Choose your method",
        [
            "Organize",
            "Fill",
            "Manual Cleaning"
        ]
    )

    # --------------------------------------------------
    # ORGANIZE
    # --------------------------------------------------

    if method == "Organize":

        st.subheader("Organize Dataset")

        selected_columns = st.multiselect(
            "Choose column order",
            original_df.columns.tolist(),
            default=original_df.columns.tolist(),
            help="The selected columns will appear first in this order."
        )

        sort_column = st.selectbox(
            "Sort rows by column",
            ["None"] + original_df.columns.tolist()
        )

        ascending = st.radio(
            "Sort direction",
            ["Ascending", "Descending"],
            horizontal=True
        )

        if st.button("Organize Dataset", type="primary"):

            try:

                result = organize_data(
                    original_df,
                    selected_columns,
                    sort_column,
                    ascending == "Ascending"
                )

                st.session_state.result_df = result
                st.session_state.history.append(
                    ("Organize", result.copy())
                )

                st.success("Dataset organized successfully!")

            except Exception as error:

                st.error(f"Organization failed: {error}")

    # --------------------------------------------------
    # FILL
    # --------------------------------------------------

    elif method == "Fill":

        st.subheader("Fill Missing Values and Handle Outliers")

        numeric_method = st.selectbox(
            "Numerical missing values",
            ["Median", "Mean"]
        )

        categorical_method = st.selectbox(
            "Categorical missing values",
            ["Mode", "Custom Value"]
        )

        custom_value = "N/A"

        if categorical_method == "Custom Value":

            custom_value = st.text_input(
                "Replacement value",
                value="N/A"
            )

        handle_outliers = st.checkbox(
            "Detect and replace numerical outliers using IQR",
            value=True
        )

        st.caption(
            "Numerical missing values are filled using the selected "
            "statistic. Categorical missing values use the mode or "
            "your custom replacement."
        )

        if st.button("Fill Dataset", type="primary"):

            try:

                result = fill_data(
                    original_df,
                    numeric_method,
                    categorical_method,
                    custom_value,
                    handle_outliers
                )

                st.session_state.result_df = result
                st.session_state.history.append(
                    ("Fill", result.copy())
                )

                st.success("Dataset filled successfully!")

            except Exception as error:

                st.error(f"Filling failed: {error}")

    # --------------------------------------------------
    # MANUAL CLEANING
    # --------------------------------------------------

    elif method == "Manual Cleaning":

        st.subheader("Manual Cleaning")

        st.write("Choose the operations you want to perform.")

        remove_duplicates = st.checkbox(
            "Remove duplicate rows"
        )

        remove_empty_rows = st.checkbox(
            "Remove completely empty rows"
        )

        remove_empty_columns = st.checkbox(
            "Remove completely empty columns"
        )

        trim_spaces = st.checkbox(
            "Trim unnecessary spaces from text columns"
        )

        columns_to_drop = st.multiselect(
            "Remove selected columns",
            original_df.columns.tolist()
        )

        missing_columns = st.multiselect(
            "Remove rows with missing values in these columns",
            original_df.columns.tolist()
        )

        st.divider()

        st.write("Replace a specific value")

        replace_column = st.selectbox(
            "Select column",
            ["None"] + original_df.columns.tolist()
        )

        old_value = None
        new_value = None

        if replace_column != "None":

            old_value = st.text_input(
                "Value to find"
            )

            new_value = st.text_input(
                "Replace with"
            )

        if st.button("Apply Manual Cleaning", type="primary"):

            try:

                result = manual_clean(
                    original_df,
                    remove_duplicates,
                    remove_empty_rows,
                    remove_empty_columns,
                    trim_spaces,
                    columns_to_drop,
                    missing_columns,
                    replace_column if replace_column != "None" else None,
                    old_value,
                    new_value
                )

                st.session_state.result_df = result
                st.session_state.history.append(
                    ("Manual Cleaning", result.copy())
                )

                st.success("Manual cleaning completed!")

            except Exception as error:

                st.error(f"Manual cleaning failed: {error}")

    # --------------------------------------------------
    # RESULT DISPLAY
    # --------------------------------------------------

    if st.session_state.result_df is not None:

        result_df = st.session_state.result_df

        st.divider()

        st.subheader("Processed Dataset")

        col1, col2, col3 = st.columns(3)

        col1.metric("Rows", result_df.shape[0])
        col2.metric("Columns", result_df.shape[1])
        col3.metric(
            "Missing Values",
            int(result_df.isna().sum().sum())
        )

        st.dataframe(
            result_df,
            width="stretch",
            height=350
        )

        # --------------------------------------------------
        # DOWNLOAD OPTIONS
        # --------------------------------------------------

        st.subheader("Download Your Dataset")

        csv_data = result_df.to_csv(
            index=False
        ).encode("utf-8")

        col1, col2 = st.columns(2)

        with col1:

            st.download_button(
                "Download CSV",
                data=csv_data,
                file_name="cleaned_dataset.csv",
                mime="text/csv",
                type="primary"
            )

        with col2:

            excel_buffer = io.BytesIO()

            with pd.ExcelWriter(
                excel_buffer,
                engine="openpyxl"
            ) as writer:

                result_df.to_excel(
                    writer,
                    index=False,
                    sheet_name="Cleaned Data"
                )

            st.download_button(
                "Download Excel",
                data=excel_buffer.getvalue(),
                file_name="cleaned_dataset.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # --------------------------------------------------
    # PROCESSING HISTORY
    # --------------------------------------------------

    if st.session_state.history:

        st.divider()

        st.subheader("Processing History")

        for index, (operation, history_df) in enumerate(
            reversed(st.session_state.history),
            start=1
        ):

            with st.expander(
                f"{operation} — Version {len(st.session_state.history) - index + 1}"
            ):

                st.dataframe(
                    history_df,
                    width="stretch"
                )

        if st.button("Clear Processing History"):

            st.session_state.history = []
            st.session_state.result_df = None

            st.rerun()