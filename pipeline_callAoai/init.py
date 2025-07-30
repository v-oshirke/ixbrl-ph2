import azure.functions as func
import logging
from utils.prompts import load_prompts
from utils.blob_functions import get_blob_content, write_to_blob
from utils.azure_openai import run_prompt
import io
import os
import pandas as pd
from PyPDF2 import PdfReader
from bs4 import BeautifulSoup
from azure.storage.blob import BlobServiceClient
import json

            # # --- Get HTML Blob ---
            # container_client = blob_service_client.get_container_client(container_name)
            # html_blobs = [blob.name for blob in container_client.list_blobs() if blob.name.endswith(".html")]

            # if not html_blobs:
            #     raise FileNotFoundError("No .html files found in container.")
            
            # blob_bytes = get_blob_content(container_name, blob_name)  # returns bytes
            # # ext = os.path.splitext(blob_name)[1].lower()

            # # blob_name = html_blobs[0]
            # # blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

            # # blob_bytes = blob_client.download_blob().readall()
            # html_content = blob_bytes.decode("utf-8")

            # # --- Parse HTML and Extract <div class="page"> ---
            # soup = BeautifulSoup(html_content, "html.parser")
            # divs = soup.find_all("div", class_="page")
            # divs_html = ''.join(str(div) for div in divs)

            # # --- Reparse only page divs ---
            # soup = BeautifulSoup(divs_html, "html.parser")
            # pages = soup.find_all("div", class_="page")

            # pages_data = []

            # for idx, page in enumerate(pages):
            #     page_id = page.get("id")
            #     try:
            #         page_no = int(page_id) if page_id and page_id.isdigit() else idx + 1
            #     except:
            #         page_no = idx + 1
                
            #     text = page.get_text(separator=" ", strip=True)

            #     tags_list = []
            #     for tag in page.find_all():
            #         if tag.name and tag.name.startswith("ix:"):
            #             tag_key = tag.get("name")
            #             tag_value = tag.get_text(strip=True)
            #             if tag_key:
            #                 tag_entry = {
            #                     "name": tag_key,
            #                     "value": tag_value
            #                 }
            #                 if tag.has_attr("unitref"):
            #                     tag_entry["unitRef"] = tag["unitref"]
            #                 if tag.has_attr("decimals"):
            #                     tag_entry["decimals"] = tag["decimals"]

            #                 dimensions = {}
            #                 for attr_key, attr_val in tag.attrs.items():
            #                     if "dimension" in attr_key.lower():
            #                         dimensions[attr_key] = attr_val
            #                 if dimensions:
            #                     tag_entry["dimension"] = dimensions

            #                 tags_list.append(tag_entry)

            #     if tags_list:
            #         pages_data.append({
            #             "page_no": page_no,
            #             "raw_text": text,
            #             "tags": tags_list
            #         })

            # # --- Print JSON ---
            # result_json = json.dumps(pages_data, indent=2)


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    try:
        req_body = req.get_json()
        # Get the list of blobs sent from the frontend (if any)
        selected_blobs = req_body.get("blobs", None)
        
        if not selected_blobs:
            return func.HttpResponse(
                json.dumps({"error": "No blobs provided."}),
                status_code=400,
                mimetype="application/json"
            )
        
        processed_files = []
        errors = []
        
        # Loop through each blob provided
        for blob in selected_blobs:
            blob_name = blob.get("name")
            container_name = blob.get("container", "silver")  # Default to 'silver' if not provided
            
            if not blob_name:
                errors.append("Blob is missing the 'name' property.")
                continue
            
            # Disallow processing if the blob comes from a disallowed container
            if container_name == "bronze":
                logging.warning(f"Skipping blob from the bronze container: {blob_name}")
                errors.append(f"Processing blobs from the 'bronze' container is not allowed: {blob_name}")
                continue
            
            logging.info(f"Processing blob: {blob_name} from container: {container_name}")
            
            # Step 1: Get the content of the specified blob (expects a .txt file)
            # try:
            #     content = get_blob_content(container_name, blob_name).decode('utf-8')
            # except Exception as e:
            #     error_msg = f"Error getting content for blob {blob_name}: {str(e)}"
            #     logging.error(error_msg)
            #     errors.append(error_msg)
            #     continue
           

            try:
                blob_bytes = get_blob_content(container_name, blob_name)  # returns bytes
                ext = os.path.splitext(blob_name)[1].lower()

                if ext == '.csv':
                    content = pd.read_csv(io.BytesIO(blob_bytes))  # DataFrame

                elif ext == '.xlsx':
                    xls = pd.ExcelFile(io.BytesIO(blob_bytes))
                    # sheet_json_data = {}

                    # # Only process these sheets
                    # sheets_to_read = ["Filing Information", "Free Selection Comments", "Filing Details"]

                    # for sheet_name in sheets_to_read:
                    #     if sheet_name in excel_file.sheet_names:
                    #         df = excel_file.parse(sheet_name)
                    #         df_limited = df.head(10)  # limit to first 10 rows
                    #         sheet_json_data[sheet_name] = json.loads(df_limited.to_json(orient='records'))
                    #     else:
                    #         logging.warning(f"Sheet '{sheet_name}' not found in blob {blob_name}")

                    # 1. Filing Information
                    df_info = pd.read_excel(xls, sheet_name='Filing Information').dropna(how='all')
                    json_info = df_info.to_dict(orient='records')

                    # 2. Free Selection Comments
                    df_comments = pd.read_excel(xls, sheet_name='Free Selection Comments')
                    df_comments = df_comments[['Document Value', 'Comment Text']].dropna(how='all')
                    json_comments = df_comments.to_dict(orient='records')

                    # 3. Filing Details
                    df_filing = pd.read_excel(xls, sheet_name='Filing Details')
                    df_filing = df_filing[['Concept Label', 'Document Value', 'Tag Value']].dropna(how='all')
                    json_filing = df_filing.to_dict(orient='records')

                    # Combine into sectioned format
                    final_output = {
                        "Filing Information": json_info,
                        "Free Selection Comments": json_comments,
                        "Filing Details": json_filing }

                    content = final_output


                # elif ext == '.xlsx':
                #     content = pd.read_excel(io.BytesIO(blob_bytes))  # DataFrame

                elif ext == '.pdf':
                    reader = PdfReader(io.BytesIO(blob_bytes))
                    content = ''
                    for page in reader.pages:
                        content += page.extract_text()

                elif ext in ['.html', '.htm']:
                    soup = BeautifulSoup(blob_bytes.decode('utf-8'), 'html.parser')
                    content = soup.get_text()

                else:
                    content = blob_bytes.decode('utf-8')  # fallback for plain text or .txt

            except Exception as e:
                error_msg = f"Error getting content for blob {blob_name}: {str(e)}"
                logging.error(error_msg)
                errors.append(error_msg)
                continue

            # Step 2: Load Prompts
            try:
                logging.info("Loading Prompts")
                # prompts = load_prompts()
                # system_prompt = prompts["system_prompt"]
                prompts = load_prompts()
                system_prompt = prompts["system_prompt"]
                taxonomy_prompt = prompts["taxonomy_prompt"]
                comment_prompt = prompts["comment_prompt"]
                filing_prompt = prompts["filing_prompt"]

                user_prompt = prompts["user_prompt"]
            except Exception as e:
                error_msg = f"Error loading prompts for blob {blob_name}: {str(e)}"
                logging.error(error_msg)
                errors.append(error_msg)
                continue
            
