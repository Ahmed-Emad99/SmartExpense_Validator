# PDF Upload to Azure Blob Storage - Streamlit UI

A simple Streamlit application that allows users to upload PDF files to Azure Blob Storage with organized folder structures.

## Features

✨ **User-Friendly Interface**
- Upload PDF files with an intuitive file uploader
- Enter custom folder names
- Real-time upload status and feedback

🔒 **Azure Blob Storage Integration**
- Secure connection via connection string
- Automatic container creation
- Organized file structure with folder prefixes
- File overwrite option

## Prerequisites

- Python 3.8 or higher
- Azure Storage Account
- Azure Storage Connection String

## Installation

1. **Clone or navigate to the project directory**
```bash
cd "c:\Users\Hasan Nader\Desktop\final project\blob storage"
```

2. **Create a virtual environment (optional but recommended)**
```bash
python -m venv venv
venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

## Setup

### Get Azure Storage Connection String

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to **Storage Accounts**
3. Select your storage account
4. Go to **Access Keys** in the left menu
5. Copy the **Connection String** (key1 or key2)

## Running the Application

```bash
streamlit run app.py
```

The app will open in your default browser at `http://localhost:8501`

## Usage

1. **Paste Connection String**: In the sidebar, enter your Azure Storage connection string
2. **Enter Folder Name**: Provide a folder name (e.g., "my-documents", "project-files")
3. **Upload PDF**: Select a PDF file from your computer
4. **Click Upload PDF**: The file will be uploaded to a folder with the specified name

## Project Structure

```
.
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── .env.example          # Example environment variables
└── README.md             # This file
```

## How It Works

- **Folder Creation**: Folders are created as blob path prefixes (e.g., "folder-name/")
- **File Organization**: PDFs are stored in the `uploads` container with paths like `folder-name/document.pdf`
- **Container Management**: The app automatically creates the `uploads` container if it doesn't exist

## Environment Variables (Optional)

You can set the connection string as an environment variable to avoid pasting it every time:

1. Create a `.env` file in the project directory
2. Add your connection string:
```
AZURE_STORAGE_CONNECTION_STRING=your_connection_string_here
```

3. Modify `app.py` to load from environment variables (optional enhancement)

## Error Handling

- **Missing Connection String**: You'll see a prompt to enter it
- **Invalid Connection String**: An error message will appear
- **Missing Folder Name**: The app won't allow upload
- **Missing PDF File**: You'll be prompted to select a file
- **Upload Failure**: Detailed error messages will help troubleshoot

## Security Notes

⚠️ **Important**:
- Never commit your connection string to version control
- Use `.env` files locally and add to `.gitignore`
- Connection strings entered in the UI are not saved
- For production, consider using Azure Managed Identity or other secure authentication methods

## Troubleshooting

### "Invalid connection string"
- Verify the connection string from Azure Portal
- Ensure it hasn't expired
- Check for extra spaces or characters

### "Container already exists"
- This is normal if you've run the app before
- The app will skip creation and continue

### File not uploading
- Ensure the PDF file is valid
- Check Azure Storage account permissions
- Verify network connectivity to Azure

## Dependencies

- **streamlit**: Web app framework
- **azure-storage-blob**: Azure Blob Storage SDK

## License

This project is open source and available for modification and distribution.

## Support

For issues or questions about Azure Blob Storage, visit the [Azure Documentation](https://docs.microsoft.com/en-us/azure/storage/blobs/).
