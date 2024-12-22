# Test-Builder Guide

Follow these steps to set up and use the Test-Builder:

## Setup Instructions

1. **Download the Questionbank**  
   - Obtain the **5th Edition (Topic)** or **6th Edition** IB Docs Questionbank.  
   - Save the downloaded file inside the **test-builder** folder.

2. **Extract the Files**  
   - Extract the downloaded file.  
   - **Do not change any folder names** during or after extraction.

3. **Open the Questionbank**  
   - Navigate into the folder you extracted.  
   - Locate and open `index.html` in your web browser.

## Usage Instructions

4. **Select a Subject and Section**  
   - Choose the subject you want to work with.  
   - Click on the link for the desired syllabus section.

5. **Copy the URL**  
   - Copy the URL from your browser's address bar.

   6. **Run the Script**  
      - Open a terminal or command prompt and run the following command:

        ```bash
        python script.py <URL> [True] [destination.html]
        ```

        - Replace `<URL>` with the copied URL.  
        - Use `[True]` to enable additional features (optional):  
          - For the **5th Edition (Topic)**, this ensures questions with similar bases (e.g., `22N.1A.SL.TZ0.8a` and `22N.1A.SL.TZ0.8`) are grouped together, showing only unique base questions in the output.  
          - For the **6th Edition**, this extracts all reference codes for exam questions, even those buried in subsections, and includes their respective links in the output. 
        - Replace `[destination.html]` with the name of the output file you want to generate (optional).

7. **Serve the File Locally**  
   - Start a local HTTP server by running:

     ```bash
     python -m http.server
     ```

8. **View the File in Your Browser**  
   - Open your web browser and navigate to:

     ```
     http://localhost:8000
     ```

   - Click on the output file you generated (`destination.html`) to view it.

---

## Notes:
- Ensure Python is installed on your system.
- Replace any placeholder values (`<URL>`, `[True]`, `[destination.html]`) as needed.
- If you encounter issues, verify the folder structure and file paths.