# -----------------------------------------------------------------------
            # Combinig the html + excel tags before sending to LLM
            
            # html_data = json.loads(result_json)
            # content["HTML Pages"] = html_data

            # This is the part that would be going to the LLM
            # full_user_prompt = user_prompt + content
# -------------------------------------------------------------------------
            # Build structured prompt with JSON sheets if it's Excel
            if isinstance(content, dict):
                full_user_prompt = user_prompt + "\n\n"
                for sheet_name, rows in content.items():
                    # Take only first 10 records from each sheet
                    limited_rows = rows[:50]
                    full_user_prompt += f"### Sheet: {sheet_name}\n"
                    full_user_prompt += json.dumps(limited_rows, indent=2) + "\n\n"
            else:
                full_user_prompt = user_prompt + content


            
            # Step 3: Call OpenAI to generate response
            try:
                response_content = run_prompt(system_prompt, full_user_prompt)
            except Exception as e:
                error_msg = f"Error running prompt for blob {blob_name}: {str(e)}"
                logging.error(error_msg)
                errors.append(error_msg)
                continue

            # try:
            #     # 1. Taxonomy Validation
            #     taxonomy_input = taxonomy_prompt + json.dumps(json_info, indent=2)
            #     taxonomy_response = run_prompt(system_prompt, taxonomy_input)

            #     # 2. Comment Validation
            #     comment_input = comment_prompt + json.dumps(json_comments, indent=2)
            #     comment_response = run_prompt(system_prompt, comment_input)

            #     # 3. Filing Detail Validation
            #     filing_input = filing_prompt + json.dumps(json_filing, indent=2)
            #     filing_response = run_prompt(system_prompt, filing_input)
            # except Exception as e:
            #     error_msg = f"Error running prompts for blob {blob_name}: {str(e)}"
            #     logging.error(error_msg)
            #     errors.append(error_msg)
            #     continue

            
            # Clean up JSON response if necessary
            if response_content.startswith('```json') and response_content.endswith('```'):
                response_content = response_content.strip('`')
                response_content = response_content.replace('json', '', 1).strip()

            # def clean_response(resp):
            #     if resp.startswith('```json') and resp.endswith('```'):
            #         resp = resp.strip('`')
            #         resp = resp.replace('json', '', 1).strip()
            #     return resp

            # taxonomy_response = clean_response(taxonomy_response)
            # comment_response = clean_response(comment_response)
            # filing_response = clean_response(filing_response)

            # combined_response = {
            #     "taxonomy_validation": json.loads(taxonomy_response),
            #     "comment_validation": json.loads(comment_response),
            #     "filing_validation": json.loads(filing_response)
            # }

            # json_bytes = json.dumps(combined_response, indent=2).encode('utf-8')
            json_bytes = response_content.encode('utf-8')
            
            # Step 4: Write the response to a blob in the 'gold' container
            try:
                sourcefile = os.path.splitext(os.path.basename(blob_name))[0]
                write_to_blob("gold", f"{sourcefile}-output.json", json_bytes)
                processed_files.append(blob_name)
            except Exception as e:
                error_msg = f"Error writing output for blob {blob_name}: {str(e)}"
                logging.error(error_msg)
                errors.append(error_msg)
                continue
        
        # Prepare the response payload
        response_data = {
            "processedFiles": processed_files,
            "errors": errors,
            "status": "completed" if not errors else "completed_with_errors"
        }
        
        status_code = 200 if not errors else 500
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=status_code,
            mimetype="application/json"
        )
    
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
