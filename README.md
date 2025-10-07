# Confluence to PDF Exporter

A Python tool to download Confluence spaces, folders, or pages with all their sub-pages, exporting each as a PDF file.

## Features

- **Export entire Confluence spaces** - download all pages from a complete space
- Download pages from a Confluence folder or page URL
- Recursively process all subfolders and subdocuments
- **Preserves folder structure** - creates the same directory hierarchy in output
- **Space exports create dedicated directories** - space name becomes top-level folder
- Download a parent page and all its child pages (recursively)
- **Download attachments** - automatically downloads all attachments for each page
- Export each page as a well-formatted PDF
- **Attachment links in PDF** - lists all attachments with links to their location
- Preserves page hierarchy and formatting
- Handles authentication with Confluence API tokens

## Prerequisites

- Python 3.7 or higher
- A Confluence account with API access
- Confluence API token (for authentication)

## Installation

1. **Clone or download this project**

2. **Install Python dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Install system dependencies for WeasyPrint:**

   WeasyPrint requires some system libraries for PDF generation.

   - **Ubuntu/Debian:**
     ```bash
     sudo apt-get install python3-pip python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0
     ```

   - **macOS:**
     ```bash
     brew install python3 pango
     ```

   - **Windows:**
     Download and install GTK3 from https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer

4. **Set up authentication:**

   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your Confluence credentials:
   ```
   CONFLUENCE_USERNAME=your_email@example.com
   CONFLUENCE_API_TOKEN=your_api_token_here
   ```

## Getting Your Confluence API Token

1. Log in to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a name (e.g., "PDF Exporter")
4. Copy the token and paste it into your `.env` file

## Usage

1. **Run the script:**

   ```bash
   python main.py
   ```

2. **Enter the Confluence page, folder, or space URL when prompted:**

   The tool supports URLs in these formats:
   
   **Space URLs:**
   - `https://your-domain.atlassian.net/wiki/spaces/SPACEKEY`
   - Example: `https://your-domain.atlassian.net/wiki/spaces/ENG`
   
   **Folder URLs:**
   - `https://your-domain.atlassian.net/wiki/spaces/SPACE/folder/123456`
   - Example: `https://tigertext.atlassian.net/wiki/spaces/ENG/folder/3784114204`
   
   **Page URLs:**
   - `https://your-domain.atlassian.net/wiki/spaces/SPACE/pages/123456/Page+Title`
   - `https://your-domain.atlassian.net/wiki/pages/viewpage.action?pageId=123456`

3. **Wait for the export to complete:**

   The tool will:
   - Connect to Confluence
   - Detect if you provided a space, folder, or page URL
   - **For spaces:** Find all pages in the entire space (recursively)
   - **For folders:** Find all pages in the folder and all subfolders (recursively)
   - **For pages:** Download the parent page and find all child pages (recursively)
   - Download all attachments for each page
   - Export each page as a PDF

4. **Find your PDFs:**

   All exported PDFs will be saved in the `output/` directory.
   
   **Folder Structure:**
   - For space URLs, a top-level directory with the space name is created
   - For folder URLs, the output directory will mirror the Confluence folder structure
   - Each page's attachments are saved in a folder named `{PageName}_{PageID}_attachments`
   - PDFs include a list of attachments with their locations
   
   Example output structure for a space export:
   ```
   output/
   └── Engineering/              # Space name directory
       ├── API_Documentation_123456.pdf
       ├── API_Documentation_123456_attachments/
       │   ├── api_schema.json
       │   └── example_request.txt
       └── Backend/
           ├── Database_Design_789012.pdf
           └── Database_Design_789012_attachments/
               └── erd_diagram.png
   ```

## File Structure

```
confluence/
├── main.py                 # Main entry point
├── confluence_client.py    # Confluence API interaction
├── pdf_exporter.py         # PDF generation logic
├── requirements.txt        # Python dependencies
├── .env.example           # Example environment file
├── .env                   # Your credentials (not in git)
├── .gitignore            # Git ignore rules
└── output/               # Generated PDFs and attachments (created automatically)
    ├── folder_structure/  # Mirrors Confluence folders
    └── page_attachments/  # Downloaded attachments
```

## Troubleshooting

### Authentication Errors

- Verify your API token is correct in `.env`
- Make sure your username is your email address
- Check that you have permission to access the Confluence pages

### PDF Generation Issues

- If WeasyPrint fails, the tool will save an HTML file for debugging
- Check that system dependencies are installed correctly
- Some complex Confluence macros may not render perfectly

### Attachment Download Issues

- Large attachments may take time to download
- Check network connectivity if downloads fail
- Verify you have permission to access attachments
- Check available disk space for large attachment collections

### URL Format Errors

- Make sure the URL includes the space key, page ID, or folder ID
- For spaces, use: `https://your-domain.atlassian.net/wiki/spaces/SPACEKEY`
- For folders, use: `https://your-domain.atlassian.net/wiki/spaces/SPACE/folder/FOLDER_ID`
- For pages, use: `https://your-domain.atlassian.net/wiki/spaces/SPACE/pages/PAGE_ID/Page+Title`
- You can find the ID in the URL when viewing a page or folder in Confluence

### Empty Folder Results

- If a folder appears empty, verify you have permissions to access its contents
- Some folders may not contain pages directly, only subfolders

## Limitations

- Some Confluence macros may not render in PDF
- Very large pages might take time to process
- Images need to be publicly accessible or authentication-compatible
- Embedded content (videos, interactive elements) may not display in PDF
- Attachments are downloaded separately and linked in the PDF (not embedded)

## License

This project is open source and available for personal and commercial use.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.
